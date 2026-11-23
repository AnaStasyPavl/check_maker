"""Общие данные для тестов. Файлы проекта не изменяются."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from pdf_generator.config import CSV_COLUMNS

EXPECTED_TOTAL = "199000.00"


def sample_invoice(number: str = "2026-001") -> dict[str, Any]:
    """Счёт с четырьмя позициями. Итог — 199000.00."""
    return {
        "invoice_number": number,
        "invoice_date": "23.11.2026",
        "seller_name": "ООО Ромашка",
        "seller_inn": "7701234567",
        "seller_address": "г. Москва, ул. Ленина, д. 10",
        "seller_phone": "+7 495 123-45-67",
        "buyer_name": "ООО Покупатель",
        "buyer_inn": "7809876543",
        "buyer_address": "г. Санкт-Петербург, Невский проспект, д. 25",
        "bank_name": "Сбербанк",
        "bik": "044525225",
        "bank_account": "40702810000000000001",
        "correspondent_account": "30101810400000000225",
        "payment_days": 5,
        "items": [
            {"product": "Ноутбук Lenovo ThinkPad", "price": "75000.00", "qty": "2"},
            {"product": "Мышь Logitech", "price": "2500.00", "qty": "3"},
            {"product": "Клавиатура Logitech", "price": "4500.00", "qty": "1"},
            {"product": "Монитор Samsung 27", "price": "18500.00", "qty": "2"},
        ],
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, documents: list[dict[str, Any]], delimiter: str = ";") -> None:
    rows: list[dict[str, Any]] = []
    for document in documents:
        shared = {column: document[column] for column in CSV_COLUMNS if column not in {"product", "price", "qty"}}
        for item in document["items"]:
            row = dict(shared)
            row["product"] = item["product"]
            row["price"] = item["price"]
            row["qty"] = item["qty"]
            rows.append(row)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(CSV_COLUMNS),
            delimiter=delimiter,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
