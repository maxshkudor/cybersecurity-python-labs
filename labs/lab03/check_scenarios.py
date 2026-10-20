"""Відтворювана перевірка сценаріїв 2–13 завдання 3 для запущеного API.

Спочатку заповніть базу й запустіть сервер, потім в іншому терміналі:
    python -m labs.lab03.check_scenarios
    python -m labs.lab03.check_scenarios --base-url http://127.0.0.1:8000

Скрипт використовує лише стандартну бібліотеку. Записи, які він створює,
видаляються наприкінці, тому повторний запуск дає той самий результат.
Сценарій 14 (перезапуск сервера) перевіряється вручну, див. README.md.
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BASE_URL = "http://127.0.0.1:8000"
RESULTS: list[tuple[str, bool]] = []


def request(
    method: str, path: str, body: Any = None, base: str = BASE_URL
) -> tuple[int, Any]:
    """Виконати HTTP-запит і повернути код та розібране JSON-тіло."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            code, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        code, raw = error.code, error.read()
    return code, json.loads(raw) if raw else None


def show(title: str, method: str, path: str, code: int, payload: Any) -> None:
    """Надрукувати запит, код і відповідь для звіту."""
    print(f"\n### {title}\n{method} {path} -> {code}")
    if payload is not None:
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        lines = text.splitlines()
        print("\n".join(lines[:25]) + ("\n  ..." if len(lines) > 25 else ""))


def check(name: str, condition: bool) -> None:
    """Зафіксувати результат перевірки."""
    RESULTS.append((name, condition))
    print(f"[{'OK' if condition else 'FAIL'}] {name}")


def all_records(base: str) -> list[dict]:
    """Отримати всі записи посторінково через limit та offset."""
    items: list[dict] = []
    offset = 0
    while True:
        _, page = request("GET", f"/records?limit=100&offset={offset}", base=base)
        items.extend(page)
        if len(page) < 100:
            return items
        offset += 100


def call(title: str, method: str, path: str, body: Any, base: str) -> tuple[int, Any]:
    """Виконати запит і одразу показати результат."""
    code, payload = request(method, path, body, base)
    show(title, method, path, code, payload)
    return code, payload


def record(code: str, category_id: int = 1, value: float = 50.0) -> dict:
    """Сформувати тіло запису для перевірок."""
    return {
        "code": code,
        "title": f"Перевірка {code}",
        "category_id": category_id,
        "value": value,
        "status": "new",
    }


