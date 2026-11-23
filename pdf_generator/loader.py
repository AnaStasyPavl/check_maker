"""Чтение входного файла и сборка списка счетов."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from pdf_generator.exceptions import InputFileNotFoundError, ValidationError
from pdf_generator.models import Invoice
from pdf_generator.normalizer import normalize_invoice
from pdf_generator.readers import read_documents

logger = logging.getLogger(__name__)

_FORMAT_NAMES = {
    ".csv": "CSV",
    ".json": "JSON",
}


def load_invoices(path: Path, delimiter: str | None = None) -> list[Invoice]:
    """Прочитать и нормализовать все счета из CSV или JSON."""
    logger.info("Обработка файла: %s", path)
    if not path.exists():
        raise InputFileNotFoundError(f"Файл не найден: {path}")
    if not path.is_file():
        raise InputFileNotFoundError(f"Ожидался файл, а не каталог: {path}")

    logger.info("Формат входных данных: %s", _FORMAT_NAMES.get(path.suffix.lower(), path.suffix))
    documents = read_documents(path, delimiter=delimiter)
    invoices = [normalize_invoice(document) for document in documents]
    _ensure_unique_numbers(invoices)
    logger.info("Найдено счетов: %d", len(invoices))
    for invoice in invoices:
        logger.info(
            "Счёт %s: товаров %d, сумма %s",
            invoice.invoice_number,
            len(invoice.items),
            f"{invoice.total:.2f}",
        )
    return invoices


def build_output_stem(invoice_number: str) -> str:
    """Безопасное имя файла без путей и служебных каталогов."""
    cleaned = re.sub(r"[^\w.-]+", "_", invoice_number.strip(), flags=re.UNICODE)
    cleaned = cleaned.strip("._") or "document"
    return f"invoice_{cleaned}"


def _ensure_unique_numbers(invoices: list[Invoice]) -> None:
    seen_numbers: dict[str, str] = {}
    seen_stems: dict[str, str] = {}
    for invoice in invoices:
        number = invoice.invoice_number
        if number in seen_numbers:
            raise ValidationError(
                f"Номер счёта «{number}» встречается несколько раз. "
                "В одном файле номера должны быть уникальными."
            )
        stem = build_output_stem(number)
        if stem in seen_stems:
            raise ValidationError(
                f"Номера «{seen_stems[stem]}» и «{number}» дают одно и то же имя файла {stem}."
            )
        seen_numbers[number] = number
        seen_stems[stem] = number
