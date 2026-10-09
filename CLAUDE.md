# FolderOrganizer

Desktop widget (Python 3.13 + PySide6) with buttons that open File Explorer on saved folders:
- **Permanent** list: always shown. Every change is saved as a snapshot in the permanent history and can be restored.
- **Daily** list: one list per logical day. A new day starts at `[day] reset_time` (default 04:00). Every day is kept and can be loaded again.

Every button has a custom name (label), because projects often contain folders with the same name (e.g. `ProjectA\renders`, `ProjectB\renders`).

## Layout rules
- Source code only in `src/folder_organizer/` (Qt UI in `src/folder_organizer/ui/`).
- Config only in `config/`. On first run, `config/settings.toml` is generated from `src/folder_organizer/default_settings.toml` and is not in git. To add a new option, add it with a comment to the template and read it in `config.py`. Missing keys fall back to the template.
- Runtime data lives in `data/`: `permanent.json`, `permanent_history/`, `daily/` and `state.json`, plus the log `folder_organizer.log`. It is created on first run and is not in git.
- The virtual env is `.venv/` in the project root. Start the app with `run.bat`.
- Tests live in `tests/`.

## Plans workflow
- All plans, current and future, go in `plans/` as `NNN-short-name.md`.
- When a plan is fully implemented and verified, move it to `plans/done/` and add `Implemented: YYYY-MM-DD` with a short note on any deviations.
- New feature ideas become new plan files in `plans/`, not just notes in chat.
- Read the relevant plan before starting work, and update it if the design changes.

## Commands
- Run: `run.bat` (creates `.venv` and installs the dependencies on first run).
- Debug run with a console (cmd): `set PYTHONPATH=src && .venv\Scripts\python -m folder_organizer`
- Tests: `.venv\Scripts\python -m pip install -r requirements-dev.txt`, then `.venv\Scripts\python -m pytest`

## Conventions
- Non-UI logic (`day.py`, `storage.py`, `naming.py`, `config.py`) must have unit tests. The UI has offscreen smoke tests in `tests/test_ui_smoke.py`.
- All data writes go through `Storage`, which uses atomic JSON writes.
- Every change to the Permanent list must go through `Storage.save_permanent(entries, action)`, so it is recorded in the history.
- Drops from Explorer must be accepted as Link/Copy, never Move. A Move would let Explorer delete the source.
