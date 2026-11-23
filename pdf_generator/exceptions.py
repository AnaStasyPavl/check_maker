"""Исключения генератора документов.

Обычный запуск показывает только текст этих ошибок. Полный traceback
включается параметром ``--debug``.
"""

from __future__ import annotations


class PdfGeneratorError(Exception):
    """Базовая ошибка обработки или генерации. Код завершения — 1."""


class InputFileNotFoundError(PdfGeneratorError):
    """Входной файл не существует или не является файлом."""


class UnsupportedFormatError(PdfGeneratorError):
    """Расширение входного файла не поддерживается."""


class InvalidJsonError(PdfGeneratorError):
    """JSON повреждён или имеет неверную структуру."""


class InvalidCsvError(PdfGeneratorError):
    """CSV не удаётся разобрать или в нём нет нужных столбцов."""


class ValidationError(PdfGeneratorError):
    """Данные документа не проходят проверки."""

    def __init__(self, message: str | list[str]) -> None:
        if isinstance(message, list):
            cleaned = [item.strip() for item in message if item and item.strip()]
            self.messages = cleaned or ["Данные документа не прошли проверку."]
            text = "\n".join(self.messages)
        else:
            self.messages = [message]
            text = message
        super().__init__(text)


class TemplateNotFoundError(PdfGeneratorError):
    """HTML-шаблон не найден."""


class TemplateRenderError(PdfGeneratorError):
    """Jinja2 не смог обработать шаблон."""


class PdfRenderError(PdfGeneratorError):
    """WeasyPrint не смог создать PDF."""


class OutputDirectoryError(PdfGeneratorError):
    """Выходную директорию нельзя создать или в неё нельзя записать файл."""


class OutputFileExistsError(PdfGeneratorError):
    """Файл результата уже есть, а перезапись не разрешена."""
