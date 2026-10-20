"""Модель користувача, сесії та аудиту для лабораторної роботи №2."""

import hashlib
import hmac
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import ClassVar

PASSWORD_ITERATIONS = 310_000
SESSION_TIMEOUT_SEC = 900

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z][A-Za-z0-9_]{2,63}@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
)


class User:
    """Користувач із перевіркою email і захищеним зберіганням пароля."""

    def __init__(
        self,
        username: str,
        email: str,
        role: str = "user",
        active: bool = True,
    ) -> None:
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Ім'я користувача не може бути порожнім.")

        self.username = username
        self._email = ""
        self.email = email
        self.role = role
        self.active = active

        # Пароль не зберігається у відкритому вигляді.
        self.__password_hash = b""
        self.__password_salt = b""

    @property
    def email(self) -> str:
        """Повертає email користувача."""
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        """Перевіряє формат email перед збереженням."""
        if not isinstance(value, str) or not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Email має неправильний формат.")
        self._email = value

    def set_password(self, password: str) -> None:
        """Зберігає хеш пароля з випадковою сіллю."""
        if not isinstance(password, str) or len(password) < 8:
            raise ValueError("Пароль має містити щонайменше 8 символів.")

        self.__password_salt = os.urandom(16)
        self.__password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            self.__password_salt,
            PASSWORD_ITERATIONS,
        )

    def check_password(self, password: str) -> bool:
        """Перевіряє пароль, не розкриваючи його хеш."""
        if not isinstance(password, str) or not self.__password_hash:
            return False

        candidate_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            self.__password_salt,
            PASSWORD_ITERATIONS,
        )
        return hmac.compare_digest(candidate_hash, self.__password_hash)

    def deactivate(self) -> None:
        """Деактивує обліковий запис користувача."""
        self.active = False

    def __str__(self) -> str:
        """Повертає безпечний опис користувача."""
        return (
            f"User(username={self.username!r}, "
            f"email={self.email!r}, "
            f"role={self.role!r}, "
            f"active={self.active})"
        )


class Admin(User):
    """Адміністратор — користувач із додатковими дозволами."""

    def __init__(
        self,
        username: str,
        email: str,
        role: str = "admin",
        active: bool = True,
        permissions: set[str] | None = None,
    ) -> None:
        super().__init__(username, email, role, active)
        self.permissions = set(permissions) if permissions is not None else set()

    def grant_permission(self, permission: str) -> None:
        """Додає дозвіл адміністратору."""
        if not isinstance(permission, str) or not permission.strip():
            raise ValueError("Назва дозволу не може бути порожньою.")
        self.permissions.add(permission)

    def revoke_permission(self, permission: str) -> None:
        """Відкликає дозвіл, якщо він існує."""
        self.permissions.discard(permission)

    def has_permission(self, permission: str) -> bool:
        """Перевіряє наявність дозволу."""
        return permission in self.permissions

    def __str__(self) -> str:
        """Повертає опис адміністратора разом із його дозволами."""
        permissions = ", ".join(sorted(self.permissions)) or "немає"
        return f"{super().__str__()}, permissions=[{permissions}]"


@dataclass
class Session:
    """Сесія користувача з часом у часовому поясі UTC."""

    ip: str
    login_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        """Оновлює час останньої активності."""
        self.last_activity = datetime.now(timezone.utc)

    def is_active(self, timeout_sec: int) -> bool:
        """Перевіряє, чи не завершився строк дії сесії."""
        if timeout_sec <= 0:
            raise ValueError("Час очікування має бути додатним.")

        inactive_for = datetime.now(timezone.utc) - self.last_activity
        return inactive_for < timedelta(seconds=timeout_sec)


@dataclass(frozen=True)
class AuditRecord:
    """Один незмінний запис журналу аудиту."""

    timestamp: datetime
    username: str
    action: str


class AuditLog:
    """Зберігає події входу та виходу користувачів."""

    def __init__(self) -> None:
        self.records: list[AuditRecord] = []

    def add_log(self, username: str, action: str) -> None:
        """Додає запис із поточним часом UTC."""
        record = AuditRecord(
            timestamp=datetime.now(timezone.utc),
            username=username,
            action=action,
        )
        self.records.append(record)

    def show_all(self) -> list[AuditRecord]:
        """Виводить усі записи та повертає їх списком."""
        for record in self.records:
            print(f"{record.timestamp.isoformat()} {record.username}: {record.action}")
        return list(self.records)


class UserAccount:
    """Обліковий запис, що поєднує користувача, сесію та аудит."""

    ALLOWED_KEYS: ClassVar[frozenset[str]] = frozenset({"user", "session", "audit_log"})

    def __init__(
        self,
        user: User,
        session: Session | None = None,
        audit_log: AuditLog | None = None,
    ) -> None:
        if not isinstance(user, User):
            raise TypeError("user має бути об'єктом класу User або Admin.")
        if session is not None and not isinstance(session, Session):
            raise TypeError("session має бути об'єктом класу Session.")
        if audit_log is not None and not isinstance(audit_log, AuditLog):
            raise TypeError("audit_log має бути об'єктом класу AuditLog.")

        self.user = user
        self.session = session
        self.audit_log = audit_log if audit_log is not None else AuditLog()

    def login(self, username: str, password: str, ip: str) -> bool:
        """Перевіряє дані й створює сесію в разі успішного входу."""
        if username != self.user.username or not self.user.active:
            self.audit_log.add_log(username, "login_failure")
            return False

        if not self.user.check_password(password):
            self.audit_log.add_log(username, "login_failure")
            return False

        now = datetime.now(timezone.utc)
        self.session = Session(ip=ip, login_time=now, last_activity=now)
        self.session.touch()
        self.audit_log.add_log(username, "login_success")
        return True

    def is_authenticated(self) -> bool:
        """Повертає True, якщо сесія існує та ще активна."""
        return self.session is not None and self.session.is_active(SESSION_TIMEOUT_SEC)

    def logout(self) -> None:
        """Завершує активну сесію та записує вихід до аудиту."""
        if self.session is not None:
            self.session = None
            self.audit_log.add_log(self.user.username, "logout")

    def __getitem__(self, key: str) -> User | Session | AuditLog | None:
        """Дозволяє читати дозволені поля як account['user']."""
        if key not in self.ALLOWED_KEYS:
            raise KeyError(f"Невідомий ключ: {key}")
        return getattr(self, key)

    def __setitem__(
        self,
        key: str,
        value: User | Session | AuditLog | None,
    ) -> None:
        """Дозволяє змінювати лише поля з відповідними типами."""
        expected_types = {
            "user": User,
            "session": Session,
            "audit_log": AuditLog,
        }

        if key not in expected_types:
            raise KeyError(f"Невідомий ключ: {key}")

        if key == "session" and value is None:
            self.session = None
            return

        if not isinstance(value, expected_types[key]):
            raise TypeError(f"Неправильний тип значення для ключа {key!r}.")

        setattr(self, key, value)
