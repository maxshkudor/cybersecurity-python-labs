"""Командний рядок для лабораторної роботи №2."""

import argparse
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from labs.lab02.task1 import (
    Admin,
    AuditLog,
    User,
    UserAccount,
)
from labs.lab02.task2 import (
    analyze_certificates,
    load_certificates,
    print_report,
    save_csv_report,
    save_json_report,
)

DEFAULT_DATA = Path("labs/lab02/data/data_v10/certificates.json")
DEFAULT_REPORT = Path("labs/lab02/data/certificate_report.json")
SESSION_TIMEOUT_SEC = 900

LOGGER = logging.getLogger(__name__)


def run_demo() -> None:
    """Показує роботу класів із завдання 1."""
    user = User(
        username="olena",
        email="olena_ua@example.com",
    )
    user.set_password("SafePass123!")

    audit_log = AuditLog()
    account = UserAccount(user=user, audit_log=audit_log)

    print("Успішний вхід:")
    print(account.login("olena", "SafePass123!", "192.0.2.10"))
    print("Авторизований:", account.is_authenticated())

    print("\nНевдалий вхід:")
    print(account.login("olena", "wrong-password", "192.0.2.10"))

    print("\nПеревірка email:")
    try:
        user.email = "неправильний-email"
    except ValueError as error:
        print("Помилка:", error)

    user.email = "olena_new@example.com"
    print("Новий email:", user.email)

    print("\nАдміністратор:")
    admin = Admin(
        username="admin",
        email="admin@example.com",
    )
    admin.grant_permission("certificates:read")
    print(admin)
    print(
        "Має дозвіл certificates:read:",
        admin.has_permission("certificates:read"),
    )

    print("\nПеревірка завершення сесії за таймаутом:")
    if account.session is not None:
        account.session.last_activity = datetime.now(timezone.utc) - timedelta(
            seconds=SESSION_TIMEOUT_SEC + 1
        )
    print("Авторизований:", account.is_authenticated())

    print("\nВихід:")
    account.logout()

    print("\nЗаписи аудиту:")
    account.audit_log.show_all()


def run_analyze(args: argparse.Namespace) -> None:
    """Зчитує сертифікати, аналізує та зберігає звіт."""
    LOGGER.info("Зчитую дані сертифікатів з %s", args.certs_data)

    certificates = load_certificates(args.certs_data)
    results, issuer_counts = analyze_certificates(
        certificates,
        days_warning=args.days_warning,
    )

    print_report(results, issuer_counts)

    if args.format == "json":
        save_json_report(results, issuer_counts, args.output_report)
    else:
        save_csv_report(results, args.output_report)

    LOGGER.info(
        "Перевірено сертифікатів: %d. Звіт збережено: %s",
        len(results),
        args.output_report,
    )


def build_parser() -> argparse.ArgumentParser:
    """Створює парсер команд і параметрів."""
    parser = argparse.ArgumentParser(
        description="Лабораторна робота №2: монітор SSL/TLS сертифікатів"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # Команда demo — демонстрація завдання 1.
    subparsers.add_parser(
        "demo",
        help="показати демонстрацію ООП-моделі",
    )

    # Команда analyze — аналіз сертифікатів, завдання 2.
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="проаналізувати сертифікати",
    )
    analyze_parser.add_argument(
        "--certs-data",
        type=Path,
        default=DEFAULT_DATA,
        help="шлях до JSON-файлу сертифікатів",
    )
    analyze_parser.add_argument(
        "--days-warning",
        type=int,
        default=30,
        help="попереджати про завершення строку за стільки днів",
    )
    analyze_parser.add_argument(
        "--output-report",
        type=Path,
        default=DEFAULT_REPORT,
        help="шлях для вихідного звіту",
    )
    analyze_parser.add_argument(
        "--format",
        choices=("json", "csv"),
        default="json",
        help="формат вихідного звіту",
    )
    analyze_parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help="рівень повідомлень журналу",
    )

    return parser


def main() -> int:
    """Обробляє команду користувача."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "demo":
        run_demo()
        return 0

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="[%(levelname)s] %(message)s",
    )

    try:
        run_analyze(args)
    except (OSError, TypeError, ValueError) as error:
        LOGGER.error("Не вдалося виконати аналіз: %s", error)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
