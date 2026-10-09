# Single instance

Status: Idea

## Context
If `run.bat` is started twice, two widgets write the same `data/` files and the last write wins. A change made in one window can then be overwritten by the other.

## Approach
- At startup, try to connect a `QLocalSocket` to the server name `folder-organizer-<hash of project root>`.
  - If the connection succeeds, send "show" and exit. The running instance then calls `show_and_raise()`.
  - If it fails, start a `QLocalServer` with that name and continue starting normally.
- Call `QLocalServer.removeServer(name)` before `listen`, to recover after a crash.

## Verification
Start `run.bat` twice. Only one widget should exist, and it should come to the front.
