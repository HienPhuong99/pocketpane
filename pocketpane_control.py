"""Console entry of the packaged app (pocketpane-control.exe).

`pocketpane-control pmd3 ...` runs pymobiledevice3 (the app's child processes use this, see
control/usb.py); anything else is the control helper, same as control.bat."""
import sys

if sys.argv[1:2] == ["pmd3"]:
    del sys.argv[1]
    for stream in (sys.stdout, sys.stderr):
        # a frozen exe ignores PYTHONUTF8, and the app reads this output as UTF-8
        stream.reconfigure(encoding="utf-8", errors="replace")
    from pymobiledevice3.__main__ import main
else:
    from iphone_mirror.control.__main__ import main

sys.exit(main())
