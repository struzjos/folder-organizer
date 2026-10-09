"""Well-known locations inside the project folder."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parents[1]  # <root>/src/folder_organizer -> <root>

CONFIG_DIR = PROJECT_ROOT / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.toml"
DEFAULT_SETTINGS_FILE = PACKAGE_DIR / "default_settings.toml"
