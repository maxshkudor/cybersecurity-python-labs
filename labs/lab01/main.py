"""Головний файл для демонстрації роботи Лабораторної роботи №1 (Варіант 10)."""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import task1
import task2
import task3

from shared.student import GROUP_NAME, STUDENT_NAME, VARIANT_NUMBER


def main() -> None:
    print("=" * 70)
    print(
        f"Лабораторна робота №1 | {STUDENT_NAME} | {GROUP_NAME} | Варіант {VARIANT_NUMBER}"
    )
    print("=" * 70)

    print("\n\n### ЗАВДАННЯ 1: Аналізатор надійності паролів ###")
    task1.run()

    print("\n\n### ЗАВДАННЯ 2: Система контролю доступу ###")
    task2.run()

    print("\n\n### ЗАВДАННЯ 3: Хешування, CSV-база та JSON-логування ###")
    task3.run()


if __name__ == "__main__":
    main()
