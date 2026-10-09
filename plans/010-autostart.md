# Start with Windows

Status: Idea

## Context
The widget is most useful when it is always there after login. At the moment the user has to start `run.bat` by hand.

## Approach
- Add a config option `[app] autostart = false`, plus a tray menu toggle "Start with Windows".
- When the option is enabled, create a shortcut in `shell:startup` (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`). The shortcut points to `.venv\Scripts\pythonw.exe -m folder_organizer`, with the working directory set to the project root and `PYTHONPATH=src`. Alternatively it can point to a small `start_hidden.vbs`, because a `.lnk` file can't set environment variables.
- When the option is disabled, remove the shortcut.
- Optionally start hidden in the tray when started by autostart (`--hidden` argument).

## Open questions
- Should we use a shortcut or the registry `HKCU\...\Run` key? The shortcut is easier for the user to see and remove.
