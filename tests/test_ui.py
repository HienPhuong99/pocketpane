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


class RecordingFailureTest(unittest.TestCase):
    def test_failed_encoder_stops_recording_and_tells_the_user(self):
        win = make_window()
        win._tray = None
        rx = win.rx
        rx.recorder = SimpleNamespace(alive=False, error="disk full", seconds=3.0)

        def stop_recording():
            rx.recorder = None
            return []

        rx.stop_recording = stop_recording
        win._rec_timer.start()
        win._rec_tick()
        self.assertIsNone(rx.recorder)
        self.assertFalse(win._rec_timer.isActive())
        self.assertIn("Recording failed: disk full", win._bar_label())


class FullScreenTest(unittest.TestCase):
    def test_f11_and_esc(self):
        win = make_window()
        win.show()
        normal = win.size()
        QTest.keyClick(win, Qt.Key_F11)
        app.processEvents()
        self.assertTrue(win.fullscreen)
        r = win.phone_rect()
        self.assertAlmostEqual(r.width() / r.height(), win.aspect, places=3)
        self.assertTrue(r.right() <= win.width() + 0.5 and r.bottom() <= win.height() + 0.5)
        self.assertEqual(win.rx.decoder.target, (round(r.width() * win.devicePixelRatioF()),
                                                 round(r.height() * win.devicePixelRatioF())))
        win.set_phone_height(400)  # ignored in full screen
        QTest.mouseMove(win, r.center().toPoint())
        self.assertFalse(win.hover)  # the bar is hidden away from the top...
        close = win._buttons()["close"].center().toPoint()
        with mock.patch.object(ui.QApplication, "quit") as quit_:
            QTest.mouseClick(win, Qt.LeftButton, pos=close)  # ...so its Close button is not there
            quit_.assert_not_called()
        QTest.mouseMove(win, close)
        self.assertTrue(win.hover)  # mouse at the top: bar shown
        win._show_front()  # e.g. from the tray: stays in full screen
        app.processEvents()
        self.assertTrue(win.isFullScreen())
        QTest.keyClick(win, Qt.Key_Escape)
        app.processEvents()
        self.assertFalse(win.fullscreen)
        self.assertEqual(win.size(), normal)
        win.close()


class WindowOptionsTest(unittest.TestCase):
    def test_keep_awake_only_while_mirroring(self):
        with mock.patch.object(ui, "keep_awake") as awake:
            win = make_window()  # make_window delivers a first frame: mirroring
            awake.assert_called_once_with(True)
            win.on_event("paused", {})  # iPhone locked: no frames, let the PC sleep
            awake.assert_called_with(False)
            win.on_frame(np.zeros((128, 60, 4), dtype=np.uint8), 60, 128)  # unlocked again
            awake.assert_called_with(True)
            win.on_event("mirror_stopped", {})
            awake.assert_called_with(False)
            awake.reset_mock()
            win.settings["keep_awake"] = False
            win.on_frame(np.zeros((128, 60, 4), dtype=np.uint8), 60, 128)
            awake.assert_not_called()  # disabled: no new request

    def test_opacity_is_applied_and_saved(self):
        win = make_window()
        win._set_opacity(0.5)
        self.assertAlmostEqual(win.windowOpacity(), 0.5, places=2)
        self.assertEqual(Settings(win.settings.path)["opacity"], 0.5)


class StreamInfoTest(unittest.TestCase):
    def test_ctrl_i_toggles_the_overlay(self):
        win = make_window()
        win.rx.decoder.decoded, win.rx.decoder.dropped = 42, 1
        QTest.keyClick(win, Qt.Key_I, Qt.ControlModifier)
        self.assertTrue(win.show_stats)
        lines = win._stats_lines()
        self.assertIn("Video  60x128", lines)
        self.assertIn("Decoded  42  dropped  1", lines)
        win.grab()  # paints the overlay without errors
        QTest.keyClick(win, Qt.Key_I, Qt.ControlModifier)
        self.assertFalse(win.show_stats)

    def test_quality_is_saved_for_the_next_connection(self):
        win = make_window()
        win._set_quality(1280, 720)
        win._set_quality(fps=30)
        s = Settings(win.settings.path)
        self.assertEqual((s["width"], s["height"], s["fps"]), (1280, 720, 30))
        self.assertIn("next time", win._bar_label())


class FakeController:
    """Records the commands the window sends; always READY."""

    def __init__(self):
        self.calls = []
        self.active = True
        self.screen_aspect = None

    def snapshot(self):
        return ui.READY, "ready", 1

    def __getattr__(self, name):
        return lambda *a: self.calls.append((name, *a))


class ControlShortcutsTest(unittest.TestCase):
    def window(self):
        win = make_window()
        win.ctrl = FakeController()
        win.on_control(ui.READY, "ready")
        return win

    def test_keys_and_mouse_buttons(self):
        win = self.window()
        for key, mods in ((Qt.Key_N, Qt.ControlModifier), (Qt.Key_N, Qt.ControlModifier | Qt.ShiftModifier),
                          (Qt.Key_K, Qt.ControlModifier), (Qt.Key_L, Qt.ControlModifier),
                          (Qt.Key_B, Qt.ControlModifier)):
            QTest.keyClick(win, key, mods)
        QTest.mouseClick(win, Qt.MiddleButton, pos=win.phone_rect().center().toPoint())
        names = [c[0] for c in win.ctrl.calls]
        self.assertEqual(names, ["notification_center", "control_center", "spotlight", "lock", "back", "home"])

    def test_quick_middle_clicks_are_two_home_presses(self):
        win = self.window()
        pos = win.phone_rect().center().toPoint()
        QTest.mouseClick(win, Qt.MiddleButton, pos=pos)  # Windows: press, release,
        QTest.mouseDClick(win, Qt.MiddleButton, pos=pos)  # then a double-click event for the 2nd press
        self.assertEqual([c[0] for c in win.ctrl.calls], ["home", "home"])

    def test_paste_types_the_clipboard(self):
        win = self.window()
        QApplication.clipboard().setText("xin chào")
        QTest.keyClick(win, Qt.Key_V, Qt.ControlModifier)
        self.assertIn(("type_text", "xin chào"), win.ctrl.calls)

    def test_paste_is_limited(self):
        win = self.window()
        QApplication.clipboard().setText("a" * (ui.PASTE_MAX + 50))
        win._paste()
        self.assertEqual(len(win.ctrl.calls[-1][1]), ui.PASTE_MAX)


class TrayStartTest(unittest.TestCase):
    def test_hidden_window_shows_when_an_iphone_connects(self):
        win = make_window()
        self.assertFalse(win.isVisible())
        win.on_event("connecting", {"name": "Test iPhone", "ip": "192.168.1.5"})
        self.assertTrue(win.isVisible())
        win.close()

    def test_autostart_shortcut_round_trip(self):
        from iphone_mirror import autostart

        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(autostart.set_enabled(True, Path(d)))
            self.assertTrue(autostart.enabled(Path(d)))
            self.assertFalse(autostart.set_enabled(False, Path(d)))
            self.assertFalse(autostart.enabled(Path(d)))


if __name__ == "__main__":
    unittest.main()
