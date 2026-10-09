"""Entry point: python -m folder_organizer (run.bat sets PYTHONPATH=src)."""

from __future__ import annotations

import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import paths
from .config import ensure_config, load_settings
from .storage import Storage

log = logging.getLogger("folder_organizer")


def _setup_logging(data_dir: Path) -> None:
    handlers: list[logging.Handler] = [
        RotatingFileHandler(data_dir / "folder_organizer.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    ]
    if sys.stderr is not None:  # pythonw.exe has no console
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=handlers
    )


def _log_unhandled(exc_type, exc, tb) -> None:
    log.critical("Unhandled exception", exc_info=(exc_type, exc, tb))


def _report_startup_error() -> None:
    """pythonw.exe swallows tracebacks; write them to a file and show a message box."""
    error_file = paths.PROJECT_ROOT / "folder_organizer_error.log"
    error_file.write_text(traceback.format_exc(), encoding="utf-8")
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None, f"Folder Organizer could not start.\n\nDetails: {error_file}", "Folder Organizer", 0x10
        )


def main() -> int:
    try:
        # First run: create config/ and data/ before any Qt code.
        created = ensure_config()
        settings, warnings = load_settings()
        storage = Storage(settings.data_dir, settings.max_snapshots)
        storage.ensure()
        _setup_logging(settings.data_dir)
    except Exception:
        _report_startup_error()
        raise
    sys.excepthook = _log_unhandled
    if created:
        log.info("Created %s from the default template", paths.SETTINGS_FILE)
    for warning in warnings:
        log.warning(warning)

    from .ui.app import run

    log.info("Starting (data: %s)", settings.data_dir)
    return run(settings, storage, warnings)


if __name__ == "__main__":
    sys.exit(main())
