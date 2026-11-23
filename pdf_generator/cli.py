"""CLI for PDF invoice generation."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

from pdf_generator import __version__
from pdf_generator.config import DEFAULT_TEMPLATE
from pdf_generator.exceptions import PdfGeneratorError
from pdf_generator.generator import DocumentGenerator
from pdf_generator.loader import load_invoices
from pdf_generator.template_engine import TemplateEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="Generate PDF and HTML documents from CSV or JSON.",
    )
    parser.add_argument("--version", action="version", version=f"pdf-generator {__version__}")
    commands = parser.add_subparsers(dest="command", required=False)

    generate = commands.add_parser("generate", help="Generate documents")
    generate.add_argument("--input", required=True, type=Path)
    generate.add_argument("--template", type=Path, default=None)
    generate.add_argument("--output-dir", type=Path, default=Path("output"))
    generate.add_argument("--format", choices=("pdf", "html", "both"), default="pdf")
    generate.add_argument("--delimiter", type=_delimiter_type, default=None)
    generate.add_argument("--force", action="store_true")
    generate.add_argument("--verbose", action="store_true")
    generate.add_argument("--debug", action="store_true")

    validate = commands.add_parser("validate", help="Validate input")
    validate.add_argument("--input", required=True, type=Path)
    validate.add_argument("--delimiter", type=_delimiter_type, default=None)
    validate.add_argument("--verbose", action="store_true")
    validate.add_argument("--debug", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    configure_logging(False)
    parser = build_parser()

    if argv is None and len(sys.argv) == 1:
        return _command_interactive()

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    configure_logging(bool(getattr(args, "verbose", False)))
    try:
        if args.command == "generate":
            return _command_generate(args)
        if args.command == "validate":
            return _command_validate(args)
    except PdfGeneratorError as exc:
        logging.getLogger("pdf_generator").error("%s", exc)
        return 1
    except Exception as exc:
        logging.getLogger("pdf_generator").error("Unexpected error: %s", exc)
        if getattr(args, "debug", False):
            raise
        return 1
    return 2


def configure_logging(verbose: bool) -> None:
    package_logger = logging.getLogger("pdf_generator")
    package_logger.handlers.clear()
    package_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    package_logger.propagate = False
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    package_logger.addHandler(handler)


def _command_generate(args: argparse.Namespace) -> int:
    source = _resolve_path(args.input)
    template_path = _resolve_path(args.template) if args.template else DEFAULT_TEMPLATE
    output_dir = _resolve_path(args.output_dir)
    invoices = load_invoices(source, delimiter=args.delimiter)
    engine = TemplateEngine(template_path)
    formats = ("html", "pdf") if args.format == "both" else (args.format,)
    generator = DocumentGenerator(engine, output_dir, formats, force=bool(args.force))
    generator.generate(invoices)
    return 0


def _command_validate(args: argparse.Namespace) -> int:
    source = _resolve_path(args.input)
    invoices = load_invoices(source, delimiter=args.delimiter)
    logger = logging.getLogger("pdf_generator")
    logger.info("Файл проверен: %s", source)
    logger.info("Количество счетов: %d", len(invoices))
    return 0


def _command_interactive() -> int:
    data_dir = _resolve_path(Path("data"))
    template_dir = _resolve_path(Path("templates"))
    output_dir = _resolve_path(Path("output"))

    data_files = sorted(
        (p for p in data_dir.iterdir() if p.is_file() and p.suffix.lower() in {".csv", ".json"})
        if data_dir.is_dir() else [],
        key=lambda p: p.name.lower(),
    )
    template_files = sorted(
        (p for p in template_dir.iterdir() if p.is_file() and p.suffix.lower() == ".html")
        if template_dir.is_dir() else [],
        key=lambda p: p.name.lower(),
    )

    print("\n=== Генератор PDF-документов ===")
    print("\nДоступные файлы с данными:")
    if not data_files:
        print("  Файлы CSV/JSON в директории data не найдены.")
        return 1
    _print_numbered(data_files)

    print("\nДоступные HTML-шаблоны:")
    if not template_files:
        print("  Файлы HTML в директории templates не найдены.")
        return 1
    _print_numbered(template_files)

    data_path = _choose_path("Выберите файл данных", data_files)
    if data_path is None:
        return 0
    template_path = _choose_path("Выберите HTML-шаблон", template_files)
    if template_path is None:
        return 0

    try:
        invoices = load_invoices(data_path)
    except PdfGeneratorError as exc:
        logging.getLogger("pdf_generator").error("%s", exc)
        return 1

    print("\nДоступные invoice id:")
    for index, invoice in enumerate(invoices, start=1):
        print(f"  {index}. {invoice.invoice_number}")
    invoice = _choose_invoice("Выберите invoice id", invoices)
    if invoice is None:
        return 0

    try:
        engine = TemplateEngine(template_path)
        generator = DocumentGenerator(engine, output_dir, ("pdf",), force=True)
        written = generator.generate([invoice])
    except PdfGeneratorError as exc:
        logging.getLogger("pdf_generator").error("%s", exc)
        return 1

    pdf_path = next((path for path in written if path.suffix.lower() == ".pdf"), None)
    if pdf_path:
        print(f"\nPDF сохранён: {pdf_path}")
        _open_file(pdf_path)
    return 0


def _print_numbered(paths: list[Path]) -> None:
    for index, path in enumerate(paths, start=1):
        print(f"  {index}. {path.name}")


def _choose_path(prompt: str, choices: list[Path]) -> Path | None:
    while True:
        answer = input(f"\n{prompt} (1-{len(choices)}, 0 - выход): ").strip()
        if answer == "0":
            return None
        try:
            index = int(answer)
        except ValueError:
            print("Введите номер из списка.")
            continue
        if 1 <= index <= len(choices):
            return choices[index - 1]
        print("Номер вне допустимого диапазона.")


def _choose_invoice(prompt: str, invoices: list[object]) -> object | None:
    while True:
        answer = input(f"\n{prompt} (1-{len(invoices)}, 0 - выход): ").strip()
        if answer == "0":
            return None
        try:
            index = int(answer)
        except ValueError:
            print("Введите номер из списка.")
            continue
        if 1 <= index <= len(invoices):
            return invoices[index - 1]
        print("Номер вне допустимого диапазона.")


def _open_file(path: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except OSError as exc:
        logging.getLogger("pdf_generator").warning(
            "Не удалось открыть PDF автоматически: %s", exc
        )


def _resolve_path(path: Path) -> Path:
    return path.expanduser().resolve()


def _delimiter_type(value: str) -> str:
    if value.lower() in {"\\t", "tab"}:
        return "\t"
    if len(value) != 1:
        raise argparse.ArgumentTypeError("Разделитель должен быть одним символом или TAB.")
    return value


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass
