"""Аналіз строків дії та безпеки SSL/TLS сертифікатів."""

import csv
import json
import logging
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

LOGGER = logging.getLogger(__name__)

# Шукаємо застарілі алгоритми підпису.
WEAK_ALGORITHM_PATTERN = re.compile(r"sha1|md5|md2", re.IGNORECASE)


@dataclass
class CertificateResult:
    """Результат аналізу одного сертифіката."""

    domain: str
    issuer: str
    valid_from: str
    valid_to: str
    days_left: int
    key_length: int
    signature_algorithm: str
    status: str
    issues: list[str]


def load_certificates(file_path: Path) -> list[dict]:
    """Зчитує список сертифікатів із JSON-файлу."""
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"Файл не знайдено: {file_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Некоректний JSON у файлі: {file_path}") from error

    if not isinstance(data, list):
        raise TypeError("JSON має містити список сертифікатів.")

    required_fields = {
        "domain",
        "issuer",
        "validFrom",
        "validTo",
        "keyLength",
        "signatureAlgorithm",
    }

    for number, certificate in enumerate(data, start=1):
        if not isinstance(certificate, dict):
            raise TypeError(f"Запис сертифіката №{number} має бути об'єктом.")

        missing_fields = required_fields - certificate.keys()
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"У сертифікаті №{number} відсутні поля: {missing}")

    return data


def analyze_certificates(
    certificates: list[dict],
    days_warning: int,
    current_date: date | None = None,
) -> tuple[list[CertificateResult], Counter]:
    """Перевіряє строки дії, алгоритми підпису та довжину ключа."""
    if days_warning < 0:
        raise ValueError("Кількість днів попередження не може бути від'ємною.")

    today = current_date or datetime.now(timezone.utc).astimezone().date()
    results = []
    issuer_counts = Counter()

    for certificate in certificates:
        try:
            valid_from = date.fromisoformat(certificate["validFrom"])
            valid_to = date.fromisoformat(certificate["validTo"])
            key_length = int(certificate["keyLength"])
        except (TypeError, ValueError) as error:
            domain = certificate.get("domain", "невідомий домен")
            raise ValueError(
                f"Некоректні дата або довжина ключа для {domain}."
            ) from error

        domain = certificate["domain"]
        issuer = certificate["issuer"]
        algorithm = certificate["signatureAlgorithm"]
        days_left = (valid_to - today).days
        issues = []

        if valid_from > today:
            issues.append("not_yet_valid")

        if days_left < 0:
            issues.append("expired")
        elif days_left <= days_warning:
            issues.append("expiring_soon")

        if WEAK_ALGORITHM_PATTERN.search(algorithm):
            issues.append("weak_signature")

        if key_length < 2048:
            issues.append("short_key")

        if "expired" in issues:
            status = "EXPIRED"
        elif issues:
            status = "WARNING"
        else:
            status = "OK"

        if issues:
            LOGGER.warning(
                "%s: %s",
                domain,
                ", ".join(issues),
            )

        results.append(
            CertificateResult(
                domain=domain,
                issuer=issuer,
                valid_from=valid_from.isoformat(),
                valid_to=valid_to.isoformat(),
                days_left=days_left,
                key_length=key_length,
                signature_algorithm=algorithm,
                status=status,
                issues=issues,
            )
        )
        issuer_counts[issuer] += 1

    return results, issuer_counts


def save_json_report(
    results: list[CertificateResult],
    issuer_counts: Counter,
    output_path: Path,
) -> None:
    """Зберігає результати та статистику у JSON."""
    report = {
        "issuer_statistics": dict(issuer_counts.most_common()),
        "certificates": [asdict(result) for result in results],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def save_csv_report(
    results: list[CertificateResult],
    output_path: Path,
) -> None:
    """Зберігає результати аналізу у CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(CertificateResult.__dataclass_fields__)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            row = asdict(result)
            row["issues"] = "; ".join(result.issues)
            writer.writerow(row)


def print_report(
    results: list[CertificateResult],
    issuer_counts: Counter,
) -> None:
    """Виводить короткий звіт у консоль."""
    print("=== SSL/TLS Certificate Report ===")

    for result in results:
        issues = ", ".join(result.issues) if result.issues else "none"
        print(
            f"{result.domain} | {result.issuer} | "
            f"{result.days_left} days left | {result.status} | "
            f"{result.signature_algorithm} | Issues: {issues}"
        )

    print("\n=== Issuer Statistics ===")
    for issuer, count in issuer_counts.most_common():
        print(f"{issuer}: {count}")