def run(base: str) -> None:
    """Виконати сценарії перевірки."""
    created_ids: list[int] = []

    # 2. Службові маршрути
    code, body = call("2. Ping", "GET", "/ping", None, base)
    check("GET /ping -> 200 ok", code == 200 and body == {"status": "ok"})
    code, body = call("2. Student", "GET", "/student", None, base)
    check("GET /student -> 200", code == 200 and body["variant_number"] == 10)
    code, body = call("2. Categories", "GET", "/categories", None, base)
    check("GET /categories -> 3 категорії", code == 200 and len(body) >= 3)

    # 3. CRUD
    code, body = call("3. Create", "POST", "/records", record("V10-CHK-CRUD"), base)
    check("POST /records -> 201", code == 201 and body.get("category_name") == "cpu")
    if code != 201:
        print("Запис V10-CHK-CRUD уже існує: видаліть його й запустіть знову.")
        return
    rid = body["id"]
    created_ids.append(rid)
    code, body = call("3. Read", "GET", f"/records/{rid}", None, base)
    check("GET /records/{id} -> 200", code == 200)
    new = record("V10-CHK-CRUD", category_id=3, value=97.5) | {"status": "done"}
    code, body = call("3. Replace", "PUT", f"/records/{rid}", new, base)
    check(
        "PUT -> 200, id не змінився",
        code == 200 and body["id"] == rid and body["category_name"] == "disk",
    )
    code, body = call("3. Delete", "DELETE", f"/records/{rid}", None, base)
    check("DELETE -> 204", code == 204 and body is None)
    created_ids.remove(rid)
    code, _ = call("3. Read deleted", "GET", f"/records/{rid}", None, base)
    check("GET видаленого -> 404", code == 404)

    # 4. Фільтри та сторінки
    code, body = call("4. min_value", "GET", "/records?min_value=80", None, base)
    check("min_value=80", all(r["value"] >= 80 for r in body))
    path = "/records?category_id=1&status=new"
    code, body = call("4. Два фільтри", "GET", path, None, base)
    check(
        "category_id=1 AND status=new",
        all(r["category_id"] == 1 and r["status"] == "new" for r in body),
    )
    _, page1 = call("4. Page 1", "GET", "/records?limit=3&offset=0", None, base)
    _, page2 = call("4. Page 2", "GET", "/records?limit=3&offset=3", None, base)
    ids = [r["id"] for r in page1 + page2]
    check("limit/offset, порядок за id", ids == sorted(ids) and len(set(ids)) == 6)
    _, body = call("4. q", "GET", "/records?q=" + urllib.parse.quote("01"), None, base)
    check("q=01 -> лише V10-01", [r["code"] for r in body] == ["V10-01"])

    # 5–6. Помилки перевірки
    before = len(all_records(base))
    bad_bodies = {
        "5. Від’ємне value": record("V10-BAD1", value=-1),
        "5. Порожній title": record("V10-BAD2") | {"title": "   "},
        "5. Недозволений статус": record("V10-BAD3") | {"status": "closed"},
        "6. value > 100": record("V10-BAD4", value=100.5),
        "6. Невідоме поле id": record("V10-BAD5") | {"id": 99},
    }
    for title, bad in bad_bodies.items():
        code, _ = call(title, "POST", "/records", bad, base)
        check(f"{title} -> 422", code == 422)
    code, _ = call("5. limit=0", "GET", "/records?limit=0", None, base)
    check("limit=0 -> 422", code == 422)
    check("база не змінилась після 422", len(all_records(base)) == before)

    # 7. Неіснуючі ресурси
    code, _ = call("7. Неіснуючий запис", "GET", "/records/99999", None, base)
    check("record_id=99999 -> 404", code == 404)
    body = record("V10-NOCAT", category_id=999)
    code, _ = call("7. Неіснуюча категорія", "POST", "/records", body, base)
    check("category_id=999 -> 404", code == 404)

    # 8. Дублікати
    code, _ = call("8. Дублікат code", "POST", "/records", record("V10-01"), base)
    check("повторний code -> 409", code == 409)
    code, _ = call(
        "8. Дублікат категорії", "POST", "/categories", {"name": "cpu"}, base
    )
    check("повторна назва категорії -> 409", code == 409)

    # 9. Видалення категорій
    code, _ = call("9. Непорожня категорія", "DELETE", "/categories/1", None, base)
    check("DELETE непорожньої -> 409", code == 409)
    _, cat = call("9. Нова категорія", "POST", "/categories", {"name": "gpu"}, base)
    code, _ = call(
        "9. Порожня категорія", "DELETE", f"/categories/{cat['id']}", None, base
    )
    check("DELETE порожньої -> 204", code == 204)

    # 10. Коректний пакет
    batch = [record("V10-CHK-BULK-1", 2, 70.0), record("V10-CHK-BULK-2", 3, 90.0)]
    code, body = call("10. Коректний пакет", "POST", "/records/bulk", batch, base)
    check("bulk -> 201, 2 записи", code == 201 and len(body) == 2)
    if code == 201:
        created_ids.extend(r["id"] for r in body)

    # 11–12. Скасування пакета
    for title, second, expected in (
        ("11. Пакет із дублікатом", record("V10-01", 2), 409),
        ("12. Пакет із неіснуючою категорією", record("V10-CHK-RB-2", 999), 404),
    ):
        before_items = all_records(base)
        batch = [record("V10-CHK-RB"), second]
        code, _ = call(title, "POST", "/records/bulk", batch, base)
        after_items = all_records(base)
        print(
            f"Кількість записів: до = {len(before_items)}, після = {len(after_items)}"
        )
        check(f"{title} -> {expected}", code == expected)
        check(
            f"{title}: нічого не збережено",
            len(after_items) == len(before_items)
            and all(r["code"] != "V10-CHK-RB" for r in after_items),
        )

    # 13. Спроба SQL-ін’єкції
    before_items = all_records(base)
    path = "/records?q=" + urllib.parse.quote("' OR 1=1 --")
    code, body = call("13. q=' OR 1=1 --", "GET", path, None, base)
    check("ін’єкція як дані -> 200, []", code == 200 and body == [])
    check("записи не змінились", all_records(base) == before_items)

    # Прибирання записів, створених цим скриптом
    for rid in created_ids:
        request("DELETE", f"/records/{rid}", base=base)


def main() -> int:
    """Розібрати аргументи, виконати сценарії та надрукувати підсумок."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()
    try:
        run(args.base_url.rstrip("/"))
    except urllib.error.URLError as error:
        print(f"Сервер недоступний: {error.reason}. Запустіть uvicorn.")
        return 1
    passed = sum(ok for _, ok in RESULTS)
    print(f"\nПідсумок: {passed}/{len(RESULTS)} перевірок пройдено.")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
