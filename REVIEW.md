# 🔍 Глубокий code review проекта Ippon Bot

> **Дисклеймер:** ниже — конструктивная критика и предложения, а не требования. Пункты отсортированы по убыванию важности (от архитектуры до мелочей). После твоего фидбека перейдём к внедрению.

---

## 1. Архитектура и разделение ответственности

### 1.1. Монолитные модули

| Модуль | Строк | Что внутри | Проблема |
|--------|-------|------------|----------|
| `bot/services/google_sheets.py` | 282 | Долги, опросы, голоса, клиент, кэш | Три разных домена + инфраструктура в одном файле. Растёт быстро, тяжело тестировать. |
| `bot/handlers/commands.py` | 309 | /start, /help, /status, /payment, /links, 3 админ-команды, 2 callback-хэндлера | Смешены user- и admin-логика, плюс callback-обработчики опросов лежат в файле "commands". |
| `bot/config.py` | 109 | Загрузка .env, secrets, config.json + Pydantic-модель | Side-effect при импорте (`_load_config()` вызывается на `import bot.config`). Мешает юнит-тестам и переиспользованию. |

**Предложение:**
```
bot/
  integrations/
    gsheets/
      __init__.py
      client.py          # _get_client, кэш клиента
      debts.py           # get_debtors, get_member_balance
      polls.py           # save_poll, get_active_polls, get_all_poll_dates
      votes.py           # save_vote, get_votes_by_poll
  services/
    debt_notifier.py     # переименовать notifier.py → debt_notifier.py
    poll_manager.py      # переименовать poll_service.py
    payment_info.py      # переименовать payment.py
  handlers/
    common.py            # /start, /help, /status, /payment, /links
    admin.py             # /remind_debts, /remind_training, /new_training
    callbacks.py         # CreatePollCallback, RemindPollCallback
    polls.py             # PollAnswer (оставить как есть)
```

### 1.2. "Утилиты" как свалка

Папка `bot/utils/` содержит `scheduler.py` и `training_scheduler.py`. Название `utils` — антипаттерн: туда со временем складывают всё подряд.

**Предложение:** переименовать в `bot/schedulers/` или `bot/jobs/`:
- `debt_scheduler.py` (было `scheduler.py`)
- `training_scheduler.py` — оставить, но вынести `CHECK_HOUR / CHECK_MINUTE` в `config.json`.

### 1.3. Отсутствие слоя моделей (DTO)

Всё передаётся как сырые `dict`:
```python
async def create_training_poll(bot: Bot, training: dict, training_date: date) -> None:
```

**Предложение:** ввести Pydantic-модели:
```python
class Training(BaseModel):
    time: time
    location: str
    poll_create_days_before: int
    ...

class PollRecord(BaseModel):
    poll_id: str
    message_id: int
    date: date
    ...
```

---

## 2. Нейминг

### 2.1. Файлы

| Текущее имя | Проблема | Предлагаю |
|-------------|----------|-----------|
| `bot/data.py` | Слишком абстрактно. Загружает только `members.json`. | `bot/members.py` или `bot/repositories/members.py` |
| `bot/services/notifier.py` | Непонятно, о каких напоминаниях речь. | `bot/services/debt_notifier.py` |
| `bot/services/template.py` | Единственное число, хотя внутри много шаблонов. | `bot/services/templates.py` или `bot/core/templating.py` |
| `bot/services/training_config.py` | Загружает `trainings.json`, а не конфиг. | `bot/services/training_schedule.py` или `bot/core/trainings_loader.py` |
| `bot/services/payment.py` | Можно спутать с платёжным шлюзом. | `bot/services/payment_info.py` |

### 2.2. Функции и переменные

| Где | Что сейчас | Проблема | Предлагаю |
|-----|------------|----------|-----------|
| `handlers/polls.py` | `VOTE_MAP` | Название не говорит, что это список вариантов. | `POLL_OPTIONS` (единый источник правды, см. п. 4.1) |
| `poll_service.py` | `remind_non_voters()` | Просто прокси на `send_poll_reminders()`. Лишняя обёртка. | Удалить, вызывать `send_poll_reminders()` напрямую. |
| `config.py` | `_load_config()` | Приватная функция с side-effect на импорте. | `init_settings()` или `load_settings()` с явным вызовом из `main()`. |
| `member_filter.py` | `MemberFilterMiddleware` | Фильтрует по `members.json`, "Filter" в имени избыточно. | `MembershipMiddleware` или `AuthMiddleware` |

