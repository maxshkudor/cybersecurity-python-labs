"""Маршрути для записів вимірювань використання ресурсів."""

from typing import Annotated

from fastapi import APIRouter, Body, Path, Query, Response, status

from labs.lab03 import repository
from labs.lab03.config import (
    LIST_DEFAULT_LIMIT,
    LIST_MAX_LIMIT,
    VALUE_MAX,
    VALUE_MIN,
)
from labs.lab03.routers import CONFLICT_RESPONSE, NOT_FOUND_RESPONSE
from labs.lab03.schemas import (
    RecordBulk,
    RecordCreate,
    RecordRead,
    RecordReplace,
    Status,
)

router = APIRouter(prefix="/records", tags=["Записи"])

RecordId = Annotated[int, Path(gt=0, description="Ідентифікатор запису")]


@router.get(
    "",
    response_model=list[RecordRead],
    summary="Список записів із фільтрами",
    description=(
        "Фільтри об’єднуються через AND, результати впорядковано за id. "
        "Якщо збігів немає, повертається порожній список."
    ),
)
def list_records(
    category_id: Annotated[
        int | None, Query(gt=0, description="Лише записи цієї категорії")
    ] = None,
    status_filter: Annotated[
        Status | None,
        Query(alias="status", description="Лише записи з цим статусом"),
    ] = None,
    min_value: Annotated[
        float | None,
        Query(
            ge=VALUE_MIN,
            le=VALUE_MAX,
            allow_inf_nan=False,
            description="Мінімальне використання, % (value >= min_value)",
        ),
    ] = None,
    q: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=120,
            description="Буквальний підрядок у title (з урахуванням регістру)",
        ),
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=LIST_MAX_LIMIT, description="Максимум записів")
    ] = LIST_DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0, description="Скільки записів пропустити")] = 0,
) -> list[dict]:
    """Отримати сторінку записів, що відповідають фільтрам."""
    return repository.list_records(
        category_id=category_id,
        status=status_filter,
        min_value=min_value,
        q=q,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/bulk",
    response_model=list[RecordRead],
    status_code=status.HTTP_201_CREATED,
    summary="Пакетне створення записів",
    description=(
        "Приймає масив із 1–100 записів. Усі записи зберігаються в одній "
        "транзакції: за будь-якої помилки не зберігається жоден."
    ),
    responses={**NOT_FOUND_RESPONSE, **CONFLICT_RESPONSE},
)
def create_records_bulk(payload: Annotated[RecordBulk, Body()]) -> list[dict]:
    """Атомарно створити пакет записів."""
    return repository.create_records_bulk([item.model_dump() for item in payload])


@router.get(
    "/{record_id}",
    response_model=RecordRead,
    summary="Отримати запис",
    responses={**NOT_FOUND_RESPONSE},
)
def get_record(record_id: RecordId) -> dict:
    """Отримати один запис за id."""
    return repository.get_record(record_id)


@router.post(
    "",
    response_model=RecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="Створити запис",
    responses={**NOT_FOUND_RESPONSE, **CONFLICT_RESPONSE},
)
def create_record(payload: RecordCreate) -> dict:
    """Створити запис; id призначає база даних."""
    return repository.create_record(payload.model_dump())


@router.put(
    "/{record_id}",
    response_model=RecordRead,
    summary="Повністю замінити запис",
    description="Потрібні всі п’ять змінюваних полів; id не змінюється.",
    responses={**NOT_FOUND_RESPONSE, **CONFLICT_RESPONSE},
)
def replace_record(record_id: RecordId, payload: RecordReplace) -> dict:
    """Замінити змінювані поля наявного запису."""
    return repository.replace_record(record_id, payload.model_dump())


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Видалити запис",
    responses={**NOT_FOUND_RESPONSE},
)
def delete_record(record_id: RecordId) -> Response:
    """Видалити запис за id."""
    repository.delete_record(record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
