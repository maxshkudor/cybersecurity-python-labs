"""Pydantic-моделі запитів і відповідей API."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from labs.lab03.config import BULK_MAX_ITEMS, BULK_MIN_ITEMS, VALUE_MAX, VALUE_MIN

Status = Literal["new", "in_progress", "done"]

INPUT_CONFIG = ConfigDict(str_strip_whitespace=True, extra="forbid")


class CategoryCreate(BaseModel):
    """Дані для створення категорії (ресурсу сервера)."""

    model_config = INPUT_CONFIG

    name: str = Field(
        min_length=2,
        max_length=40,
        description="Назва ресурсу, унікальна",
        examples=["network"],
    )


class CategoryRead(BaseModel):
    """Категорія у відповіді API."""

    id: int = Field(gt=0)
    name: str


class RecordCreate(BaseModel):
    """Дані для створення вимірювання; `id` задає база даних."""

    model_config = INPUT_CONFIG

    code: str = Field(
        min_length=3,
        max_length=40,
        description="Унікальний код вимірювання",
        examples=["V10-TEST"],
    )
    title: str = Field(
        min_length=3,
        max_length=120,
        description="Назва вимірювання",
        examples=["Навчальне вимірювання"],
    )
    category_id: int = Field(gt=0, description="Ідентифікатор категорії", examples=[1])
    value: float = Field(
        ge=VALUE_MIN,
        le=VALUE_MAX,
        allow_inf_nan=False,
        description="Використання ресурсу, % (0–100 включно)",
        examples=[85.5],
    )
    status: Status = Field(description="Стан перевірки спостереження")


class RecordReplace(RecordCreate):
    """Повна заміна змінюваних полів запису (усі поля обов’язкові)."""


class RecordRead(RecordCreate):
    """Вимірювання у відповіді API разом з `id` і назвою категорії."""

    model_config = ConfigDict(extra="ignore")

    id: int = Field(gt=0)
    category_name: str


RecordBulk = Annotated[
    list[RecordCreate],
    Field(min_length=BULK_MIN_ITEMS, max_length=BULK_MAX_ITEMS),
]


class StudentRead(BaseModel):
    """Дані студента з `shared/student.py`."""

    student_name: str
    group_name: str
    variant_number: int


class PingRead(BaseModel):
    """Відповідь перевірки доступності."""

    status: Literal["ok"]


class ErrorResponse(BaseModel):
    """Тіло відповіді з описом очікуваної помилки."""

    detail: str
