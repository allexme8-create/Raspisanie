"""
Backend «Расписание лицея».

Публичная часть:
  GET /                     -> клиентское приложение (просмотр расписания)
  GET /api/schedule         -> готовое расписание в JSON
  GET /api/status           -> краткий статус (загружено ли расписание)

Администратор (Authorization: Bearer <token>):
  POST /api/admin/login           {password} -> {token}
  GET  /api/admin/status          -> список загруженных файлов
  POST /api/admin/upload          multipart, поле files (1..N файлов .xls/.xlsx/.xml/.csv)
  POST /api/admin/fetch-yandex    {url} -> скачать файл по публичной ссылке Яндекс.Диска
  DELETE /api/admin/file/{kind}   -> удалить файл (teachers|subjects)

Запуск:
  uvicorn app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import json
import os
import re
import secrets
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from schedule_parser import ParseError, parse_schedule_file

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = (BASE_DIR.parent / "frontend").resolve()
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
STATE_FILE = DATA_DIR / "state.json"

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
TOKEN_TTL = 12 * 60 * 60  # 12 часов

app = FastAPI(title="Расписание лицея", docs_url="/api/docs")

# --------------------------------------------------------------- состояние
state: dict = {
    "teachers": None,   # {"classes": [...], "grid": {...}}
    "subjects": None,
    "files": {"teachers": None, "subjects": None},
    "updated_at": None,
}

_tokens: dict[str, float] = {}  # token -> expiry ts


def _save_state() -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False), encoding="utf-8"
    )


def _load_state() -> None:
    if STATE_FILE.exists():
        try:
            saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            for key in ("teachers", "subjects", "files", "updated_at"):
                if key in saved:
                    state[key] = saved[key]
        except Exception:  # noqa: BLE001
            pass


_load_state()


# ------------------------------------------------------------------ авторизация
def _check_token(token: str) -> bool:
    expiry = _tokens.get(token, 0)
    if time.time() < expiry:
        return True
    _tokens.pop(token, None)
    return False


def require_admin(authorization: str = Header(default="")) -> None:
    token = authorization.removeprefix("Bearer ").strip()
    if not token or not _check_token(token):
        raise HTTPException(status_code=401, detail="Требуется вход администратора")


class LoginBody(BaseModel):
    password: str


class YandexBody(BaseModel):
    url: str


# ------------------------------------------------------------------ обработка
def _ingest(buf: bytes, source_name: str) -> str:
    """Разобрать буфер, сохранить в state + на диск. Возвращает kind."""
    kind, data = parse_schedule_file(buf, source_name)
    ext = source_name.rsplit(".", 1)[-1].lower() if "." in source_name else "bin"
    # безопасное имя на диске
    safe = re.sub(r"[^0-9A-Za-zА-Яа-яЁё._-]+", "_", source_name)[:80]
    (UPLOAD_DIR / f"{kind}__{safe}").write_bytes(buf)
    state[kind] = data
    state["files"][kind] = source_name
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_state()
    return kind


def _stats_of(kind: str) -> dict | None:
    data = state.get(kind)
    if not data:
        return None
    lessons = sum(len(v) for v in data["grid"].values())
    return {
        "kind": kind,
        "filename": state["files"].get(kind),
        "classes": len(data["classes"]),
        "days_with_lessons": sum(1 for v in data["grid"].values() if v),
        "lesson_rows": lessons,
    }


# ------------------------------------------------------------------ публичное API
@app.get("/api/schedule")
def get_schedule() -> JSONResponse:
    return JSONResponse(
        {
            "teachers": state["teachers"],
            "subjects": state["subjects"],
            "files": state["files"],
            "updated_at": state["updated_at"],
        }
    )


@app.get("/api/status")
def get_status() -> dict:
    return {
        "ready": bool(state["teachers"] or state["subjects"]),
        "teachers": bool(state["teachers"]),
        "subjects": bool(state["subjects"]),
        "updated_at": state["updated_at"],
    }


# --------------------------------------------------------------------- админ API
@app.post("/api/admin/login")
def login(body: LoginBody) -> dict:
    if body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Неверный пароль")
    token = secrets.token_hex(24)
    _tokens[token] = time.time() + TOKEN_TTL
    return {"token": token}


@app.get("/api/admin/status")
def admin_status(_: None = Depends(require_admin)) -> dict:
    return {
        "teachers": _stats_of("teachers"),
        "subjects": _stats_of("subjects"),
        "updated_at": state["updated_at"],
    }


@app.post("/api/admin/upload")
async def admin_upload(
    _: None = Depends(require_admin),
    files: list[UploadFile] = File(...),
) -> dict:
    results = []
    for upload in files:
        buf = await upload.read()
        name = upload.filename or "file"
        try:
            kind = _ingest(buf, name)
        except ParseError as exc:
            results.append({"file": name, "ok": False, "error": str(exc)})
            continue
        results.append(
            {
                "file": name,
                "ok": True,
                "kind": kind,
                "classes": len(state[kind]["classes"]),
            }
        )
    return {"results": results, "updated_at": state["updated_at"]}


@app.post("/api/admin/fetch-yandex")
def admin_fetch_yandex(body: YandexBody, _: None = Depends(require_admin)) -> dict:
    """Скачать файл расписания по публичной ссылке Яндекс.Диска (серверная сторона)."""
    public_url = body.url.strip()
    if not public_url:
        raise HTTPException(status_code=400, detail="Пустая ссылка")
    api = (
        "https://cloud-api.yandex.net/v1/disk/public/resources/download"
        f"?public_key={urllib.parse.quote(public_url, safe='')}"
    )
    try:
        resp = requests.get(api, timeout=30)
        resp.raise_for_status()
        href = resp.json().get("href")
        if not href:
            raise ValueError("Яндекс не вернул ссылку на скачивание")
        file_resp = requests.get(href, timeout=120)
        file_resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Не удалось скачать файл с Яндекс.Диска: {exc}",
        ) from exc
    name = urllib.parse.unquote(
        urllib.parse.urlparse(href).path.rsplit("/", 1)[-1] or "yadisk_file.xls"
    )
    try:
        kind = _ingest(file_resp.content, name)
    except ParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "file": name, "kind": kind, "updated_at": state["updated_at"]}


@app.delete("/api/admin/file/{kind}")
def admin_delete(kind: str, _: None = Depends(require_admin)) -> dict:
    if kind not in ("teachers", "subjects"):
        raise HTTPException(status_code=404, detail="Неизвестный тип файла")
    state[kind] = None
    state["files"][kind] = None
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_state()
    return {"ok": True}


# ----------------------------------------------------------------- статика/страницы
@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/admin", include_in_schema=False)
def admin_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "admin.html")


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    return {"ok": True}


app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )
