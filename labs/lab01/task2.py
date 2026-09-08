"""Завдання 2: Багаторівнева система контролю доступу (Варіант 10)."""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


# --- Вхідні дані для варіанту 10 ---
USERS = {
    "iot_specialist": {
        "role": "iot_security",
        "clearance": 3,
        "department": "IoT",
        "active": True,
    },
    "mobile_analyst": {
        "role": "mobile_security",
        "clearance": 3,
        "department": "Mobile",
        "active": True,
    },
    "web_developer": {
        "role": "web_developer",
        "clearance": 2,
        "department": "Web",
        "active": True,
    },
    "api_consumer": {
        "role": "api_user",
        "clearance": 2,
        "department": "Integration",
        "active": True,
    },
    "demo_account": {
        "role": "demonstration",
        "clearance": 1,
        "department": "Demo",
        "active": False,
    },
}

RESOURCES = [
    ("iot_firmware", 3),
    ("mobile_policies", 3),
    ("web_applications", 2),
    ("api_gateway", 2),
    ("device_certificates", 3),
    ("app_store", 1),
    ("vulnerability_database", 3),
    ("device_management", 3),
    ("integration_docs", 2),
    ("demo_content", 1),
]

SECURITY_LEVELS = ("Consumer", "Business", "Enterprise", "Critical Systems")

BLOCKED_USERS = {"demo_account", "compromised_device", "malicious_app"}


def level_name(level_number: int, levels: tuple = SECURITY_LEVELS) -> str:
    """Перетворює числовий рівень безпеки (1..4) у текстову назву."""
    return levels[level_number - 1]


def print_resources(resources: list) -> None:
    """Виводить список усіх ресурсів із текстовою назвою рівня безпеки."""
    print("\nСписок ресурсів системи:")
    print("-" * 45)
    print(f"{'Ресурс':<25}{'Рівень безпеки':<20}")
    print("-" * 45)
    for resource_name, level in resources:
        print(f"{resource_name:<25}{level_name(level):<20}")
    print("-" * 45)


def check_access(
    username: str, resource_level: int, users: dict, blocked: set
) -> tuple:
    """Перевіряє доступ користувача до ресурсу заданого рівня безпеки.

    Повертає кортеж (decision, reason), де decision - "ALLOW"/"DENY".
    """
    if username not in users:
        return "DENY", "User not found"

    if username in blocked:
        return "DENY", "User is blocked"

    user = users[username]

    if not user["active"]:
        return "DENY", "Account inactive"

    if user["clearance"] >= resource_level:
        return "ALLOW", ""

    return "DENY", "Insufficient clearance"


def run() -> None:
    print_resources(RESOURCES)

    print("\nРезультати перевірки доступу:")
    print("-" * 70)
    for username in USERS:
        for resource_name, level in RESOURCES:
            decision, reason = check_access(username, level, USERS, BLOCKED_USERS)
            if decision == "ALLOW":
                print(f"user={username} resource={resource_name} -> ALLOW")
            else:
                print(f"user={username} resource={resource_name} -> DENY ({reason})")
    print("-" * 70)


if __name__ == "__main__":
    run()
