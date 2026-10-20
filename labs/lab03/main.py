"""FastAPI-застосунок лабораторної роботи №3 (варіант 10).

Запуск із кореня репозиторію:
    uvicorn labs.lab03.main:app --reload --host 127.0.0.1 --port 8000
"""

import logging
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from labs.lab03.config import APP_DESCRIPTION, APP_TITLE
from labs.lab03.database import initialize_database
from labs.lab03.repository import ConflictError, InvalidDataError, NotFoundError
from labs.lab03.routers import categories, records
from labs.lab03.schemas import PingRead, StudentRead
from shared import student

logger = logging.getLogger("labs.lab03")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Створити відсутні таблиці під час запуску; дані не змінюються."""
    initialize_database()
    yield


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(categories.router)
app.include_router(records.router)


@app.exception_handler(RequestValidationError)
def handle_validation(_request: Request, error: RequestValidationError) -> JSONResponse:
    """Повернути 422 без вхідних значень (NaN чи Infinity не серіалізуються в JSON)."""
    details = [
        {"type": item["type"], "loc": list(item["loc"]), "msg": item["msg"]}
        for item in error.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": details},
    )


@app.exception_handler(NotFoundError)
def handle_not_found(_request: Request, error: NotFoundError) -> JSONResponse:
    """Перетворити NotFoundError на 404."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(error)}
    )


@app.exception_handler(ConflictError)
def handle_conflict(_request: Request, error: ConflictError) -> JSONResponse:
    """Перетворити ConflictError на 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": str(error)}
    )


@app.exception_handler(InvalidDataError)
def handle_invalid(_request: Request, error: InvalidDataError) -> JSONResponse:
    """Перетворити InvalidDataError на 422."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": str(error)},
    )


@app.exception_handler(sqlite3.Error)
def handle_database_error(_request: Request, error: sqlite3.Error) -> JSONResponse:
    """Записати технічні деталі в журнал і повернути загальне повідомлення."""
    logger.error("Помилка бази даних: %s", error, exc_info=error)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Внутрішня помилка сервера під час роботи з базою даних"},
    )


@app.get("/ping", response_model=PingRead, tags=["Службові"], summary="Перевірка API")
def ping() -> dict:
    """Перевірити доступність API."""
    return {"status": "ok"}


@app.get(
    "/student",
    response_model=StudentRead,
    tags=["Службові"],
    summary="Дані студента",
)
def get_student() -> dict:
    """Повернути ПІБ, групу та номер варіанта з shared/student.py."""
    return {
        "student_name": student.STUDENT_NAME,
        "group_name": student.GROUP_NAME,
        "variant_number": student.VARIANT_NUMBER,
    }
