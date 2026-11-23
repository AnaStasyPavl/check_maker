"""Общий интерфейс чтения исходных документов."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseReader(ABC):
    """Читатель, который возвращает сырые документы до нормализации."""

    def __init__(self, path: Path, **options: Any) -> None:
        self.path = path
        self.options = options

    @abstractmethod
    def read(self) -> list[dict[str, Any]]:
        """Вернуть список счетов в промежуточном виде.

        У каждого документа есть реквизиты, список ``items`` и служебные
        поля ``source`` и ``document_index``. Суммы ещё не вычислены.
        """
