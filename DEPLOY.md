# 🚀 Публикация расписания на бесплатном хостинге

**Рекомендуемый вариант: Render** — подключается к GitHub в пару кликов, сам читает
наш `Dockerfile`, без карты и без командной строки. Готовый адрес:
`https://raspisanie-xxxx.onrender.com`

> ⚠️ Hugging Face Spaces тоже поддержан (инструкция ниже), но с 2026 года там
> ужесточена бесплатная CPU-квота — у новых аккаунтов Space может не запускаться
> с ошибкой «You've reached your base CPU quota». Поэтому Render — надёжнее.

---

## Вариант A. Render (рекомендуется)

### Шаг 1. Регистрация
Откройте https://render.com → **Get Started** → удобнее всего **Sign up with GitHub**
(тогда Render сразу увидит ваш репозиторий).

### Шаг 2. Деплой по кнопке
1. Нажмите большую кнопку **«Deploy to Render»** вверху
   [README репозитория](https://github.com/allexme8-create/Raspisanie#readme)
   (или прямую ссылку: https://render.com/deploy?repo=https://github.com/allexme8-create/Raspisanie)
2. Render найдёт `render.yaml` и покажет форму **New Blueprint Instance**:
   - **Name**: `raspisanie` (только латиница и дефисы)
   - подтвердите → **Apply**
3. Начнётся сборка (3–5 минут, виден лог). Статус → **Live** ✅.

### Шаг 3. Задайте 2 секретные переменные
Страница сервиса → слева **Environment** → **Add Environment Variable**:

| Key | Value |
|---|---|
| `ADMIN_PASSWORD` | ваш секретный пароль для входа в `/admin` |
| `BACKUP_GH_TOKEN` | GitHub-токен classic с правом `repo` (https://github.com/settings/tokens → Generate new token (classic) → галочка **repo**). Нужен для автобэкапа расписания — Render free тоже с эфемерным диском |

**Save Changes** → сервис перезапустится сам.

### Шаг 4. Готово
- Сайт: **https://raspisanie.onrender.com** (точный адрес — сверху слева на странице сервиса)
- Админка: `/admin` → пароль из `ADMIN_PASSWORD` → загрузите оба файла расписания.

> ℹ️ Особенность free-тарифа: при 15 минутах без посетителей сервис «засыпает»,
> первый заход после сна — ~30–60 секунд. Для школьного расписания обычно ок;
> при желании бесплатный https://uptimerobot.com может «пинговать» сайт каждые
> 5 минут (`https://.../healthz`) и держать его тёплым.

---

## Вариант B. Hugging Face Spaces (если квота позволит)

Полностью без командной строки, через GitHub Actions (`.github/workflows/deploy-hf.yml`):

1. Создайте Space: https://huggingface.co/new-space → имя `raspisanie` (маленькими!),
   SDK **Docker** → Blank, Public.
2. HF-токен: https://huggingface.co/settings/tokens → Create new token → **Write**.
3. Секреты в GitHub (https://github.com/allexme8-create/Raspisanie/settings/secrets/actions):
   `HF_USERNAME` = ваш логин HF, `HF_TOKEN` = токен. Если имя Space ≠ `raspisanie` —
   добавьте `HF_SPACE_NAME` с точным именем.
4. Actions → **🚀 Deploy to Hugging Face Spaces** → **Run workflow**.
5. Секреты Space (Settings → Variables and secrets): `ADMIN_PASSWORD`,
   `BACKUP_GH_TOKEN`, `BACKUP_GH_REPO=allexme8-create/Raspisanie` → Restart.
6. Адрес: `https://ЛОГИН-raspisanie.hf.space`.

⚠️ При ошибке `You've reached your base CPU quota` — поставьте на паузу/удалите
остальные Spaces и повторите через 10–15 минут; если не помогает — это текущая
политика HF для free-аккаунтов, используйте вариант A.

## Вариант C. Любой VPS / свой сервер

```bash
git clone https://github.com/allexme8-create/Raspisanie.git
cd Raspisanie
docker build -t raspisanie .
docker run -d -p 8000:8000 \
  -e PORT=8000 -e ADMIN_PASSWORD="секрет" \
  -e BACKUP_GH_TOKEN=... -e BACKUP_GH_REPO=allexme8-create/Raspisanie \
  -v raspisanie_data:/app/backend/data \
  --restart unless-stopped raspisanie
```

---

## Проверка после деплоя

1. Откройте `/api/status` — пока расписание не загружено админом: `{"ready":false,...}`.
2. `/admin` → войдите → загрузите `samples/Пример_учителя.xlsx` и `samples/Пример_предметы.xlsx`.
3. Главная страница показывает расписание; в админке — ☁️-статус автобэкапа в GitHub.
4. Замените примеры настоящими файлами — посетители увидят обновление мгновенно.
5. Перезагрузите сервис (Render: Manual Deploy → Restart) — расписание должно
   восстановиться само из ветки `schedule-data` (проверка автобэкапа).
