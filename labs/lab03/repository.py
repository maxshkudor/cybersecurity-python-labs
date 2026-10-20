"""Параметризовані SQL-запити до таблиць `categories` і `records`.

Модуль не залежить від FastAPI: про очікувані ситуації він повідомляє
власними винятками, а шар API перетворює їх на HTTP-відповіді.
Кожна функція відкриває з’єднання, виконує операцію і закриває його.
"""

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import closing, contextmanager
from typing import Any

from labs.lab03.database import get_connection

Row = dict[str, Any]

RECORD_FIELDS = ("code", "title", "category_id", "value", "status")

RECORD_SELECT = """
    SELECT r.id, r.code, r.title, r.category_id, r.value, r.status,
           c.name AS category_name
    FROM records AS r
    JOIN categories AS c ON c.id = r.category_id
"""


class RepositoryError(Exception):
    """Базовий виняток шару доступу до даних."""


class NotFoundError(RepositoryError):
    """Запис або категорію не знайдено."""


class ConflictError(RepositoryError):
    """Порушено унікальність або категорія містить записи."""


class InvalidDataError(RepositoryError):
    """Дані порушують інші обмеження бази."""


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """Відкрити з’єднання з доступом до полів за назвою і закрити після роботи."""
    with closing(get_connection()) as connection:
        connection.row_factory = sqlite3.Row
        yield connection


def _translate_integrity_error(error: sqlite3.IntegrityError, code: str) -> None:
    """Перетворити помилку обмеження SQLite на виняток шару даних."""
    message = str(error)
    if "UNIQUE" in message:
        raise ConflictError(f"Запис із code '{code}' уже існує") from error
    if "FOREIGN KEY" in message:
        raise NotFoundError("Категорію не знайдено") from error
    raise InvalidDataError("Дані запису порушують обмеження бази") from error


def _category_exists(connection: sqlite3.Connection, category_id: int) -> bool:
    """Перевірити, чи існує категорія з указаним id."""
    row = connection.execute(
        "SELECT 1 FROM categories WHERE id = ?",
        (category_id,),
    ).fetchone()
    return row is not None


def _record_exists(connection: sqlite3.Connection, record_id: int) -> bool:
    """Перевірити, чи існує запис з указаним id."""
    row = connection.execute(
        "SELECT 1 FROM records WHERE id = ?",
        (record_id,),
    ).fetchone()
    return row is not None


