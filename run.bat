@echo off
rem Starts PocketPane without a console window. Run install.bat once first.
pushd "%~dp0"
if not exist "%LOCALAPPDATA%\PocketPane\venv\Scripts\pythonw.exe" (
  echo PocketPane is not installed yet. Run install.bat first.
  popd
  pause
  exit /b 1
)
start "" "%LOCALAPPDATA%\PocketPane\venv\Scripts\pythonw.exe" -m iphone_mirror
popd
