"""Реестр читателей входных форматов."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pdf_generator.exceptions import UnsupportedFormatError
from pdf_generator.readers.base import BaseReader
from pdf_generator.readers.csv_reader import CsvReader
from pdf_generator.readers.json_reader import JsonReader

ReaderFactory = type[BaseReader]

READER_FACTORIES: dict[str, ReaderFactory] = {
    ".csv": CsvReader,
    ".json": JsonReader,
}


def register_reader(extension: str, reader_type: ReaderFactory) -> None:
    """Зарегистрировать читатель нового формата, не меняя генератор PDF."""
    normalized = extension.lower()
    if not normalized.startswith("."):
        normalized = f".{normalized}"
    READER_FACTORIES[normalized] = reader_type


def read_documents(path: Path, **options: Any) -> list[dict[str, Any]]:
    """Прочитать файл читателем, который соответствует его расширению."""
    extension = path.suffix.lower()
    reader_type = READER_FACTORIES.get(extension)
    if reader_type is None:
        supported = ", ".join(sorted(READER_FACTORIES))
        raise UnsupportedFormatError(
            f"Неподдерживаемое расширение файла «{path}». Поддерживаются: {supported}."
        )
    return reader_type(path, **options).read()
