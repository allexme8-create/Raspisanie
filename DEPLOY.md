# 🚀 Публикация расписания на бесплатном хостинге

Рекомендованный вариант: **Hugging Face Spaces** — бесплатно, без банковской карты,
не «засыпает» (сайт открывается мгновенно в любое время), поддерживает Docker.
Готовый адрес будет вида: `https://<ваш-логин>-raspisanie.hf.space`

Нужно ~10 минут и один раз выполнить шаги ниже.

---

## Вариант A. Hugging Face Spaces (рекомендуется)

### Шаг 1. Регистрация
Откройте https://huggingface.co/join — нужен только e-mail и пароль.

### Шаг 2. Создайте Space
1. https://huggingface.co/new-space
2. **Space name**: `raspisanie` (логика: `<логин>-raspisanie.hf.space`)
3. **SDK**: выберите **Docker** → шаблон **Blank**
4. **Visibility**: `Public`
5. Нажмите **Create Space**

### Шаг 3. Подключите GitHub → Space (без командной строки, всё в браузере)

В репозитории уже есть готовый автоматический сценарий публикации
(`.github/workflows/deploy-hf.yml`) — он сам зальёт код в ваш Space.

**3.1.** Создайте HF-токен: откройте https://huggingface.co/settings/tokens →
**Create new token** → тип **Write** → любое имя → **Create token** →
**скопируйте токен** (показывается один раз).

**3.2.** Добавьте два секрета в GitHub-репозиторий:
https://github.com/allexme8-create/Raspisanie/settings/secrets/actions/new

| Name | Secret (значение) |
|---|---|
| `HF_USERNAME` | ваш логин на huggingface.co (например `allexme8`) |
| `HF_TOKEN` | токен из шага 3.1 |

(секреты добавляются по одному: New repository secret → заполнить → Add secret)

**3.3.** Запустите публикацию:
https://github.com/allexme8-create/Raspisanie/actions → слева выберите
**🚀 Deploy to Hugging Face Spaces** → справа **Run workflow** → ветка `main` → зелёная кнопка.
Через ~30 секунд шаг станет зелёным ✅ — код ушёл в Space, и началась сборка (ещё 2–4 минуты).

> Дальше магия: любое будущее изменение в `main` будет **само** улетать на сайт.

<details>
<summary>Альтернатива: через командную строку (если установлен Git)</summary>

```bash
git clone https://github.com/allexme8-create/Raspisanie.git
cd Raspisanie
git remote add hf https://huggingface.co/spaces/ВАШ_ЛОГИН/raspisanie
git push hf main
```
Имя — логин HF, пароль — Access Token (Write).
</details>

### Шаг 4. Задайте секреты (пароль админки и бэкап)
Страница Space → **Settings** → **Variables and secrets** → **New secret**:

| Имя | Значение |
|---|---|
| `ADMIN_PASSWORD` | ваш секретный пароль для входа в `/admin` |
| `BACKUP_GH_TOKEN` | GitHub-токен (ниже) — чтобы расписание переживало перезапуск |
| `BACKUP_GH_REPO` | `allexme8-create/Raspisanie` |
| `BACKUP_GH_BRANCH` | `schedule-data` |

**GitHub-токен для бэкапа:**
https://github.com/settings/tokens → **Generate new token (classic)** → галочка `repo` →
Generate → скопируйте (он показывается один раз!).

> Зачем бэкап: у бесплатного Spaces эфемерный диск. Без бэкапа после рестарта/обновления
> Space админу придётся загружать файлы заново. С бэкапом сервер при старте сам
> подтянет последнее расписание из ветки `schedule-data` вашего GitHub-репозитория.
> Админка покажет статус бэкапа (☁️) вверху панели.

### Шаг 5. Готово
Через 2–4 минуты сборки откройте: `https://ВАШ_ЛОГИН-raspisanie.hf.space`

- клиент: `https://ВАШ_ЛОГИН-raspisanie.hf.space/`
- админка: `https://ВАШ_ЛОГИН-raspisanie.hf.space/admin` → пароль из `ADMIN_PASSWORD`
  → загрузите оба файла расписания.

---

## Вариант B. Render (free) — если HF недоступен

1. https://render.com → регистрация (можно через GitHub).
2. **New → Web Service** → подключите репозиторий `Raspisanie`.
3. Render сам найдёт `Dockerfile`. Instance type: **Free**.
4. Environment Variables: `ADMIN_PASSWORD`, при желании `BACKUP_*` (см. выше).
5. Deploy → адрес `https://raspisanie-xxxx.onrender.com`.

⚠️ Минус free-тарифа Render: сервис засыпает после 15 минут без трафика —
первый запрос после сна «прогревает» его ~30–60 секунд.

## Вариант C. PythonAnywhere (free) — для любителей классики

Аккаунт → Files: загрузить проект → Bash-консоль: `pip install -r backend/requirements.txt`
→ веб-вкладка: настроить WSGI на `backend/app.py` (ASGI → ASGI wrapper).
Подходит, если хочется адрес `логин.pythonanywhere.com`, но настройки больше.

---

## Проверка после деплоя

1. Откройте `/api/status` на вашем домене — должно быть `{"ready":false,...}` до первой загрузки.
2. Войдите в `/admin`, загрузите `samples/Пример_учителя.xlsx` и `samples/Пример_предметы.xlsx`.
3. На главной странице появится расписание; в админке — зелёные карточки файлов и ☁️-статус бэкапа.
4. Замените примеры настоящими файлами расписания — посетители увидят обновление сразу.
