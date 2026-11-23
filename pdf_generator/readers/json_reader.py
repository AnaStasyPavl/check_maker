"""Чтение одного счёта или массива счетов из JSON."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from pdf_generator.exceptions import InvalidJsonError
from pdf_generator.readers.base import BaseReader


class JsonReader(BaseReader):
    """Прочитать JSON-объект счёта или массив таких объектов."""

    def __init__(self, path: Path, **options: Any) -> None:
        super().__init__(path, **options)

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
            raise InvalidJsonError(f"Файл не найден: {self.path}") from exc
        except UnicodeDecodeError as exc:
            raise InvalidJsonError(
                f"Р¤Р°Р№Р» {self.path} РЅРµ СѓРґР°Р»РѕСЃСЊ РїСЂРѕС‡РёС‚Р°С‚СЊ РІ UTF-8 РёР»Рё CP1251: {exc.reason}"
            ) from exc
        except OSError as exc:
            raise InvalidJsonError(f"Не удалось прочитать JSON {self.path}: {exc}") from exc

        if not text.strip():
            raise InvalidJsonError(f"JSON-файл пуст: {self.path}")

        try:
            # Decimal сохраняет десятичную запись числа и не использует float.
            payload = json.loads(text, parse_float=Decimal, parse_int=Decimal)
        except json.JSONDecodeError as exc:
            raise InvalidJsonError(
                f"Некорректный JSON в файле {self.path}: "
                f"строка {exc.lineno}, столбец {exc.colno}: {exc.msg}"
            ) from exc

        if isinstance(payload, dict):
            documents = [payload]
        elif isinstance(payload, list):
            documents = payload
        else:
            raise InvalidJsonError(
                f"{self.path}: ожидался объект счёта или массив счетов, "
                f"получен {type(payload).__name__}"
            )

        if not documents:
            raise InvalidJsonError(f"JSON не содержит счетов: {self.path}")

        prepared: list[dict[str, Any]] = []
        for index, document in enumerate(documents, start=1):
            if not isinstance(document, dict):
                raise InvalidJsonError(
                    f"{self.path}: элемент {index} должен быть объектом счёта"
                )
            prepared.append(_prepare_document(self.path, document, index))
        return prepared


def _prepare_document(path: Path, document: dict[str, Any], index: int) -> dict[str, Any]:
    raw = dict(document)
    raw["source"] = str(path)
    raw["document_index"] = index
    items = raw.get("items")
    if isinstance(items, list):
        prepared_items: list[Any] = []
        for item_index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise InvalidJsonError(
                    f"{path}: счёт {index}, позиция {item_index} должна быть объектом"
                )
            item_copy = dict(item)
            item_copy["line"] = item_index
            item_copy["line_kind"] = "позиция"
            prepared_items.append(item_copy)
        raw["items"] = prepared_items
    return raw
