"""Завдання 1: Комплексний аналізатор надійності паролів (Варіант 10).

Оцінює стійкість паролів користувача до компрометації на основі
довжини, наявності цифр, великих/малих літер та спецсимволів,
а також факту повторного використання пароля у списку.
"""

import os
import random
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from shared.student import GROUP_NAME, STUDENT_NAME, VARIANT_NUMBER

# --- Вхідні дані для варіанту 10 ---
PASSWORDS = [
    "S0cial@Engineer",
    "basic",
    "Phish1ng@D3tect",
    "client",
    "Ransomwar3@Protect",
    "general",
    "Zero@D4y",
    "generic",
    "Bug@B0unty",
    "standard123",
]

CRITERIA = {
    "min_length": 11,
    "require_digits": True,
    "require_upper": True,
    "require_special": True,
}

FORBIDDEN_PASSWORDS = {
    "basic",
    "client",
    "general",
    "generic",
    "standard123",
    "guest",
}

# Групи символів, за якими рахується "надійність" (для градацій
# Слабкий/Середній використовуються всі 4 групи, а для
# Сильний/Дуже сильний — лише ті групи, що вимагаються критеріями).
_SPECIAL_CHARS = set("!@#$%^&*()-_=+[]{}|;:'\",.<>/?`~\\")


def _char_groups(password: str) -> dict:
    """Повертає інформацію про те, які групи символів є у паролі."""
    return {
        "digit": any(ch.isdigit() for ch in password),
        "upper": any(ch.isupper() for ch in password),
        "lower": any(ch.islower() for ch in password),
        "special": any(ch in _SPECIAL_CHARS for ch in password),
    }


def build_test_list(passwords: list, sample_size: int = 3) -> list:
    """Імітує повторне використання паролів.

    Обирає sample_size випадкових індексів зі списку, бере відповідні
    паролі та додає їх дублікати в кінець нового списку.
    """
    result = list(passwords)
    sample_size = min(sample_size, len(passwords))
    random_indices = random.sample(range(len(passwords)), k=sample_size)
    for index in random_indices:
        result.append(passwords[index])
    return result


def evaluate_password(
    password: str, criteria: dict, forbidden: set, all_passwords: list
) -> str:
    """Оцінює надійність одного пароля за 5-рівневою шкалою."""
    min_length = criteria["min_length"]

    # 1. Заборонений
    if password in forbidden or len(password) < min_length:
        return "Заборонений"

    groups = _char_groups(password)
    groups_met = sum(groups.values())

    # Перевірка виконання саме тих критеріїв, що ввімкнені у criteria
    required_met = True
    if criteria.get("require_digits") and not groups["digit"]:
        required_met = False
    if criteria.get("require_upper") and not groups["upper"]:
        required_met = False
    if criteria.get("require_special") and not groups["special"]:
        required_met = False

    # 4-5. Сильний / Дуже сильний: усі вимоги критеріїв виконано
    if required_met:
        if len(password) >= min_length + 4:
            if all_passwords.count(password) == 1:
                return "Дуже сильний"
            return "Сильний"  # довжина достатня, але не унікальний
        return "Сильний"

    # 3. Середній: декілька (але не всі) критеріїв з різних груп
    if groups_met >= 2:
        return "Середній"

    # 2. Слабкий: хоча б один критерій виконано
    if groups_met >= 1:
        return "Слабкий"

    return "Слабкий"


def print_report(all_passwords: list, results: list) -> None:
    """Виводить результат аналізу у зручному табличному форматі."""
    print(
        f"\nСтудент: {STUDENT_NAME} | Група: {GROUP_NAME} | Варіант: {VARIANT_NUMBER}"
    )
    print("\n" + "-" * 60)
    print(f"{'№':<4}{'Пароль':<25}{'Оцінка надійності':<25}")
    print("-" * 60)
    for i, (password, verdict) in enumerate(zip(all_passwords, results), start=1):
        print(f"{i:<4}{password:<25}{verdict:<25}")
    print("-" * 60)


def run() -> None:
    random.seed()  # можна прибрати seed() або задати число для відтворюваності
    all_passwords = build_test_list(PASSWORDS, sample_size=3)
    results = [
        evaluate_password(pwd, CRITERIA, FORBIDDEN_PASSWORDS, all_passwords)
        for pwd in all_passwords
    ]
    print_report(all_passwords, results)


if __name__ == "__main__":
    run()
