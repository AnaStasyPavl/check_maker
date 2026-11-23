"""Преобразование готового HTML в PDF через WeasyPrint."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path

from pdf_generator.exceptions import PdfRenderError

_glib_log_library: ctypes.CDLL | None = None
_glib_log_handler: object | None = None
_glib_dll_directory_handles: list[object] = []


def _suppress_known_gio_warning() -> None:
    global _glib_log_library, _glib_log_handler

    if os.name != "nt" or _glib_log_handler is not None:
        return

    dll_directories = os.getenv(
        "WEASYPRINT_DLL_DIRECTORIES",
        "C:\\msys64\\ucrt64\\bin;"
        "C:\\msys64\\mingw64\\bin;"
        "C:\\Program Files\\GTK3-Runtime Win64\\bin",
    ).split(";")
    for directory in dll_directories:
        if os.path.isdir(directory) and hasattr(os, "add_dll_directory"):
            _glib_dll_directory_handles.append(os.add_dll_directory(directory))

    glib = None
    for directory in dll_directories:
        candidate = Path(directory) / "libglib-2.0-0.dll"
        if candidate.is_file():
            try:
                glib = ctypes.CDLL(str(candidate))
                break
            except OSError:
                continue
    if glib is None:
        try:
            glib = ctypes.CDLL("libglib-2.0-0.dll")
        except OSError:
            return

    log_handler_type = ctypes.CFUNCTYPE(
        None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p
    )
    glib.g_log_default_handler.argtypes = [
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_void_p,
    ]
    glib.g_log_default_handler.restype = None

    def handle_gio_warning(
        domain: bytes | None,
        level: int,
        message: bytes | None,
        user_data: int | None,
    ) -> None:
        if (
            message is not None
            and message.startswith(b"Unexpectedly, UWP app `")
            and message.endswith(b" supports 4 extensions but has no verbs")
        ):
            return
        glib.g_log_default_handler(domain, level, message, user_data)

    handler = log_handler_type(handle_gio_warning)
    glib.g_log_set_handler.argtypes = [
        ctypes.c_char_p,
        ctypes.c_int,
        log_handler_type,
        ctypes.c_void_p,
    ]
    glib.g_log_set_handler.restype = ctypes.c_uint
    glib.g_log_set_handler(b"GLib-GIO", 1 << 4, handler, None)
    _glib_log_library = glib
    _glib_log_handler = handler


def render_pdf(html: str, destination: Path, base_url: Path) -> None:
    """Записать PDF. HTML уже содержит стили страницы и данные счёта."""
    _suppress_known_gio_warning()
    try:
        from weasyprint import HTML
    except Exception as exc:
        raise PdfRenderError(
            "Не удалось загрузить WeasyPrint. Установите пакет и системные "
            f"библиотеки Pango. Подробности: {exc}"
        ) from exc

    try:
        HTML(string=html, base_url=str(base_url.resolve())).write_pdf(destination)
    except Exception as exc:
        raise PdfRenderError(
            f"Ошибка WeasyPrint при создании «{destination}»: {exc}"
        ) from exc
