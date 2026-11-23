"""Оркестрация: шаблон, HTML и PDF, без чтения исходных таблиц."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from pdf_generator.exceptions import (
    OutputDirectoryError,
    OutputFileExistsError,
    PdfGeneratorError,
)
from pdf_generator.loader import build_output_stem
from pdf_generator.models import Invoice
from pdf_generator.pdf_renderer import render_pdf
from pdf_generator.template_engine import TemplateEngine

logger = logging.getLogger(__name__)


class DocumentGenerator:
    """Сохранить уже нормализованные счета в HTML и/или PDF."""

    def __init__(
        self,
        template_engine: TemplateEngine,
        output_dir: Path,
        formats: tuple[str, ...],
        force: bool = False,
    ) -> None:
        unknown = [item for item in formats if item not in {"html", "pdf"}]
        if unknown or not formats:
            raise ValueError(f"Неизвестный формат результата: {', '.join(formats)}")
        self.template_engine = template_engine
        self.output_dir = output_dir
        self.formats = formats
        self.force = force

    def generate(self, invoices: list[Invoice]) -> list[Path]:
        """Создать по одному комплекту файлов на каждый счёт."""
        self._prepare_directory()
        planned = [(invoice, self._targets(invoice)) for invoice in invoices]
        if not self.force:
            existing = [path for _, paths in planned for _, path in paths if path.exists()]
            if existing:
                listed = "\n".join(str(path) for path in existing)
                raise OutputFileExistsError(
                    "Файлы уже существуют. Повторите команду с --force, "
                    f"чтобы перезаписать их:\n{listed}"
                )

        written: list[Path] = []
        for invoice, targets in planned:
            html = self.template_engine.render(invoice.to_context())
            written.extend(self._write_invoice(html, targets))
        return written

    def _targets(self, invoice: Invoice) -> list[tuple[str, Path]]:
        stem = build_output_stem(invoice.invoice_number)
        targets: list[tuple[str, Path]] = []
        if "html" in self.formats:
            targets.append(("html", self.output_dir / f"{stem}.html"))
        if "pdf" in self.formats:
            targets.append(("pdf", self.output_dir / f"{stem}.pdf"))
        return targets

    def _prepare_directory(self) -> None:
        if self.output_dir.exists() and not self.output_dir.is_dir():
            raise OutputDirectoryError(
                f"Путь вывода не является директорией: {self.output_dir}"
            )
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as exc:
            raise OutputDirectoryError(
                f"Нет прав на создание директории {self.output_dir}"
            ) from exc
        if not os.access(self.output_dir, os.W_OK):
            raise OutputDirectoryError(
                f"Нет прав на запись в директорию: {self.output_dir}"
            )

    def _write_invoice(self, html: str, targets: list[tuple[str, Path]]) -> list[Path]:
        temporary_files: list[tuple[Path, Path]] = []
        published: list[Path] = []
        try:
            for kind, destination in targets:
                temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
                if kind == "html":
                    temporary.write_text(html, encoding="utf-8", newline="\n")
                else:
                    render_pdf(
                        html,
                        temporary,
                        self.template_engine.template_path.parent,
                    )
                temporary_files.append((temporary, destination))
            for temporary, destination in temporary_files:
                temporary.replace(destination)
                logger.info("Создан документ: %s", destination)
                published.append(destination)
        except PdfGeneratorError:
            raise
        except PermissionError as exc:
            raise OutputDirectoryError(
                f"Нет прав на запись в директорию: {self.output_dir}"
            ) from exc
        except OSError as exc:
            raise OutputDirectoryError(
                f"Не удалось записать файл в {self.output_dir}: {exc}"
            ) from exc
        finally:
            for temporary, _destination in temporary_files:
                if temporary.exists():
                    temporary.unlink(missing_ok=True)
        return published
