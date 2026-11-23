"""Константы и описание полей документа."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = PROJECT_ROOT / "templates" / "invoice.html"
DEFAULT_OUTPUT_DIR = Path("output")

MONEY_QUANTUM = Decimal("0.01")

SUPPORTED_EXTENSIONS = (".csv", ".json")
OUTPUT_FORMATS = ("pdf", "html", "both")

REQUIRED_INVOICE_FIELDS: tuple[str, ...] = (
    "invoice_number",
    "invoice_date",
    "seller_name",
    "seller_inn",
    "seller_address",
    "seller_phone",
    "buyer_name",
    "buyer_inn",
    "buyer_address",
    "bank_name",
    "bik",
    "bank_account",
    "correspondent_account",
    "payment_days",
)

REQUIRED_ITEM_FIELDS: tuple[str, ...] = ("product", "price", "qty")

# Реквизиты, которые в CSV должны совпадать у всех строк одного счёта.
CONSISTENT_FIELDS: tuple[str, ...] = REQUIRED_INVOICE_FIELDS

STRING_INVOICE_FIELDS: tuple[str, ...] = tuple(
    field for field in REQUIRED_INVOICE_FIELDS if field != "payment_days"
)

ACCOUNT_FIELDS: tuple[str, ...] = ("bik", "bank_account", "correspondent_account")

CSV_COLUMNS: tuple[str, ...] = REQUIRED_INVOICE_FIELDS + REQUIRED_ITEM_FIELDS
