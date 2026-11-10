"""'Set Up iPhone Control' window: the USB control checks (control/setup.py) as a checklist.

Every step shows a status light, what was found and, when it needs attention, what to do
and a button for it (open the Apple Devices store page, reveal the Developer Mode switch,
download WebDriverAgent, open Sideloadly, turn on control). The checks run on a worker
thread and repeat every few seconds while the window is open, so a step turns green by
itself once the user has done it on the iPhone.
"""
import logging
import os
import subprocess
import threading

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .control import setup, usb

log = logging.getLogger(__name__)

RECHECK_MS = 4000
APPLE_DEVICES_STORE = "ms-windows-store://pdp/?productid=9NP83LWLPZ9K"
APPLE_DEVICES_WEB = "https://apps.microsoft.com/detail/9np83lwlpz9k"
SIDELOADLY_URL = "https://sideloadly.io"

LIGHTS = {  # state -> (symbol, colour)
    setup.OK: ("✔", "#30d158"),
    setup.FAIL: ("✖", "#ff453a"),
    setup.WARN: ("!", "#ff9f0a"),
    setup.TODO: ("•", "#8e8e93"),
    setup.SKIP: ("–", "#8e8e93"),
}
BUTTONS = {
    setup.A_GET_APPLE: "Get Apple Devices",
    setup.A_REVEAL_DEV_MODE: "Show Developer Mode",
    setup.A_GET_WDA: "Download WebDriverAgent",
    setup.A_SIDELOADLY: "Open Sideloadly",
    setup.A_START: "Turn on control",
}


class StepRow(QFrame):
    def __init__(self, step_key, on_action):
        super().__init__()
        self.key = step_key
        self.on_action = on_action
        self.light = QLabel()
        self.light.setFixedWidth(22)
        self.light.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.title = QLabel(setup.TITLES[step_key])
        self.title.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        self.detail = QLabel()
        self.detail.setWordWrap(True)
        self.detail.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.how = QLabel()
        self.how.setWordWrap(True)
        self.how.setStyleSheet("color: #636366;")
        self.buttons = QHBoxLayout()
        self.buttons.setContentsMargins(0, 2, 0, 0)
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(self.title)
        text.addWidget(self.detail)
        text.addWidget(self.how)
        text.addLayout(self.buttons)
        row = QHBoxLayout(self)
        row.setContentsMargins(6, 6, 6, 6)
        row.addWidget(self.light, 0)
        row.addLayout(text, 1)
        self.light.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self._actions = None
        self.show_step(setup.Step(step_key))

    def show_step(self, step, busy=False):
        sym, colour = LIGHTS[step.state]
        self.light.setText(sym)
        self.light.setStyleSheet(f"color: {colour};")
        self.detail.setText(step.detail)
        self.detail.setVisible(bool(step.detail))
        attention = step.state in (setup.FAIL, setup.WARN) or (step.key == "start" and step.actions)
        self.how.setText(step.how if attention else "")
        self.how.setVisible(bool(attention and step.how))
        actions = tuple(step.actions)
        if actions != self._actions:
            self._actions = actions
            while self.buttons.count():
                w = self.buttons.takeAt(0).widget()
                if w is not None:
                    w.deleteLater()
            for a in actions:
                b = QPushButton(BUTTONS[a])
                b.clicked.connect(lambda _=False, a=a: self.on_action(a))
                self.buttons.addWidget(b)
            self.buttons.addStretch(1)
        for i in range(self.buttons.count()):
            w = self.buttons.itemAt(i).widget()
            if w is not None:
                w.setEnabled(not busy)


