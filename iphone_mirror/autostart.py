"""Start with Windows: a value under HKCU\\...\\Run that starts the app in the tray.

The registry is Unicode, unlike WScript.Shell shortcuts (which mangle paths outside the ANSI
code page, e.g. a user folder with Vietnamese letters). The command points at this folder, so
refresh() rewrites it at every start in case the folder was moved.
"""
import logging
import os
import sys
import winreg
from pathlib import Path

from .config import APP_NAME

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent  # folder that contains the iphone_mirror package
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
LEGACY_LNK = Path(os.environ.get("APPDATA") or Path.home()) / "Microsoft/Windows/Start Menu/Programs/Startup" / f"{APP_NAME}.lnk"


def pythonw() -> str:
    exe = Path(sys.executable)
    w = exe.with_name("pythonw.exe")
    return str(w if w.exists() else exe)


def command() -> str:
    return f'"{pythonw()}" "{ROOT / "pocketpane.pyw"}" --tray'


def current(name: str = APP_NAME):
    """The registered command, or None."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def enabled(name: str = APP_NAME) -> bool:
    return current(name) is not None


def set_enabled(on: bool, name: str = APP_NAME) -> bool:
    """Register or remove the command. Returns whether it is now enabled."""
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, name, 0, winreg.REG_SZ, command())
            else:
                try:
                    winreg.DeleteValue(k, name)
                except FileNotFoundError:
                    pass
    except OSError as e:
        log.warning("could not change Start with Windows: %s", e)
    return enabled(name)


def refresh(name: str = APP_NAME):
    """At start-up: keep the command pointing at this folder and interpreter, and replace the
    Startup-folder shortcut that earlier versions created."""
    if LEGACY_LNK.exists():
        LEGACY_LNK.unlink(missing_ok=True)
        set_enabled(True, name)
    value = current(name)
    if value is not None and value != command():
        log.info("Start with Windows updated: %s", command())
        set_enabled(True, name)