### 2.3. Шаблоны

| Текущее | Проблема | Предлагаю |
|---------|----------|-----------|
| `debt_dm.txt` | "dm" — сленг (Direct Message). | `debt_private.txt` или `debt_direct.txt` |
| `debt_group.txt` | Ок, но можно явнее. | `debt_group_mention.txt` (опционально) |

---

## 3. Дублирование и единый источник правды

### 3.1. Дублирование `POLL_OPTIONS`

```python
# bot/services/poll_service.py
POLL_OPTIONS = ["Буду", "Не буду", "Не знаю"]

# bot/handlers/polls.py
VOTE_MAP = ["Буду", "Не буду", "Не знаю"]
```

Если команда захочет добавить вариант, придётся менять в двух местах. Рассинхронизация приведёт к багу сопоставления голосов.

**Предложение:** вынести в `bot/constants.py` или `bot/models.py`.

### 3.2. Дублирование поиска имени по `user_id`

Одинаковый цикл в:
- `handlers/commands.py` (`cmd_status`)
- `handlers/polls.py` (`handle_poll_answer`)

**Предложение:** добавить в `bot/data.py` (или `bot/members.py`):
```python
def get_member_name_by_id(user_id: int) -> str | None:
    ...
```

---

## 4. Баги и потенциальные проблемы

### 4.1. Неправильный год при ручном создании опроса (`/new_training`)

```python
# bot/handlers/commands.py:on_create_poll
day, month = map(int, date_str.split("."))
year = datetime.now().year
training_date = datetime(year, month, day).date()
```

Если сейчас декабрь, а тренировка в январе, `year` останется текущим, и дата окажется в прошлом. `create_training_poll` получит неверную `training_date`.

**Предложение:** передавать `date_str` + `time` + `location` достаточно для `create_training_poll`, чтобы она сама определяла правильный год через `get_next_training_date()`, либо передавать `year` в callback.

### 4.2. Side-effect при импорте `bot.config`

```python
# bot/config.py
_load_config()  # вызывается прямо в модуле
```

Это делает невозможным:
- Импортировать модуль в тестах без создания файловой структуры.
- Переопределить `SENSITIVE_DIR` после импорта.

**Предложение:** сделать загрузку явной:
```python
# main.py
from bot.config import load_settings, Settings
settings = load_settings()
```

Или использовать `functools.lru_cache` для ленивой инициализации.

### 4.3. Несоответствие документации и файлов

- В `README.md` написано: `cp config/config.json.example config/config.json`, но в репозитории **нет** `config/config.json.example`, есть только `config/config.json`.
- В `PLAN.md` (п. 4.2) указано `data/members.json`, но на деле `members.json` живёт в `sensitive_dir` (вне репозитория).
- `PLAN.md` roadmap: этап 3 (Systemd, deploy.sh) не отмечен галочкой, хотя файлы уже в репозитории.

**Предложение:** синхронизировать `README.md` и `PLAN.md` с реальностью. Добавить `config/config.json.example`, если `config.json` не должен коммититься (хотя сейчас он закоммичен и не содержит секретов — это ок, но тогда убрать упоминание `.example` из README).

### 4.4. Systemd unit ссылается на `.env.prod`, которого нет в репозитории

```ini
# ippon-bot.service
EnvironmentFile=/home/bladvaran/projects/ippon_bot/.env.prod
```

В корне проекта есть только `.env.example`. Нет `.env.prod.example` или `.env.dev.example`.

**Предложение:**
1. Добавить `.env.prod.example` и `.env.dev.example` в корень.
2. Использовать переменные systemd (`%h`) для переносимости:
   ```ini
   WorkingDirectory=%h/projects/ippon_bot
   EnvironmentFile=%h/projects/ippon_bot/.env.prod
   ```
3. Или объяснить в README, что `.env` в корне — это и есть прод-конфиг (но тогда поправить `ippon-bot.service`).

