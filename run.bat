@echo off
rem Starts Folder Organizer.
rem First run: creates the .venv and installs the dependencies.
rem The app itself creates config\settings.toml and data\ on its first start.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating Python virtual environment in .venv ...
    py -3.13 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 goto :error
)

rem Install / update dependencies only when requirements.txt changed
fc /b requirements.txt ".venv\requirements.installed" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies ...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 goto :error
    copy /y requirements.txt ".venv\requirements.installed" >nul
)

set "PYTHONPATH=%~dp0src"
start "" ".venv\Scripts\pythonw.exe" -m folder_organizer %*
exit /b 0

:error
echo.
echo Setup failed. See the messages above.
pause
exit /b 1
