"""Default button names that tell apart folders with the same name."""

from collections.abc import Iterable
from pathlib import Path


def suggest_label(path: str, existing_labels: Iterable[str]) -> str:
    """Suggest a name for `path` that isn't already used in `existing_labels`.

    Starts with the folder name ("renders"). If that's taken, parent folders are
    prepended until it's unique ("ProjectB / renders", "Clients / ProjectB / renders").
    The comparison ignores case.
    """
    taken = {label.strip().casefold() for label in existing_labels}
    p = Path(path)
    names = [part for part in p.parts if part != p.anchor]  # without drive / root
    for depth in range(1, len(names) + 1):
        label = " / ".join(names[-depth:])
        if label.casefold() not in taken:
            return label
    return str(p)