### 4.5. Отсутствие валидации обязательных секретов

```python
class Settings(BaseSettings):
    bot_token: str = ""          # пусто по умолчанию
    google_sheets_spreadsheet_key: str = ""
    group_chat_id: int = 0
```

Бот запустится с пустым токеном и упадёт позже с неочевидной ошибкой.

**Предложение:** использовать `Field(...)` (required) для критичных полей, либо кастомный валидатор `@field_validator`.

---

## 5. Конфигурация и окружение

### 5.1. Захардкоженные константы

```python
# bot/utils/training_scheduler.py
CHECK_HOUR = 10
CHECK_MINUTE = 0
```

Это время проверки тренировок. Сейчас поменять можно только правкой кода.

**Предложение:** добавить в `config/config.json`:
```json
{
  "training_check_hour": 10,
  "training_check_minute": 0
}
```

### 5.2. Мутация `os.environ`

```python
# bot/config.py
for key, value in config.items():
    env_key = key.upper()
    if env_key not in os.environ:
        os.environ[env_key] = str(value)
```

Мутировать глобальный `os.environ` при старте приложения — плохая практика. Это влияет на все последующие импорты и тесты.

**Предложение:** читать `config.json` в словарь и передавать в `BaseSettings` через `SettingsConfigDict` или кастомный `json_file` source. В Pydantic-settings v2 можно реализовать кастомный `SettingsSourceFn`.

### 5.3. Хранение `members.json` и `payment.json`

Они живут в `sensitive_dir` (вне проекта). Это хорошо для секретов. Но `payment.json` — не секрет, а контент. `members.json` — не совсем секрет, а скорее данные.

**Предложение:** если `members.json` и `payment.json` не содержат чувствительных данных (только имена и реквизиты), можно держать их в `data/` рядом с `trainings.json`. Если они секретны — оставить в `sensitive_dir`, но явно задокументировать логику разделения.

---

## 6. Инфраструктура и DevEx

### 6.1. Отсутствие тестов

Нет ни одного теста. Даже простейшие юнит-тесты на чистые функции (`get_next_training_date`, `get_debtors` с моком gspread) сильно повысят уверенность при рефакторинге.

**Предложение:** добавить `tests/`:
```
tests/
  unit/
    test_training_schedule.py
    test_debt_notifier.py
    test_members.py
  conftest.py
```

И `pytest`, `pytest-asyncio` в `requirements-dev.txt` (или `requirements.txt` с `[dev]` extra).

### 6.2. `deploy.sh` — можно улучшить

```bash
# deploy.sh
git -C "$PROJECT_DIR" pull origin main
sudo systemctl restart "$SERVICE_NAME"
```

- Нет проверки, что `git pull` действительно принёс изменения (перезапускает сервис всегда).
- Нет `pip install` с `requirements.txt`? Есть, но только после `pull`.

**Предложение:**
```bash
if git -C "$PROJECT_DIR" pull origin main | grep -q "Already up to date"; then
    echo "No changes."
    exit 0
fi
pip install -q -r "$PROJECT_DIR/requirements.txt"
sudo systemctl restart "$SERVICE_NAME"
```

### 6.3. Logrotate

В `PLAN.md` упомянут `logrotate`, но в репозитории нет конфига. Бот пишет в journald (systemd), так что ротация идёт через `journalctl`. Стоит либо добавить пример `logrotate` (если логи пишутся в файл), либо удалить упоминание из `PLAN.md`.

### 6.4. Python version и `__future__`

Используется синтаксис `str | None` (Python 3.10+). В `requirements.txt` не указана версия Python.

**Предложение:** добавить `python_requires=">=3.10"` в `pyproject.toml` (если появится) или `README.md`. Если на ноутбуке вдруг Python 3.9 — добавить `from __future__ import annotations` в начало файлов.

---

## 7. Мелкие улучшения кода

### 7.1. Кэширование Google Sheets клиента

```python
# bot/services/google_sheets.py
_get_client()  # каждый раз создаёт Credentials.from_service_account_file()
```

