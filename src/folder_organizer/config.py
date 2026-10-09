"""Settings: first-run creation of config/settings.toml and loading it with defaults."""

from __future__ import annotations

import logging
import shutil
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import time
from pathlib import Path
from typing import Any, TypeVar

from . import paths
from .day import parse_time

log = logging.getLogger(__name__)

T = TypeVar("T")

LAYOUTS = ("horizontal", "vertical")
SIDES = ("left", "right", "top", "bottom")


@dataclass(frozen=True)
class WindowSettings:
    always_on_top: bool
    opacity: float
    width: int
    layout: str  # "horizontal" | "vertical"
    permanent_first: bool  # Permanent on the left (horizontal) / top (vertical)
    start_hidden: bool


@dataclass(frozen=True)
class Settings:
    reset_time: time
    window: WindowSettings
    data_dir: Path
    max_snapshots: int


def ensure_config(
    settings_file: Path = paths.SETTINGS_FILE,
    template: Path = paths.DEFAULT_SETTINGS_FILE,
) -> bool:
    """Create the config folder and settings file from the template if missing.

    Never overwrites an existing file. Returns True if the file was created.
    """
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    if settings_file.exists():
        return False
    shutil.copyfile(template, settings_file)
    return True


def load_settings(
    settings_file: Path = paths.SETTINGS_FILE,
    template: Path = paths.DEFAULT_SETTINGS_FILE,
    project_root: Path = paths.PROJECT_ROOT,
) -> tuple[Settings, list[str]]:
    """Load settings; the template supplies every default.

    Returns the settings and a list of human-readable warnings (unreadable file,
    invalid values). Invalid values fall back to the default; the file is never changed.
    """
    with template.open("rb") as f:
        defaults = tomllib.load(f)

    warnings: list[str] = []
    user: dict[str, Any] = {}
    try:
        with settings_file.open("rb") as f:
            user = tomllib.load(f)
    except FileNotFoundError:
        pass
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError) as e:
        warnings.append(
            f"Could not read {settings_file}:\n{e}\n"
            "Using default settings. The file was not changed."
        )

    def value(section: str, key: str, convert: Callable[[Any], T]) -> T:
        default = defaults[section][key]
        table = user.get(section, {})
        if not isinstance(table, dict) or key not in table:
            return convert(default)
        try:
            return convert(table[key])
        except (TypeError, ValueError):
            warnings.append(
                f"Invalid value in {settings_file.name}: [{section}] {key} = {table[key]!r}. "
                f"Using the default {default!r}."
            )
            return convert(default)

    data_dir = Path(value("storage", "data_dir", _non_empty_str))
    if not data_dir.is_absolute():
        data_dir = project_root / data_dir

    settings = Settings(
        reset_time=value("day", "reset_time", parse_time),
        window=WindowSettings(
            always_on_top=value("window", "always_on_top", _bool),
            opacity=value("window", "opacity", _number(0.2, 1.0)),
            width=value("window", "width", _int(200, 4000)),
            layout=value("window", "layout", _choice(LAYOUTS)),
            permanent_first=value("window", "permanent_side", _choice(SIDES)) in ("left", "top"),
            start_hidden=value("window", "start_hidden", _bool),
        ),
        data_dir=data_dir,
        max_snapshots=value("permanent_history", "max_snapshots", _int(0, None)),
    )
    return settings, warnings


def _bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    raise ValueError(v)


def _int(lo: int, hi: int | None) -> Callable[[Any], int]:
    def convert(v: Any) -> int:
        if isinstance(v, bool) or not isinstance(v, int) or v < lo or (hi is not None and v > hi):
            raise ValueError(v)
        return v

    return convert


def _number(lo: float, hi: float) -> Callable[[Any], float]:
    def convert(v: Any) -> float:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
            raise ValueError(v)
        return float(v)

    return convert


def _choice(options: tuple[str, ...]) -> Callable[[Any], str]:
    def convert(v: Any) -> str:
        if isinstance(v, str) and v.strip().lower() in options:
            return v.strip().lower()
        raise ValueError(v)

    return convert


def _non_empty_str(v: Any) -> str:
    if isinstance(v, str) and v.strip():
        return v.strip()
    raise ValueError(v)
