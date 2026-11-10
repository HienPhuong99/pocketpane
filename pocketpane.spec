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

app = Analysis(["pocketpane.pyw"], excludes=["tkinter", "pytest"])
ctl = Analysis(
    ["pocketpane_control.py"],
    datas=datas, binaries=binaries, hiddenimports=hidden, excludes=["tkinter", "pytest"],
)

exe_app = EXE(PYZ(app.pure), app.scripts, exclude_binaries=True, name="PocketPane", console=False)
exe_ctl = EXE(PYZ(ctl.pure), ctl.scripts, exclude_binaries=True, name="pocketpane-control", console=True)

COLLECT(exe_app, app.binaries, app.datas, exe_ctl, ctl.binaries, ctl.datas, name="PocketPane")
