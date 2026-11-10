@echo off
rem Builds dist\PocketPane\PocketPane.exe. Needs Python 3.11+ on PATH (a developer task).
rem Uses its own environment in .venv, not the app's one under %LOCALAPPDATA%: when Windows
rem virtualizes that folder (it was created from a Store-packaged app), PyInstaller collects
rem no Qt plugins and the built app cannot start.
setlocal
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
    python -m venv .venv || exit /b 1
)
"%PY%" -m pip install --quiet --disable-pip-version-check -r requirements.txt pyinstaller || exit /b 1
rem PyInstaller silently leaves out a module that has a syntax error
"%PY%" -m compileall -q iphone_mirror pocketpane.pyw pocketpane_control.py || exit /b 1
"%PY%" -m PyInstaller --noconfirm --clean pocketpane.spec || exit /b 1
rem smoke checks: Qt's platform plugin was collected, and every pymobiledevice3 sub-command
rem the app runs (control\usb.py) starts
if not exist dist\PocketPane\_internal\PySide6\plugins\platforms\qwindows.dll (
    echo FAILED: Qt platform plugin missing from the build
    exit /b 1
)
for %%C in ("usbmux list" "usbmux forward" "amfi developer-mode-status" "amfi reveal-developer-mode" "apps list" "provision list" "mounter auto-mount" "developer dvt xcuitest") do (
    dist\PocketPane\pocketpane-control.exe pmd3 %%~C --help >nul || (echo FAILED: pmd3 %%~C & exit /b 1)
)
echo.
echo Built dist\PocketPane\PocketPane.exe
