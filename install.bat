@echo off
setlocal
rem PocketPane installer.
rem Creates a Python environment in %LOCALAPPDATA%\PocketPane\venv, installs the
rem dependencies and creates "PocketPane" shortcuts (Desktop + Start menu) that
rem point at this folder. Run it again after moving the folder.
rem If no Python 3.11+ is installed, a private copy of Python 3.12 (the official
rem "python" package on nuget.org, checked against its SHA-256) is downloaded into
rem %LOCALAPPDATA%\PocketPane\python. Nothing is added to PATH.

set "APPDIR=%~dp0"
if "%APPDIR:~-1%"=="\" set "APPDIR=%APPDIR:~0,-1%"
set "DATA=%LOCALAPPDATA%\PocketPane"
set "VENV=%DATA%\venv"
set "PORTABLE=%DATA%\python\tools\python.exe"
set "PY_URL=https://www.nuget.org/api/v2/package/python/3.12.10"
set "PY_SHA256=0eb85c2dfccccf1b17352de4c397f69194035b7d37149eacc16f1147d93de3b8"
set "PAUSE=pause"
if defined PP_NOPAUSE set "PAUSE=cd ."

rem --- find Python 3.11+. The Microsoft Store "python" alias is only an installer
rem --- stub: running it fails, so every candidate is actually run, not just looked up.
set "PY="
call :try_python python
call :try_python py -3
call :try_python "%PORTABLE%"
if not defined PY call :get_python || (%PAUSE% & exit /b 1)
echo Using Python: %PY%

if not exist "%VENV%\Scripts\python.exe" (
  echo Creating the Python environment in "%VENV%" ...
  %PY% -m venv --without-pip "%VENV%" || (%PAUSE% & exit /b 1)
)

echo Installing the dependencies (this can take a few minutes)...
%PY% -m pip --python "%VENV%\Scripts\python.exe" install -q --upgrade pip -r "%APPDIR%\requirements.txt" || (%PAUSE% & exit /b 1)

echo Creating the shortcuts...
set "PP_EXE=%VENV%\Scripts\pythonw.exe"
set "PP_ARGS=-m iphone_mirror"
set "PP_DIR=%APPDIR%"
set "PP_ICON=%APPDIR%\iphone_mirror\icon.ico"
set "PP_NAME=PocketPane"
powershell -NoProfile -ExecutionPolicy Bypass -File "%APPDIR%\tools\shortcuts.ps1" || (
  echo Could not create the shortcuts. You can still start the app with run.bat.
  %PAUSE% & exit /b 1
)

echo.
echo Done. Start "PocketPane" from the Desktop or the Start menu.
%PAUSE%
exit /b 0

:try_python
if defined PY exit /b 0
%* -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul && set "PY=%*"
exit /b 0

:get_python
echo Python 3.11 or newer was not found.
echo Downloading a private copy of Python 3.12 (about 15 MB) into "%DATA%\python" ...
set "PP_PY_URL=%PY_URL%"
set "PP_PY_SHA256=%PY_SHA256%"
set "PP_PY_DIR=%DATA%\python"
powershell -NoProfile -ExecutionPolicy Bypass -File "%APPDIR%\tools\get_python.ps1" || goto :get_python_failed
call :try_python "%PORTABLE%"
if defined PY exit /b 0
:get_python_failed
echo Could not set up Python automatically. Install Python 3.11 or newer from
echo https://www.python.org/downloads/ (tick "Add python.exe to PATH") and run install.bat again.
exit /b 1
