"""Початкове заповнення бази навчальними даними з data/seed.json.

Запуск із кореня репозиторію:
    python -m labs.lab03.seed
"""

import json
import logging
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from labs.lab03.config import SEED_PATH
from labs.lab03.database import get_connection, initialize_database
from labs.lab03.schemas import CategoryCreate, RecordCreate

logger = logging.getLogger("labs.lab03.seed")


class SeedCategory(CategoryCreate):
    """Категорія початкового набору з наперед заданим id."""

    id: int = Field(gt=0)


class SeedData(BaseModel):
    """Структура seed.json: три категорії та вісім записів."""

    model_config = ConfigDict(extra="forbid")

    categories: list[SeedCategory] = Field(min_length=3, max_length=3)
    records: list[RecordCreate] = Field(min_length=8, max_length=8)

    @model_validator(mode="after")
    def check_consistency(self) -> "SeedData":
        """Перевірити унікальність і посилання на категорії всередині файлу."""
        category_ids = [category.id for category in self.categories]
        names = [category.name for category in self.categories]
        codes = [record.code for record in self.records]
        if len(set(category_ids)) != len(category_ids):
            raise ValueError("id категорій повторюються")
        if len(set(names)) != len(names):
            raise ValueError("назви категорій повторюються")
        if len(set(codes)) != len(codes):
            raise ValueError("code записів повторюються")
        unknown = {r.category_id for r in self.records} - set(category_ids)
        if unknown:
            raise ValueError(f"записи посилаються на відсутні категорії: {unknown}")
        return self


def load_seed(path: Path = SEED_PATH) -> SeedData:
    """Прочитати та перевірити початкові дані."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return SeedData.model_validate(raw)


def seed_database(data: SeedData) -> bool:
    """Заповнити порожню базу в одній транзакції.

    Повертає False, якщо база вже містить дані (нічого не змінюється).
    """
    with closing(get_connection()) as connection, connection:
        (categories_count,) = connection.execute(
            "SELECT COUNT(*) FROM categories"
        ).fetchone()
        (records_count,) = connection.execute("SELECT COUNT(*) FROM records").fetchone()
        if categories_count or records_count:
            return False
        connection.executemany(
            "INSERT INTO categories (id, name) VALUES (?, ?)",
            [(category.id, category.name) for category in data.categories],
        )
        connection.executemany(
            "INSERT INTO records (code, title, category_id, value, status) "
            "VALUES (?, ?, ?, ?, ?)",
            [(r.code, r.title, r.category_id, r.value, r.status) for r in data.records],
        )
    return True


def main() -> int:
    """Ініціалізувати базу й заповнити її; повернути код завершення."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    try:
        initialize_database()
        data = load_seed()
    except FileNotFoundError:
        print(f"Помилка: файл початкових даних не знайдено ({SEED_PATH.name}).")
        return 1
    except json.JSONDecodeError as error:
        print(f"Помилка: seed.json містить некоректний JSON (рядок {error.lineno}).")
        return 1
    except ValidationError as error:
        print("Помилка: початкові дані не пройшли перевірку:")
        for item in error.errors():
            location = ".".join(str(part) for part in item["loc"])
            print(f"  - {location or 'файл'}: {item['msg']}")
        return 1
    except sqlite3.Error:
        logger.exception("Не вдалося ініціалізувати базу")
        print("Помилка: не вдалося створити таблиці бази даних.")
        return 1

    try:
        inserted = seed_database(data)
    except sqlite3.IntegrityError:
        logger.exception("Порушено обмеження під час заповнення")
        print("Помилка: дані порушують обмеження бази. Зміни скасовано повністю.")
        return 1
    except sqlite3.Error:
        logger.exception("Помилка бази під час заповнення")
        print("Помилка роботи з базою. Зміни скасовано повністю.")
        return 1

    if not inserted:
        print(
            "База вже містить дані — повторне заповнення пропущено, нічого не змінено."
        )
        return 0
    print(
        f"Базу заповнено: категорій — {len(data.categories)}, "
        f"записів — {len(data.records)}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
