"""Window tests (offscreen Qt, no iPhone). Run:  python -m pytest tests"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import av  # noqa: E402
import numpy as np  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from iphone_mirror import ui  # noqa: E402
from iphone_mirror.config import Settings  # noqa: E402

app = QApplication.instance() or QApplication([])


class FakeReceiver:
    def __init__(self):
        img = np.zeros((128, 60, 3), dtype=np.uint8)
        img[:, :, 0] = 200
        self.decoder = SimpleNamespace(last_frame=av.VideoFrame.from_ndarray(img, format="rgb24"), target=None)
        self.recorder = None
        self.muted = False


def make_window():
    tmp = tempfile.mkdtemp()
    win = ui.PhoneWindow(Settings(Path(tmp) / "s.json"), None)
    win.rx = FakeReceiver()
    win.on_frame(np.zeros((128, 60, 4), dtype=np.uint8), 60, 128)
    return win


class ScreenshotTest(unittest.TestCase):
    def test_copy_to_clipboard(self):
        win = make_window()
        QApplication.clipboard().clear()
        QTest.keyClick(win, Qt.Key_S, Qt.ControlModifier | Qt.ShiftModifier)
        img = QApplication.clipboard().image()
        self.assertEqual((img.width(), img.height()), (60, 128))  # full-resolution frame, not the window

    def test_save_file(self):
        win = make_window()
        with tempfile.TemporaryDirectory() as d, mock.patch.object(ui.Path, "home", return_value=Path(d)):
            QTest.keyClick(win, Qt.Key_S, Qt.ControlModifier)
            files = list((Path(d) / "Pictures" / ui.APP_NAME).glob("*.png"))
        self.assertEqual(len(files), 1)

    def test_nothing_to_capture_without_a_frame(self):
        win = make_window()
        win.on_event("mirror_stopped", {})
        QApplication.clipboard().clear()
        win.copy_screenshot()
        self.assertTrue(QApplication.clipboard().image().isNull())
        self.assertIn("Nothing", win._bar_label())


if __name__ == "__main__":
    unittest.main()
