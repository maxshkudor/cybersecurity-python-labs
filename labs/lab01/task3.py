"""Завдання 3: Безпечне хешування, CSV-база та JSON-логування (Варіант 10).

Алгоритм хешування: SHA3-384
Мінімальна довжина пароля: 10 символів
"""

import csv
import hashlib
import json
import os
import sys
from datetime import datetime
from functools import wraps

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from shared.student import VARIANT_NUMBER

# --- Налаштування варіанту 10 ---
MIN_PASSWORD_LENGTH = 10
PERSONAL_SALT = str(VARIANT_NUMBER).zfill(5)  # "00010"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_CSV_PATH = os.path.join(DATA_DIR, "users.csv")
LOG_JSON_PATH = os.path.join(DATA_DIR, "log.json")

USERS_TO_REGISTER = (
    ("iot_admin", "IoTSecurity#2024"),
    ("mobile_lead", "M0bileGuard@Pro"),
    ("web_dev01", "WebDev$ecure123"),
    ("api_client", "ApiGateway!456"),
    ("device_mgr", "D3viceManager#1"),
    ("cert_authority", "CertAuth0rity!9"),
    ("vuln_scanner", "Vulner@bility10"),
    ("app_publisher", "AppPubl1sh#2024"),
    ("integration_svc", "Integr@tion#987"),
    ("demo_tester", "DemoT3st!ng2024"),
)


class ValidationError(Exception):
    """Власний виняток для помилок валідації пароля."""


def generate_hash(password: str, salt: str = "00000") -> str:
    """Генерує шістнадцятковий SHA3-384 хеш від конкатенації пароля та солі."""
    if password is None or password == "" or salt is None or salt == "":
        raise ValueError("Пароль та сіль не можуть бути порожніми")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"Довжина пароля має бути не менше {MIN_PASSWORD_LENGTH} символів"
        )

    combined = (password + salt).encode("utf-8")
    return hashlib.sha3_384(combined).hexdigest()


def create_user(username: str, password: str) -> tuple:
    """Створює запис користувача (логін, хеш пароля)."""
    hash_value = generate_hash(password, PERSONAL_SALT)
    return username, hash_value


def create_users(users_list: tuple) -> None:
    """Обробляє список користувачів та записує їх у CSV-файл."""
    os.makedirs(DATA_DIR, exist_ok=True)

    try:
        with open(USERS_CSV_PATH, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            for username, password in users_list:
                try:
                    login, hash_value = create_user(username, password)
                    writer.writerow([login, hash_value])
                except (ValueError, ValidationError) as exc:
                    print(f"Пропущено користувача '{username}': {exc}")
    except (FileNotFoundError, PermissionError, IOError) as exc:  # noqa: UP024
        print(f"Помилка запису файлу бази користувачів: {exc}")


def read_users_db() -> list:
    """Зчитує вміст CSV-файлу у список кортежів (login, hash)."""
    users_db = []
    try:
        with open(USERS_CSV_PATH, newline="", encoding="utf-8") as csv_file:
            reader = csv.reader(csv_file)
            for row in reader:
                if row:
                    users_db.append((row[0], row[1]))
    except FileNotFoundError:
        print(f"Файл {USERS_CSV_PATH} не знайдено. Спочатку зареєструйте користувачів.")
    except (PermissionError, IOError) as exc:  # noqa: UP024
        print(f"Помилка читання файлу бази користувачів: {exc}")
    return users_db


def print_users_db(users_db: list) -> None:
    """Виводить базу користувачів у вигляді структурованої таблиці."""
    print("\nБаза користувачів (users.csv):")
    print("-" * 100)
    print(f"{'Логін':<20}{'Хеш пароля (SHA3-384)':<80}")
    print("-" * 100)
    for username, hash_value in users_db:
        print(f"{username:<20}{hash_value:<80}")
    print("-" * 100)


def log_event(func):
    """Декоратор, що логує кожну спробу входу у файл log.json."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        username = kwargs.get("username", args[0] if args else "unknown")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # noqa: DTZ005

        try:
            result = func(*args, **kwargs)
            status = "success" if result else "failure"
        except (ValueError, ValidationError) as exc:
            result = False
            status = "failure"
            print(f"Помилка входу для '{username}': {exc}")

        event_entry = {
            "event": "login",
            "user": username,
            "result": status,
            "timestamp": timestamp,
            "args": [str(a) for a in args],
            "kwargs": {k: str(v) for k, v in kwargs.items()},
        }

        os.makedirs(DATA_DIR, exist_ok=True)
        events = []
        try:
            if os.path.exists(LOG_JSON_PATH):
                with open(LOG_JSON_PATH, encoding="utf-8") as log_file:
                    events = json.load(log_file)
        except (json.JSONDecodeError, IOError):  # noqa: UP024
            events = []

        events.append(event_entry)

        try:
            with open(LOG_JSON_PATH, "w", encoding="utf-8") as log_file:
                json.dump(events, log_file, ensure_ascii=False, indent=2)
        except (FileNotFoundError, PermissionError, IOError) as exc:  # noqa: UP024
            print(f"Помилка запису файлу журналу: {exc}")

        return result

    return wrapper


@log_event
def login(username: str, password: str) -> bool:
    """Перевіряє автентифікаційні дані користувача."""
    if username is None or username == "" or password is None or password == "":
        raise ValueError("Логін та пароль не можуть бути порожніми")

    users_db = read_users_db()
    expected_hash = generate_hash(password, PERSONAL_SALT)

    for db_username, db_hash in users_db:
        if db_username == username:
            return db_hash == expected_hash

    return False


def run() -> None:
    print(f"\nПерсональна сіль (варіант {VARIANT_NUMBER}): {PERSONAL_SALT}")

    create_users(USERS_TO_REGISTER)
    users_db = read_users_db()
    print_users_db(users_db)

    print("\nПеревірка автентифікації:")
    test_cases = [
        ("iot_admin", "IoTSecurity#2024"),  # правильний пароль
        ("iot_admin", "WrongPassword"),  # неправильний пароль
        ("unknown_user", "SomePassword123"),  # неіснуючий користувач
        ("mobile_lead", ""),  # порожній пароль -> ValueError
    ]

    for username, password in test_cases:
        try:
            success = login(username=username, password=password)
            status = "успішно" if success else "не успішно"
            print(f"Вхід для '{username}': {status}")
        except (ValueError, ValidationError) as exc:
            print(f"Вхід для '{username}' завершився помилкою: {exc}")


if __name__ == "__main__":
    run()
