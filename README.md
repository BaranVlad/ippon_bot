# Ippon Volleyball Bot

Telegram-бот для автоматизации рутины волейбольной команды «Иппон».

## Возможности

### 💰 Напоминания о долгах (MVP)
- Читает долги из Google Таблицы (диапазон `J2:K15`)
- **Личные сообщения** — тем, кто писал боту `/start`
- **Групповое сообщение** — для остальных (в General)
- Кликабельная ссылка на таблицу с расчётом
- Шаблоны сообщений в `templates/` (удобно редактировать)
- Команда `/remind` — принудительная отправка (только админ)

### 🏐 Опросы перед тренировками
- Автоматическое создание опросов за N дней до тренировки
- Расписание в `data/trainings.json` (пятница, воскресенье)
- Нативные Telegram-опросы (видно, кто как проголосовал)
- Сохранение результатов в Google Таблице (листы «Опросы» и «Голоса»)
- Напоминание не проголосовавшим за день до тренировки

## Быстрый старт

### 1. Создание ботов

1. Напишите [@BotFather](https://t.me/BotFather)
2. Создайте два бота:
   - `@ippon_volley_bot` (продакшен)
   - `@ippon_volley_test_bot` (для разработки)
3. Сохраните токены

### 2. Настройка Google Sheets API

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте проект → включите API Google Sheets
3. Создайте **Service Account** (не OAuth Client!)
4. Сгенерируйте ключ JSON и скачайте как `credentials.json`
5. Поделитесь таблицей с email сервисного аккаунта (`...@...gserviceaccount.com`)

**Таблица долгов:**

Лист **«Долги»**:
| | J | K |
|---|---|---|
| 2 | Иван | -1500 |
| 3 | Петр | 500 |

**Таблица опросов** (отдельная, задаётся `POLLS_SPREADSHEET_KEY`):

Лист **«Опросы»** (создаётся автоматически):
| poll_id | message_id | date | time | location | thread_id | status |

Лист **«Голоса»** (создаётся автоматически):
| poll_id | name | vote | voted_at |

### 3. Настройка конфигурации (3 уровня)

Проект использует 3 уровня конфигурации:

| Уровень | Файл | Что внутри | Кто видит |
|---------|------|-----------|-----------|
| Мета | Корневой `.env` | `SENSITIVE_DIR`, `CONFIG_PATH` | В репозитории (пример) |
| Секреты | `sensitive_dir/.env` + `credentials.json` | Токены, ключи таблиц | Только разработчик |
| Конфиг | `config/config.json` | Часы, дни, диапазоны | В репозитории |

**Шаг 1: Создайте папку секретов**
```bash
mkdir ~/ippon-secrets
cp secrets/.env.example ~/ippon-secrets/.env
cp secrets/credentials.json.example ~/ippon-secrets/credentials.json
cp secrets/members.json.example ~/ippon-secrets/members.json
cp secrets/payment.json.example ~/ippon-secrets/payment.json
# Отредактируйте файлы
```

**Шаг 2: Runtime-конфиг**
`config/config.json` — не содержит секретов, коммитится в репозиторий. При необходимости отредактируйте.

**Шаг 3: Корневой `.env`** указывает пути:
```bash
SENSITIVE_DIR=/home/bladvaran/ippon-secrets
CONFIG_PATH=./config/config.json
```

**`members.json`** — имя из таблицы → Telegram `user_id`:
```json
{
  "Иван": 123456789,
  "Петр": 987654321
}
```

**`data/trainings.json`** — расписание тренировок (не секрет, лежит в проекте):
```json
[
  {
    "day_of_week": 4,
    "time": "18:00",
    "location": "БНТУ",
    "poll_create_days_before": 2,
    "reminder_days_before": 1
  },
  {
    "day_of_week": 6,
    "time": "18:00",
    "location": "БНТУ",
    "poll_create_days_before": 2,
    "reminder_days_before": 1
  }
]
```

### 4. Установка

```bash
# Клонирование
git clone <repo-url>
cd ippon_bot

# Виртуальное окружение
python -m venv .venv
source .venv/bin/activate

# Зависимости
pip install -r requirements.txt

# Конфигурация
cp .env.example .env
cp config/config.json.example config/config.json
# Создайте ~/ippon-secrets из примеров в secrets/
# Отредактируйте корневой .env (укажите SENSITIVE_DIR)
```

### 5. Запуск

```bash
# Локальная разработка
python -m bot

# Продакшен
# Убедитесь, что корневой .env указывает на production SENSITIVE_DIR
python -m bot
```

## Деплой на ноутбуке (Manjaro/Linux)

```bash
# Скопировать systemd unit
sudo cp ippon-bot.service /etc/systemd/system/
sudo systemctl daemon-reload

# Запуск
sudo systemctl enable --now ippon-bot

# Просмотр логов
sudo journalctl -u ippon-bot -f

# Обновление
./deploy.sh
```

## Команды

| Команда | Описание | Кто видит |
|---------|----------|-----------|
| `/start` | Приветствие | Все |
| `/help` | Справка (адаптивная) | Все |
| `/status` | Показать свой баланс | Все |
| `/payment` | Реквизиты для оплаты | Все |
| `/links` | Полезные ссылки | Все |
| `/remind_debts` | Напомнить о долгах | Админы группы |
| `/remind_training` | Напомнить не проголосовавшим | Админы группы |
| `/new_training` | Создать опрос для тренировки | Админы группы |

**Подсказки при вводе `/`:** общие команды видны всем, админские — только администраторам группы.

**Безопасность:** бот игнорирует сообщения от пользователей, которых нет в `members.json`. Голосовать в опросах может любой участник группы.

## Настройка окружения

**Корневой `.env`** (в репозитории, не содержит секретов):
```bash
SENSITIVE_DIR=/home/bladvaran/ippon-secrets
CONFIG_PATH=./config/config.json
```

**`sensitive_dir/.env`** (только у разработчика):
```bash
BOT_TOKEN=...
GOOGLE_SHEETS_SPREADSHEET_KEY=...
POLLS_SPREADSHEET_KEY=        # Отдельная таблица для опросов (опционально)
SPREADSHEET_URL=https://docs.google.com/spreadsheets/d/...
GROUP_CHAT_ID=-100...
POLLS_MESSAGE_THREAD_ID=2   # ID темы "Опросы"
ADMINS=705263227,123456789
```

**`config/config.json`** (коммитится, не содержит секретов):
```json
{
  "timezone": "Europe/Moscow",
  "reminder_day_of_week": 0,
  "reminder_hour": 19,
  "reminder_minute": 0,
  "debt_threshold": -20.0,
  "google_sheets_debts_range": "J2:K15"
}
```

## Архитектура

```
ippon_bot/
├── config/
│   └── config.json         # Нечувствительные настройки
├── secrets/
│   ├── .env.example        # Пример секретов
│   ├── members.json.example
│   └── credentials.json.example
├── bot/
│   ├── main.py              # Точка входа, polling + scheduler
│   ├── config.py            # Загрузка конфигурации (3 уровня)
│   ├── data.py              # Загрузка members.json
│   ├── handlers/
│   │   ├── commands.py      # /start, /help, /status, /remind
│   │   └── polls.py         # Обработка PollAnswer
│   ├── middlewares/
│   │   └── member_filter.py # Фильтр: только участники из members.json
│   ├── services/
│   │   ├── google_sheets.py # Работа с таблицами (долги, опросы, голоса)
│   │   ├── notifier.py      # Отправка напоминаний о долгах
│   │   ├── poll_service.py  # Создание опросов, напоминания
│   │   ├── template.py      # Загрузка шаблонов
│   │   └── training_config.py # Чтение trainings.json
│   └── utils/
│       ├── scheduler.py         # APScheduler (долги: воскресенье 19:00)
│       └── training_scheduler.py # Ежедневная проверка тренировок
```

## Разработка

- `main` — стабильная ветка, крутится на ноутбуке
- `feature/xxx` — фичи
- Два бота: dev (для тестов) и prod (боевой)

## Roadmap

- [x] Напоминания о долгах (ЛС + группа)
- [x] Опросы перед тренировками
- [x] Сохранение голосов в Google Sheets (отдельная таблица)
- [x] Команда `/new_training` для ручного создания опроса
- [x] Команда `/remind_training` для напоминания не проголосовавшим
- [x] Включение/выключение авто-создания опросов
- [x] Обработка отмены голоса (retract vote)
- [x] Команды `/payment` и `/links`
- [ ] Итоговая сводка после закрытия опроса
