"""Маршрути API лабораторної роботи №3."""

from labs.lab03.schemas import ErrorResponse

NOT_FOUND_RESPONSE = {
    404: {"model": ErrorResponse, "description": "Запис або категорію не знайдено"}
}
CONFLICT_RESPONSE = {
    409: {"model": ErrorResponse, "description": "Конфлікт із наявними даними"}
}
