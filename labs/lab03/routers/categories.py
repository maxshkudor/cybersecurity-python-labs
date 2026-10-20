"""Маршрути для категорій (ресурсів сервера)."""

from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from labs.lab03 import repository
from labs.lab03.routers import CONFLICT_RESPONSE, NOT_FOUND_RESPONSE
from labs.lab03.schemas import CategoryCreate, CategoryRead

router = APIRouter(prefix="/categories", tags=["Категорії"])

CategoryId = Annotated[int, Path(gt=0, description="Ідентифікатор категорії")]


@router.get(
    "",
    response_model=list[CategoryRead],
    summary="Список категорій",
    description="Повертає всі категорії за зростанням id.",
)
def list_categories() -> list[dict]:
    """Отримати список категорій."""
    return repository.list_categories()


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Створити категорію",
    responses={**CONFLICT_RESPONSE},
)
def create_category(payload: CategoryCreate) -> dict:
    """Створити категорію з унікальною назвою."""
    return repository.create_category(payload.name)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Видалити порожню категорію",
    description="Категорію, яка містить записи, видалити не можна (409).",
    responses={**NOT_FOUND_RESPONSE, **CONFLICT_RESPONSE},
)
def delete_category(category_id: CategoryId) -> Response:
    """Видалити категорію без записів."""
    repository.delete_category(category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
