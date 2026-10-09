from datetime import time

from folder_organizer import paths
from folder_organizer.config import ensure_config, load_settings

TEMPLATE = paths.DEFAULT_SETTINGS_FILE


def load(tmp_path, text=None):
    settings_file = tmp_path / "config" / "settings.toml"
    if text is not None:
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text(text, encoding="utf-8")
    return load_settings(settings_file, TEMPLATE, tmp_path)


def test_first_run_creates_config_from_template(tmp_path):
    settings_file = tmp_path / "config" / "settings.toml"
    assert ensure_config(settings_file, TEMPLATE)
    assert settings_file.read_text(encoding="utf-8") == TEMPLATE.read_text(encoding="utf-8")


def test_existing_config_is_not_overwritten(tmp_path):
    settings_file = tmp_path / "config" / "settings.toml"
    settings_file.parent.mkdir()
    settings_file.write_text('[day]\nreset_time = "05:00"\n', encoding="utf-8")
    assert not ensure_config(settings_file, TEMPLATE)
    assert settings_file.read_text(encoding="utf-8") == '[day]\nreset_time = "05:00"\n'


def test_defaults(tmp_path):
    settings, warnings = load(tmp_path)
    assert warnings == []
    assert settings.reset_time == time(4, 0)
    assert settings.window.layout == "horizontal"
    assert settings.window.permanent_first is True
    assert settings.window.width == 520
    assert settings.data_dir == tmp_path / "data"
    assert settings.max_snapshots == 1000


def test_user_values_override_and_missing_keys_use_defaults(tmp_path):
    settings, warnings = load(tmp_path, '[day]\nreset_time = "06:30"\n')
    assert warnings == []
    assert settings.reset_time == time(6, 30)
    assert settings.window.width == 520


def test_permanent_on_the_right(tmp_path):
    settings, _ = load(tmp_path, '[window]\npermanent_side = "right"\n')
    assert settings.window.permanent_first is False


def test_vertical_layout_bottom(tmp_path):
    settings, _ = load(tmp_path, '[window]\nlayout = "vertical"\npermanent_side = "bottom"\n')
    assert settings.window.layout == "vertical"
    assert settings.window.permanent_first is False


def test_invalid_values_fall_back_with_warnings(tmp_path):
    settings, warnings = load(
        tmp_path, '[day]\nreset_time = "25:99"\n[window]\nopacity = 5\nlayout = "diagonal"\n'
    )
    assert settings.reset_time == time(4, 0)
    assert settings.window.opacity == 0.95
    assert settings.window.layout == "horizontal"
    assert len(warnings) == 3


def test_broken_toml_uses_defaults_and_keeps_file(tmp_path):
    broken = "[day\nreset_time = \n"
    settings, warnings = load(tmp_path, broken)
    assert settings.reset_time == time(4, 0)
    assert len(warnings) == 1 and "settings.toml" in warnings[0]
    assert (tmp_path / "config" / "settings.toml").read_text(encoding="utf-8") == broken


def test_absolute_data_dir(tmp_path):
    target = tmp_path / "elsewhere"
    settings, _ = load(tmp_path, f"[storage]\ndata_dir = '{target}'\n")
    assert settings.data_dir == target
