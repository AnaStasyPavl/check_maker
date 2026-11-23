"""Загрузка шаблона Jinja2 и подстановка данных счёта."""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

from jinja2 import FileSystemLoader, StrictUndefined, TemplateError
from jinja2.sandbox import SandboxedEnvironment

from pdf_generator.exceptions import TemplateNotFoundError, TemplateRenderError
from pdf_generator.validators import quantize_money

logger = logging.getLogger(__name__)

_FONT_CANDIDATES: tuple[tuple[Path, Path], ...] = (
    (
        Path(r"C:\Windows\Fonts\DejaVuSans.ttf"),
        Path(r"C:\Windows\Fonts\DejaVuSans-Bold.ttf"),
    ),
    (
        Path("/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf"),
        Path("/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf"),
    ),
    (
        Path("/Library/Fonts/Roboto-Regular.ttf"),
        Path("/Library/Fonts/Roboto-Bold.ttf"),
    ),
    (
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
    ),
    (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ),
    (
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ),
    (
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ),
    (
        Path("/Library/Fonts/Arial.ttf"),
        Path("/Library/Fonts/Arial Bold.ttf"),
    ),
)


class TemplateEngine:
    """Отрисовать HTML по файлу шаблона.

    Данные пользователя попадают в шаблон как значения переменных и
    экранируются. Шаблон выполняется в песочнице Jinja2 и не получает
    доступ к файлам и произвольному Python-коду из исходных данных.
    """

    def __init__(self, template_path: Path) -> None:
        self.template_path = template_path
        if not template_path.is_file():
            raise TemplateNotFoundError(f"HTML-шаблон не найден: {template_path}")

        self.font_url, self.font_bold_url = find_cyrillic_fonts()
        self._environment = SandboxedEnvironment(
            autoescape=True,
            undefined=StrictUndefined,
            loader=FileSystemLoader(str(template_path.parent)),
        )
        self._environment.filters["money"] = _money_filter
        try:
            self._template = self._environment.get_template(template_path.name)
        except TemplateError as exc:
            raise TemplateRenderError(
                f"Ошибка шаблона «{template_path}»: {exc}"
            ) from exc

    def render(self, context: dict[str, Any]) -> str:
        """Вернуть HTML-строку. Суммы в контексте уже посчитаны."""
        payload = dict(context)
        payload.setdefault("font_url", self.font_url)
        payload.setdefault("font_bold_url", self.font_bold_url or self.font_url)
        try:
            return self._template.render(**payload)
        except TemplateError as exc:
            raise TemplateRenderError(
                f"Ошибка шаблона «{self.template_path}»: {exc}"
            ) from exc


def find_cyrillic_fonts() -> tuple[str | None, str | None]:
    """Найти установленный шрифт с кириллицей и вернуть file-URI для CSS."""
    for regular, bold in _FONT_CANDIDATES:
        if regular.is_file():
            bold_path = bold if bold.is_file() else regular
            logger.debug("Шрифт для PDF: %s", regular)
            return regular.as_uri(), bold_path.as_uri()
    logger.warning(
        "Не найден системный шрифт с кириллицей (Arial или DejaVu Sans). "
        "В PDF русские буквы могут отобразиться пустыми квадратами."
    )
    return None, None


def _money_filter(value: Any) -> str:
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    return f"{quantize_money(amount):.2f}"
