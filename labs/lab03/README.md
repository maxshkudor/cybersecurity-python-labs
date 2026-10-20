# Лабораторна робота №3 — варіант 10

## Облік навантаження серверних ресурсів

Web API на FastAPI для обліку навчальних вимірювань використання серверних
ресурсів. Дані зберігаються у файловій базі SQLite; робота з базою виконується
напряму через модуль `sqlite3` (без ORM) із параметризованими запитами.

| Поле          | Значення                                                      |
|---------------|---------------------------------------------------------------|
| `categories`  | ресурс сервера: `cpu`, `memory`, `disk`                       |
| `code`        | унікальний код вимірювання, формат `V10-01`                   |
| `title`       | назва вимірювання, наприклад `Вимірювання сервера 01`         |
| `value`       | використання ресурсу, **percent**, `float` від 0 до 100 включно |
| `status`      | стан перевірки: `new`, `in_progress`, `done`                  |
| Поріг         | **80.0 %** — вимірювання з `value >= 80` вибирає `min_value=80` |

Між таблицями `categories` і `records` зв’язок «один до багатьох»:
`records.category_id` → `categories.id` з `ON DELETE RESTRICT`.

## Структура

```text
labs/lab03/
├── __init__.py
├── main.py              # FastAPI-застосунок, lifespan, обробники помилок, /ping, /student
├── database.py          # з’єднання (PRAGMA foreign_keys = ON) і виконання schema.sql
├── schema.sql           # готова схема (спільний початок + блок варіантів 10–12 + завершення)
├── repository.py        # усі параметризовані SQL-запити й транзакції
├── schemas.py           # Pydantic-моделі запитів і відповідей
├── config.py            # одиниця вимірювання, поріг, межі value, обмеження списку
├── seed.py              # перевірка seed.json і початкове заповнення в одній транзакції
├── check_scenarios.py   # відтворювана перевірка сценаріїв 2–13 завдання 3
├── routers/
│   ├── __init__.py      # спільні описи відповідей 404/409 для Swagger
│   ├── categories.py
│   └── records.py
├── data/
│   ├── seed.json        # 3 категорії та 8 записів варіанта 10
│   └── lab3.sqlite3     # створюється програмою, у Git не додається
└── README.md
```

## Встановлення

Усі команди виконуються з кореня репозиторію (Python 3.10+).

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## Створення та заповнення бази

```powershell
python -m labs.lab03.database     # лише створює таблиці (повторний запуск безпечний)
python -m labs.lab03.seed         # створює таблиці й додає 3 категорії та 8 записів
```

Повторний `seed` нічого не змінює і повідомляє, що база вже містить дані.
Щоб почати з чистої бази, видаліть файл `labs/lab03/data/lab3.sqlite3`.

## Запуск API

```powershell
uvicorn labs.lab03.main:app --reload --host 127.0.0.1 --port 8000
```

- Swagger UI: <http://127.0.0.1:8000/docs>
- OpenAPI-схема: <http://127.0.0.1:8000/openapi.json>

## Маршрути

| Метод і маршрут               | Призначення                         | Успіх |
|-------------------------------|-------------------------------------|-------|
| `GET /ping`                   | перевірка доступності               | 200   |
| `GET /student`                | ПІБ, група, варіант                 | 200   |
| `GET /categories`             | список категорій за `id`            | 200   |
| `POST /categories`            | створення категорії                 | 201   |
| `DELETE /categories/{id}`     | видалення порожньої категорії       | 204   |
| `GET /records`                | список із фільтрами та сторінками   | 200   |
| `GET /records/{id}`           | один запис                          | 200   |
| `POST /records`               | створення запису                    | 201   |
| `PUT /records/{id}`           | повна заміна змінюваних полів       | 200   |
| `DELETE /records/{id}`        | видалення запису                    | 204   |
| `POST /records/bulk`          | атомарне створення 1–100 записів    | 201   |

Параметри `GET /records`: `category_id` (> 0), `status`, `min_value` (0–100),
`q` (буквальний підрядок у `title`, 1–120 символів, з урахуванням регістру),
`limit` (1–100, типово 20), `offset` (≥ 0, типово 0). Фільтри об’єднуються
через `AND`, результат упорядковано за `id`.

Помилки: `404` — немає запису чи категорії; `409` — дублікат `code` або назви
категорії, видалення непорожньої категорії; `422` — дані не відповідають
моделі; `500` — технічна помилка бази (деталі лише в журналі сервера).

## Приклади запитів

PowerShell (`curl.exe`, щоб не викликався аліас `Invoke-WebRequest`):

```powershell
curl.exe -i "http://127.0.0.1:8000/ping"
curl.exe -i "http://127.0.0.1:8000/records?category_id=1&status=new&limit=5&offset=0"
curl.exe -i "http://127.0.0.1:8000/records?min_value=80"
```

Bash:

```bash
# створення запису
curl -i -X POST "http://127.0.0.1:8000/records" \
  -H "Content-Type: application/json" \
  -d '{"code":"V10-TEST","title":"Навчальне вимірювання","category_id":1,"value":85.5,"status":"new"}'

# повна заміна (усі п’ять полів)
curl -i -X PUT "http://127.0.0.1:8000/records/9" \
  -H "Content-Type: application/json" \
  -d '{"code":"V10-TEST","title":"Оновлене вимірювання","category_id":3,"value":97.5,"status":"done"}'

# видалення
curl -i -X DELETE "http://127.0.0.1:8000/records/9"

# пакет, який буде скасовано повністю (V10-01 уже є в базі) -> 409
curl -i -X POST "http://127.0.0.1:8000/records/bulk" \
  -H "Content-Type: application/json" \
  -d '[{"code":"V10-ROLLBACK","title":"Перший елемент","category_id":1,"value":40.0,"status":"new"},
       {"code":"V10-01","title":"Дублікат коду","category_id":2,"value":50.0,"status":"new"}]'
```

## Перевірка сценаріїв завдання 3

Із запущеним сервером в іншому терміналі:

```powershell
python -m labs.lab03.check_scenarios
```

Скрипт друкує кожен запит, HTTP-код і відповідь, а наприкінці — підсумок
(`32/32`). Створені ним записи видаляються, тож запуск можна повторювати.
Сценарій 14: створіть запис через `POST /records`, зупиніть сервер (Ctrl+C),
запустіть знову й прочитайте запис через `GET /records/{id}`.

## Перевірка стилю

```powershell
ruff check labs/lab03
ruff format --check labs/lab03
```
