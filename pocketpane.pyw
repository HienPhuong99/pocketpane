"""Starts PocketPane without a console window, from any working directory
(used by Start with Windows: pythonw pocketpane.pyw --tray)."""
import sys

from iphone_mirror.__main__ import main  # this file's folder is sys.path[0]

sys.exit(main())