class SetupWindow(QDialog):
    checked = Signal(object)  # setup.Report, from the worker thread
    action_done = Signal(str, str)  # (action, message), from the worker thread

    def __init__(self, parent=None, start_control=None):
        super().__init__(parent)
        self.setWindowTitle("Set Up iPhone Control")
        self.setMinimumWidth(520)
        self.start_control = start_control  # callable that turns control on (the window's toggle)
        self.report = None
        self._checking = False
        self._busy = None  # action running in the background
        self._stop = threading.Event()

        intro = QLabel(
            "Controlling the iPhone with the mouse and keyboard needs a USB cable and WebDriverAgent, "
            "a small helper app installed on the iPhone with your Apple ID. Work through the list; "
            "it re-checks by itself."
        )
        intro.setWordWrap(True)
        self.rows = [StepRow(k, self._action) for k in setup.TITLES]
        box = QWidget()
        lst = QVBoxLayout(box)
        lst.setContentsMargins(0, 0, 0, 0)
        for r in self.rows:
            lst.addWidget(r)
        lst.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(box)
        self.status = QLabel("Checking...")
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        again = QPushButton("Check again")
        again.clicked.connect(self.recheck)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        bottom = QHBoxLayout()
        bottom.addWidget(self.status, 1)
        bottom.addWidget(again)
        bottom.addWidget(close)
        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(scroll, 1)
        layout.addLayout(bottom)
        self.resize(560, 640)

        self.checked.connect(self._on_checked)
        self.action_done.connect(self._on_action_done)
        self._timer = QTimer(self, interval=RECHECK_MS, timeout=self.recheck)

    # ------------------------------------------------------------ checks
    def showEvent(self, e):
        super().showEvent(e)
        self._stop.clear()
        self._timer.start()
        self.recheck()

    def closeEvent(self, e):
        self._timer.stop()
        self._stop.set()  # a running check stops its pymobiledevice3 call
        super().closeEvent(e)

    def recheck(self):
        if self._checking or self._busy:
            return
        self._checking = True
        self.status.setText("Checking...")
        threading.Thread(target=self._check_thread, name="setup-check", daemon=True).start()

    def _check_thread(self):
        try:
            report = setup.check(cancel=self._stop)
        except usb.Cancelled:
            report = None
        except Exception as e:  # never leave the window stuck in "Checking..."
            log.exception("setup check failed")
            report = setup.Report([setup.Step(k) for k in setup.TITLES])
            report.steps[0].state, report.steps[0].detail = setup.FAIL, f"Unexpected error: {e}"
        try:
            self.checked.emit(report)
        except RuntimeError:  # the window was deleted meanwhile
            pass

    def _on_checked(self, report):
        self._checking = False
        if report is None:
            return
        self.report = report
        for row, step in zip(self.rows, report.steps):
            row.show_step(step, busy=bool(self._busy))
        if self._busy:
            return
        first = next((s for s in report.steps if s.state == setup.FAIL), None)
        if report.ready:
            self.status.setText("Everything is set up. Click \"Turn on control\".")
        elif first is not None:
            self.status.setText(f"Next: {first.title}.")
        else:
            self.status.setText("")

    # ------------------------------------------------------------ actions
    def _action(self, action):
        if action == setup.A_GET_APPLE:
            if not QDesktopServices.openUrl(QUrl(APPLE_DEVICES_STORE)):
                QDesktopServices.openUrl(QUrl(APPLE_DEVICES_WEB))
        elif action == setup.A_SIDELOADLY:
            QDesktopServices.openUrl(QUrl(SIDELOADLY_URL))
        elif action == setup.A_START:
            if self.start_control is not None:
                self.start_control()
            self.close()
        elif action in (setup.A_REVEAL_DEV_MODE, setup.A_GET_WDA) and not self._busy:
            self._busy = action
            self._set_busy(True)
            self.status.setText("Working...")
            threading.Thread(target=self._action_thread, args=(action,), name="setup-action", daemon=True).start()

    def _set_busy(self, busy):
        if self.report is not None:
            for row, step in zip(self.rows, self.report.steps):
                row.show_step(step, busy=busy)

    def _action_thread(self, action):
        try:
            if action == setup.A_REVEAL_DEV_MODE:
                udid = self.report.udid if self.report else None
                code, out, err = usb.pmd3("amfi", "reveal-developer-mode", "--udid", udid, timeout=60)
                msg = ("The Developer Mode switch is now visible. On the iPhone: Settings > Privacy & Security > "
                       "Developer Mode > On, then Restart. After the restart unlock it and tap Turn On."
                       if code == 0 else usb.failure_text(err or out, "Could not show the Developer Mode switch"))
            else:
                path = usb.download_wda_ipa(progress=lambda m: None)
                msg = f"Saved {path}. Install it with Sideloadly using your Apple ID."
                _show_in_explorer(path)
        except usb.UsbError as e:
            msg = str(e)
        except OSError as e:
            msg = f"Failed: {e}"
        try:
            self.action_done.emit(action, msg)
        except RuntimeError:
            pass

    def _on_action_done(self, action, message):
        self._busy = None
        self.status.setText(message)
        self._set_busy(False)
        QTimer.singleShot(1500, self.recheck)


def _show_in_explorer(path):
    try:
        subprocess.Popen(["explorer", "/select,", str(path)])
    except OSError:
        os.startfile(str(path.parent))
