"""Start with Windows: a shortcut in the user's Startup folder that runs the app in the tray."""
import logging
import os
import subprocess
import sys
from pathlib import Path

from .config import APP_NAME

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent  # folder that contains the iphone_mirror package
STARTUP = Path(os.environ.get("APPDATA") or Path.home()) / "Microsoft/Windows/Start Menu/Programs/Startup"
ARGS = "-m iphone_mirror --tray"

# the paths travel in environment variables, so no quoting is needed inside the script
_CREATE = (
    "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:PP_LNK);"
    "$s.TargetPath = $env:PP_EXE; $s.Arguments = $env:PP_ARGS; $s.WorkingDirectory = $env:PP_DIR;"
    "$s.IconLocation = $env:PP_ICON; $s.Description = 'PocketPane (AirPlay receiver)'; $s.Save()"
)


def shortcut(folder: Path = None) -> Path:
    return (folder or STARTUP) / f"{APP_NAME}.lnk"


def pythonw() -> str:
    exe = Path(sys.executable)
    w = exe.with_name("pythonw.exe")
    return str(w if w.exists() else exe)


def enabled(folder: Path = None) -> bool:
    return shortcut(folder).exists()


def set_enabled(on: bool, folder: Path = None) -> bool:
    """Create or remove the Startup shortcut. Returns whether it is now enabled."""
    lnk = shortcut(folder)
    if not on:
        lnk.unlink(missing_ok=True)
        return False
    env = dict(os.environ, PP_LNK=str(lnk), PP_EXE=pythonw(), PP_ARGS=ARGS, PP_DIR=str(ROOT),
               PP_ICON=str(ROOT / "iphone_mirror" / "icon.ico"))
    try:
        lnk.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _CREATE], env=env,
                       check=True, capture_output=True, timeout=30,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("could not create the startup shortcut: %s", e)
    return lnk.exists()
