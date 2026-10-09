import sys

import pytest

from folder_organizer.naming import suggest_label

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="uses Windows paths")


def test_unique_name_is_folder_name():
    assert suggest_label(r"D:\Projects\A\renders", []) == "renders"


def test_same_folder_name_adds_parent():
    assert suggest_label(r"D:\Projects\B\renders", ["renders"]) == "B / renders"


def test_deeper_collision_adds_more_parents():
    assert suggest_label(r"D:\Clients\B\renders", ["renders", "B / renders"]) == "Clients / B / renders"


def test_comparison_ignores_case():
    assert suggest_label(r"D:\x\Renders", ["RENDERS"]) == "x / Renders"


def test_drive_root():
    assert suggest_label("D:\\", []) == "D:\\"


def test_everything_taken_falls_back_to_full_path():
    assert suggest_label(r"D:\a\b", ["b", "a / b"]) == r"D:\a\b"