**Предложение:** закэшировать клиент на уровне модуля:
```python
_client_cache: gspread.Client | None = None

def _get_client() -> gspread.Client:
    global _client_cache
    if _client_cache is None:
        _check_credentials()
        creds = Credentials.from_service_account_file(...)
        _client_cache = gspread.authorize(creds)
    return _client_cache
```

### 7.2. `get_all_values()` на каждый чих

Функции `get_all_poll_dates`, `get_poll_by_date`, `get_active_polls`, `get_votes_by_poll` читают **весь** лист. Для таблиц до 1000 строк это ок, но если таблица разрастётся, будет тормозить.

**Предложение:** использовать `sheet.get_values("A2:G")` с ограниченным диапазоном, либо завести локальный in-memory кэш с TTL (например, 1 минута).

### 7.3. `MemberFilterMiddleware` молча отбрасывает незнакомцев

```python
if user_id and is_member(user_id):
    return await handler(event, data)
return None  # тихо игнорируем
```

В личке пользователь не поймёт, почему бот молчит. В группе — ок, но в ЛС стоит ответить.

**Предложение:** для `Message` в приватном чате отправлять:
```python
if isinstance(event, Message) and event.chat.type == "private":
    await event.answer("Извини, ты не в списке команды. Обратись к капитану.")
```

### 7.4. Callback-хэндлеры в `commands.py`

`on_remind_poll` и `on_create_poll` — это обработчики inline-кнопок, а не команд. Они затрудняют навигацию по коду.

**Предложение:** перенести в `handlers/callbacks.py` или `handlers/admin.py` (рядом с командами, которые их порождают).

### 7.5. `parse_mode` для отдельных сообщений

В `bot/main.py` установлен `DefaultBotProperties(parse_mode=ParseMode.HTML)`. Это хорошо, но в `commands.py` в `cmd_payment` и `cmd_links` всё равно используется ручная вставка HTML-ссылок. Стоит проверить, что нигде не забыли `parse_mode=ParseMode.HTML` при переопределении.

### 7.6. Ссылка `tg://user?id=...`

```python
f'<a href="tg://user?id={contact_id}">{contact_name}</a>'
```

Не во всех клиентах Telegram открывается такая ссылка. Если есть `username` — лучше `t.me/username`. Но для внутреннего бота — приемлемо.

---

## 8. Чек-лист для обсуждения

Чтобы не раздувать объём правок, предлагаю приоритизировать. Ниже чек-лист — отметь, что resonates, и начнём:

- [ ] **🔥 Разбить `google_sheets.py`** на `integrations/gsheets/*`
- [ ] **🔥 Разбить `commands.py`** на `common.py` + `admin.py` + `callbacks.py`
- [ ] **🔥 Убрать side-effect из `config.py`** (явная инициализация)
- [ ] **🔥 Вынести `POLL_OPTIONS` в единый `constants.py`**
- [ ] **🔥 Добавить `get_member_name_by_id`** и убрать дублирование циклов
- [ ] **⚡️ Исправить баг с годом в `on_create_poll`**
- [ ] **⚡️ Добавить `.env.prod.example` / `.env.dev.example`** и поправить `README`
- [ ] **⚡️ Переименовать `utils/` → `schedulers/` и `data.py` → `members.py`**
- [ ] **⚡️ Добавить базовые тесты** (`pytest`)
- [ ] **💡 Добавить `config.json.example`** или убрать упоминание из `README`
- [ ] **💡 Закэшировать `_get_client()`**
- [ ] **💡 Вынести `CHECK_HOUR` в `config.json`**
- [ ] **💡 Добавить ответ незнакомцу в ЛС** (в middleware)
- [ ] **💡 Удалить устаревшие/неактуальные части `PLAN.md`**

---

## 9. Быстрые победы (если хочешь что-то сделать за 10 минут)

1. Создать `bot/constants.py` с `POLL_OPTIONS` и импортировать везде.
2. Добавить `get_member_name_by_id()` в `data.py`, заменить два цикла.
3. Переименовать `bot/utils/` → `bot/schedulers/`.
4. Добавить `.env.prod.example`.
5. Поправить `README`: убрать `cp config/config.json.example ...` или создать файл.
6. Убрать `remind_non_voters()` и звать `send_poll_reminders()` напрямую.

---

*Готов обсудить любой пункт и перейти к PR.*
