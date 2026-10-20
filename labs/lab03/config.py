"""Параметри варіанта 10: облік навантаження серверних ресурсів."""

from pathlib import Path

VARIANT_NUMBER = 10

APP_TITLE = "Облік навантаження серверних ресурсів"
APP_DESCRIPTION = (
    "Навчальний сервіс обліку вимірювань використання серверних ресурсів "
    "(варіант 10). Категорія визначає ресурс (`cpu`, `memory`, `disk`), "
    "`value` — використання ресурсу у відсотках від 0 до 100 включно, "
    "`status` — стан перевірки спостереження (`new`, `in_progress`, `done`). "
    "Поріг уваги — 80.0 %: вимірювання з `value >= 80` можна вибрати "
    "фільтром `min_value=80`."
)

UNIT = "percent"
THRESHOLD = 80.0
VALUE_MIN = 0.0
VALUE_MAX = 100.0

RECORD_TITLE_PREFIX = "Вимірювання сервера"

STATUSES = ("new", "in_progress", "done")

BULK_MIN_ITEMS = 1
BULK_MAX_ITEMS = 100

LIST_DEFAULT_LIMIT = 20
LIST_MAX_LIMIT = 100

SEED_PATH = Path(__file__).resolve().parent / "data" / "seed.json"
