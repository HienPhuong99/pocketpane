# PyInstaller spec. Build with build.bat. Output: dist\PocketPane\
#   PocketPane.exe          the app, no console window
#   pocketpane-control.exe  console: control helper + the app's pymobiledevice3 child processes
#   _internal\              Python and the libraries, shared by both
from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata

# pymobiledevice3 loads its CLI sub-commands lazily, so import analysis alone misses them
datas, binaries, hidden = collect_all("pymobiledevice3")
# its dependencies read their own version (importlib.metadata) and data files at import;
# build.bat checks that every sub-command the app uses still starts
datas += copy_metadata("pymobiledevice3", recursive=True)
datas += collect_data_files("pykdebugparser") + collect_data_files("pytun_pmd3")

# jedi and parso (23 MB) only serve tab completion in pymobiledevice3's interactive shells,
# which the app never opens; IPython runs without them
EXCLUDES = ["tkinter", "pytest", "jedi", "parso"]
# Collected by PyInstaller's Qt hook but never loaded by this app (about 30 MB): the software
# OpenGL fallback (the window is painted by Qt's raster engine), Qt's own translations (the
# interface is English), SVG, and image formats and platform plugins it does not use.
UNUSED_QT = (
    "opengl32sw.dll", "translations", "Qt6Svg", "qsvg", "qtuiotouchplugin",
    "qdirect2d", "qminimal", "qoffscreen", "qgif", "qicns", "qtga", "qtiff", "qwbmp", "qwebp",
)


def slim(toc):
    return [entry for entry in toc if "PySide6" not in entry[0] or not any(name in entry[0] for name in UNUSED_QT)]


app = Analysis(["pocketpane.pyw"], excludes=EXCLUDES)
ctl = Analysis(
    ["pocketpane_control.py"],
    datas=datas, binaries=binaries, hiddenimports=hidden, excludes=EXCLUDES,
)

exe_app = EXE(PYZ(app.pure), app.scripts, exclude_binaries=True, name="PocketPane", console=False)
exe_ctl = EXE(PYZ(ctl.pure), ctl.scripts, exclude_binaries=True, name="pocketpane-control", console=True)

COLLECT(exe_app, slim(app.binaries), slim(app.datas), exe_ctl, ctl.binaries, ctl.datas, name="PocketPane")
