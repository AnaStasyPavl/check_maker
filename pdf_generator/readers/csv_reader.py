"""Чтение счетов из CSV."""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path
from typing import Any

from pdf_generator.config import CONSISTENT_FIELDS, CSV_COLUMNS
from pdf_generator.exceptions import InvalidCsvError, ValidationError
from pdf_generator.readers.base import BaseReader

logger = logging.getLogger(__name__)

_DELIMITERS = (";", "\t", ",")


class CsvReader(BaseReader):
    """Собрать счета из построчного CSV.

    Каждая строка — один товар. Общие реквизиты повторяются в строке.
    Строки с одним ``invoice_number`` объединяются в один счёт.
    """

    def __init__(self, path: Path, delimiter: str | None = None, **options: Any) -> None:
        super().__init__(path, delimiter=delimiter, **options)
        self.delimiter = delimiter

    def _read_text(self) -> str:
        raw = self.path.read_bytes()
        for encoding in ("utf-8-sig", "cp1251"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError("utf-8", raw, 0, len(raw), "РЅРµРёР·РІРµСЃС‚РЅР°СЏ РєРѕРґРёСЂРѕРІРєР°")

    def read(self) -> list[dict[str, Any]]:
        try:
            text = self._read_text()
        except FileNotFoundError as exc:
            raise InvalidCsvError(f"Файл не найден: {self.path}") from exc
        except UnicodeDecodeError as exc:
            raise InvalidCsvError(
                f"пїЅпїЅпїЅпїЅ {self.path} РЅРµ СѓРґР°Р»РѕСЃСЊ РїСЂРѕС‡РёС‚Р°С‚СЊ РІ UTF-8 РёР»Рё CP1251: {exc.reason}"
            ) from exc
        except OSError as exc:
            raise InvalidCsvError(f"Не удалось прочитать CSV {self.path}: {exc}") from exc

        if not text.strip():
            raise InvalidCsvError(f"CSV-файл пуст: {self.path}")

        delimiter = self._resolve_delimiter(text)
        logger.info("Разделитель CSV: %s", describe_delimiter(delimiter))
        return self._parse(text, delimiter)

    def _resolve_delimiter(self, text: str) -> str:
        if self.delimiter:
            logger.debug("Разделитель задан пользователем")
            return self.delimiter
        logger.debug("Разделитель определён автоматически")
        return detect_delimiter(text)

    def _parse(self, text: str, delimiter: str) -> list[dict[str, Any]]:
        reader = csv.DictReader(
            io.StringIO(text),
            delimiter=delimiter,
            restkey="_extra",
            restval=None,
        )
        raw_names = list(reader.fieldnames or [])
        if not raw_names:
            raise InvalidCsvError(f"В CSV нет строки заголовка: {self.path}")

        fieldnames = _normalize_fieldnames(self.path, raw_names)
        key_by_raw = dict(zip(raw_names, fieldnames))
        missing = [column for column in CSV_COLUMNS if column not in fieldnames]
        if missing:
            names = ", ".join(missing)
            raise InvalidCsvError(
                f"{self.path}: в заголовке нет столбцов: {names}. "
                f"Проверьте разделитель (сейчас «{describe_delimiter(delimiter)}»)."
            )

        grouped: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        seen_data = False

        try:
            enumerated_rows = enumerate(reader, start=2)
            for line_number, row in enumerated_rows:
                extra = row.get("_extra")
                if extra:
                    raise InvalidCsvError(
                        f"{self.path}: строка {line_number}: "
                        "число столбцов больше, чем в заголовке"
                    )
                normalized = _row_values(row, fieldnames, key_by_raw)
                if all(value == "" for value in normalized.values()):
                    continue

                seen_data = True
                invoice_number = normalized.get("invoice_number", "")
                if not invoice_number:
                    raise ValidationError(
                        f"{self.path}: строка {line_number}: "
                        "отсутствует обязательное поле «invoice_number»"
                    )

                if invoice_number not in grouped:
                    document: dict[str, Any] = {
                        field: normalized.get(field, "") for field in CONSISTENT_FIELDS
                    }
                    document["items"] = []
                    document["source"] = str(self.path)
                    document["lines"] = [line_number]
                    grouped[invoice_number] = document
                    order.append(invoice_number)
                else:
                    current = grouped[invoice_number]
                    for field in CONSISTENT_FIELDS:
                        left = str(current.get(field, ""))
                        right = normalized.get(field, "")
                        if left != right:
                            raise ValidationError(
                                f"{self.path}: счёт {invoice_number}: поле «{field}» "
                                f"в строке {line_number} («{right}») не совпадает "
                                f"со значением в строке {current['lines'][0]} («{left}»)"
                            )
                    current["lines"].append(line_number)

                grouped[invoice_number]["items"].append(
                    {
                        "product": normalized.get("product", ""),
                        "price": normalized.get("price", ""),
                        "qty": normalized.get("qty", ""),
                        "line": line_number,
                        "line_kind": "строка",
                    }
                )
        except csv.Error as exc:
            raise InvalidCsvError(f"{self.path}: некорректный CSV: {exc}") from exc

        if not seen_data:
            raise InvalidCsvError(f"CSV не содержит счетов: {self.path}")

        documents: list[dict[str, Any]] = []
        for index, invoice_number in enumerate(order, start=1):
            document = grouped[invoice_number]
            document["document_index"] = index
            documents.append(document)
        return documents


def detect_delimiter(text: str) -> str:
    """Выбрать разделитель, при котором заголовок содержит колонки счёта.

    Адреса в данных часто содержат запятые, поэтому предпочтение отдаётся
    разделителю, который находит известные имена столбцов, а не просто
    самому частому символу.
    """
    header = text.splitlines()[0] if text.splitlines() else ""
    best_delimiter = ""
    best_score = (-1, -1)
    for delimiter in _DELIMITERS:
        columns = {part.strip().lstrip("\ufeff").lower() for part in header.split(delimiter)}
        matched = sum(1 for column in CSV_COLUMNS if column in columns)
        score = (matched, header.count(delimiter))
        if score > best_score:
            best_score = score
            best_delimiter = delimiter
    if best_score[0] <= 0 or not best_delimiter:
        raise InvalidCsvError(
            "Не удалось определить разделитель CSV. Укажите его через --delimiter."
        )
    return best_delimiter


def describe_delimiter(delimiter: str) -> str:
    """Понятное имя разделителя для журнала и сообщений об ошибках."""
    if delimiter == "\t":
        return "TAB"
    return delimiter


def _normalize_fieldnames(path: Path, fieldnames: list[str | None]) -> list[str]:
    names: list[str] = []
    for name in fieldnames:
        if name is None or not str(name).strip():
            raise InvalidCsvError(f"{path}: в заголовке есть пустое имя столбца")
        names.append(str(name).strip().lstrip("\ufeff").lower())
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise InvalidCsvError(f"{path}: повторяющиеся столбцы: {', '.join(duplicates)}")
    return names


def _row_values(
    row: dict[str | None, Any],
    fieldnames: list[str],
    key_by_raw: dict[str | None, str],
) -> dict[str, str]:
    normalized = {name: "" for name in fieldnames}
    for key, value in row.items():
        if key == "_extra" or key is None:
            continue
        stripped = key_by_raw.get(key)
        if stripped is None:
            continue
        normalized[stripped] = "" if value is None else str(value).strip()
    return normalized