def _fetch_record(connection: sqlite3.Connection, record_id: int) -> Row | None:
    """Отримати запис разом із назвою категорії через JOIN."""
    row = connection.execute(
        RECORD_SELECT + " WHERE r.id = ?",
        (record_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def _insert_record(connection: sqlite3.Connection, data: Row) -> int:
    """Додати один запис у межах уже відкритої транзакції."""
    if not _category_exists(connection, data["category_id"]):
        raise NotFoundError(f"Категорію з id={data['category_id']} не знайдено")
    try:
        cursor = connection.execute(
            "INSERT INTO records (code, title, category_id, value, status) "
            "VALUES (?, ?, ?, ?, ?)",
            tuple(data[field] for field in RECORD_FIELDS),
        )
    except sqlite3.IntegrityError as error:
        _translate_integrity_error(error, data["code"])
    return int(cursor.lastrowid)


# ---------------------------------------------------------------- категорії


def list_categories() -> list[Row]:
    """Повернути всі категорії за зростанням id."""
    with _connect() as connection:
        rows = connection.execute(
            "SELECT id, name FROM categories ORDER BY id"
        ).fetchall()
    return [dict(row) for row in rows]


def create_category(name: str) -> Row:
    """Створити категорію; id призначає база."""
    with _connect() as connection:
        try:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO categories (name) VALUES (?)",
                    (name,),
                )
        except sqlite3.IntegrityError as error:
            if "UNIQUE" in str(error):
                raise ConflictError(f"Категорія з назвою '{name}' уже існує") from error
            raise InvalidDataError("Назва категорії порушує обмеження") from error
        return {"id": int(cursor.lastrowid), "name": name}


def delete_category(category_id: int) -> None:
    """Видалити категорію, лише якщо вона існує і не містить записів."""
    with _connect() as connection:
        try:
            with connection:
                if not _category_exists(connection, category_id):
                    raise NotFoundError(f"Категорію з id={category_id} не знайдено")
                (count,) = connection.execute(
                    "SELECT COUNT(*) FROM records WHERE category_id = ?",
                    (category_id,),
                ).fetchone()
                if count:
                    raise ConflictError(
                        f"Категорія містить записи ({count}); видалення заборонено"
                    )
                connection.execute(
                    "DELETE FROM categories WHERE id = ?",
                    (category_id,),
                )
        except sqlite3.IntegrityError as error:
            # ON DELETE RESTRICT спрацював, якщо запис додали паралельно.
            raise ConflictError("Категорія містить записи") from error


# ------------------------------------------------------------------- записи


def get_record(record_id: int) -> Row:
    """Повернути один запис або викликати NotFoundError."""
    with _connect() as connection:
        record = _fetch_record(connection, record_id)
    if record is None:
        raise NotFoundError(f"Запис з id={record_id} не знайдено")
    return record


def list_records(
    *,
    category_id: int | None = None,
    status: str | None = None,
    min_value: float | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Row]:
    """Повернути записи з фільтрами (через AND) і поділом на сторінки.

    SQL-фрагменти беруться лише з наперед заданих рядків у коді,
    а всі значення передаються окремим списком параметрів.
    """
    conditions: list[str] = []
    params: list[Any] = []
    if category_id is not None:
        conditions.append("r.category_id = ?")
        params.append(category_id)
    if status is not None:
        conditions.append("r.status = ?")
        params.append(status)
    if min_value is not None:
        conditions.append("r.value >= ?")
        params.append(min_value)
    if q is not None:
        # instr() шукає буквальний підрядок з урахуванням регістру.
        conditions.append("instr(r.title, ?) > 0")
        params.append(q)

    sql = RECORD_SELECT
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY r.id LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with _connect() as connection:
        rows = connection.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def create_record(data: Row) -> Row:
    """Додати запис і повернути його разом із назвою категорії."""
    with _connect() as connection:
        with connection:
            record_id = _insert_record(connection, data)
        return _fetch_record(connection, record_id)


def replace_record(record_id: int, data: Row) -> Row:
    """Повністю замінити змінювані поля запису; id не змінюється."""
    with _connect() as connection:
        with connection:
            if not _record_exists(connection, record_id):
                raise NotFoundError(f"Запис з id={record_id} не знайдено")
            if not _category_exists(connection, data["category_id"]):
                raise NotFoundError(f"Категорію з id={data['category_id']} не знайдено")
            try:
                connection.execute(
                    "UPDATE records "
                    "SET code = ?, title = ?, category_id = ?, value = ?, status = ? "
                    "WHERE id = ?",
                    (*(data[field] for field in RECORD_FIELDS), record_id),
                )
            except sqlite3.IntegrityError as error:
                _translate_integrity_error(error, data["code"])
        return _fetch_record(connection, record_id)


def delete_record(record_id: int) -> None:
    """Видалити запис або викликати NotFoundError, якщо його немає."""
    with _connect() as connection, connection:
        cursor = connection.execute(
            "DELETE FROM records WHERE id = ?",
            (record_id,),
        )
        if cursor.rowcount == 0:
            raise NotFoundError(f"Запис з id={record_id} не знайдено")


def create_records_bulk(items: Sequence[Row]) -> list[Row]:
    """Додати пакет записів атомарно: зберігаються всі або жоден.

    Усі вставки виконуються в одній транзакції. Будь-який виняток
    усередині `with connection` скасовує весь пакет (rollback).
    """
    with _connect() as connection:
        with connection:
            ids = [_insert_record(connection, item) for item in items]
        if not ids:
            return []
        # У SQL додаються лише знаки "?"; самі id передаються параметрами.
        placeholders = ", ".join("?" for _ in ids)
        rows = connection.execute(
            RECORD_SELECT + f" WHERE r.id IN ({placeholders}) ORDER BY r.id",
            ids,
        ).fetchall()
    return [dict(row) for row in rows]


def count_records() -> int:
    """Повернути загальну кількість записів."""
    with _connect() as connection:
        (count,) = connection.execute("SELECT COUNT(*) FROM records").fetchone()
    return int(count)
