# Global show/hide hotkey

Status: Idea

## Context
Showing the widget from the tray takes a mouse trip. A global hotkey (e.g. `Ctrl+Alt+Space`) would toggle it from anywhere.

## Approach
- Add a config option `[app] hotkey = "Ctrl+Alt+Space"` (empty = disabled).
- On Windows, call `RegisterHotKey` via `ctypes` and handle `WM_HOTKEY` in a `QAbstractNativeEventFilter`. No extra dependency is needed.
- If registration fails because another app already uses the key, show a warning and log it.

## Open questions
- Should the hotkey also focus a quick-filter box for typing a button name? That would be a separate plan.
