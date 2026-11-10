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


class FrameDisplayTest(unittest.TestCase):
    def test_scaled_frame_is_shown_in_place(self):
        from av.video.reformatter import VideoReformatter

        from iphone_mirror.video import to_bgra

        win = make_window()
        # 61 px wide: ffmpeg pads the rows, so the array is a strided view, not a packed copy
        arr = to_bgra(win.rx.decoder.last_frame, (61, 130), VideoReformatter())
        self.assertEqual(arr.shape, (130, 61, 4))
        win.on_frame(arr, 60, 128)
        self.assertEqual((win.image.width(), win.image.height()), (61, 130))
        for x, y in ((0, 0), (60, 0), (0, 129), (60, 129)):  # a wrong row length would skew these
            c = win.image.pixelColor(x, y)
            self.assertEqual((c.red(), c.green(), c.blue()), (200, 0, 0), (x, y))

    def test_only_the_newest_frame_reaches_a_busy_window(self):
        bridge, got = ui.Bridge(), []
        bridge.frame.connect(lambda arr, w, h: got.append(arr))
        for i in range(3):  # three frames while the GUI thread is busy
            bridge.post_frame(i, 60, 128)
        app.processEvents()
        self.assertEqual(got, [2])
        bridge.post_frame(3, 60, 128)
        app.processEvents()
        self.assertEqual(got, [2, 3])

    def test_hidden_window_skips_scaling_and_catches_up_when_shown(self):
        win = make_window()
        win.show()
        self.assertTrue(win.rx.decoder.visible)
        win.hide()
        self.assertFalse(win.rx.decoder.visible)
        win.image = None
        win.on_frame(None, 60, 128)  # decoded while hidden: no pixels
        self.assertEqual(win.state, "mirroring")
        win.show()  # the last frame is scaled now
        self.assertEqual((win.image.width(), win.image.height()), win._target())
        win.close()

    def test_resize_scales_the_still_frame_again(self):
        win = make_window()
        win.show()
        win.set_phone_height(win.phone_h + 100)
        self.assertTrue(win._rescale_timer.isActive())
        win._rescale()
        self.assertEqual((win.image.width(), win.image.height()), win._target())
        win.close()

    def test_shadow_and_bezel_go_all_the_way_round(self):
        win = make_window()
        win.on_frame(np.full((128, 60, 4), 255, dtype=np.uint8), 60, 128)  # opaque, like a real frame
        img = win.grab().toImage()
        r = win.phone_rect().toAlignedRect()
        mid = r.center()
        for x, y in ((r.left() + 3, r.bottom() + 4), (r.right() - 3, r.bottom() + 4), (mid.x(), r.bottom() + 4),
                     (r.left() - 3, mid.y()), (r.right() + 3, mid.y()), (mid.x(), r.top() - 3)):
            self.assertGreater(img.pixelColor(x, y).alpha(), 0, (x, y))  # shadow
        self.assertLess(img.pixelColor(r.left() + 1, r.top() + 1).alpha(), 60)  # rounded corner: only shadow
        self.assertEqual(img.pixelColor(mid).alpha(), 255)


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

    def test_input_method_text_is_typed(self):
        from PySide6.QtGui import QInputMethodEvent

        win = self.window()
        self.assertTrue(win.testAttribute(Qt.WA_InputMethodEnabled))
        self.assertTrue(win.inputMethodQuery(Qt.ImEnabled))
        preview = QInputMethodEvent("vie", [])  # still composing: nothing is sent
        QApplication.sendEvent(win, preview)
        commit = QInputMethodEvent()
        commit.setCommitString("Việt Nam")
        QApplication.sendEvent(win, commit)
        win._flush_type()
        self.assertEqual(win.ctrl.calls, [("type_text", "Việt Nam")])
        win.ctrl.snapshot = lambda: (ui.OFF, "", 2)  # control off: the IME is not used for the window
        win.on_control(ui.OFF, "")
        self.assertFalse(win.testAttribute(Qt.WA_InputMethodEnabled))

    def test_composing_word_goes_out_before_a_tap(self):
        from PySide6.QtGui import QInputMethodEvent

        win = self.window()
        QApplication.sendEvent(win, QInputMethodEvent("xin", []))  # still composing
        with mock.patch.object(ui.QGuiApplication, "inputMethod") as im:
            QTest.mousePress(win, Qt.LeftButton, pos=win.phone_rect().center().toPoint())
            im.return_value.reset.assert_called_once()
        self.assertEqual(win.ctrl.calls, [("type_text", "xin")])  # sent before the tap
        commit = QInputMethodEvent()
        commit.setCommitString("xin")  # Windows commits the reset composition: not typed twice
        QApplication.sendEvent(win, commit)
        win._flush_type()
        self.assertEqual(win.ctrl.calls, [("type_text", "xin")])
        QTest.mouseRelease(win, Qt.LeftButton, pos=win.phone_rect().center().toPoint())
        win._flush_tap()
        self.assertEqual([c[0] for c in win.ctrl.calls], ["type_text", "tap"])

    def test_unikey_style_unicode_keys_and_backspace(self):
        win = self.window()
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QKeyEvent

        QTest.keyClicks(win, "vie")  # Unikey: plain keys, then Backspace + the composed letter
        QTest.keyClick(win, Qt.Key_Backspace)
        # (QTest.keyClicks crashes the interpreter on characters outside Latin-1: send the event)
        QApplication.sendEvent(win, QKeyEvent(QEvent.KeyPress, 0, Qt.NoModifier, "ệ"))
        win._flush_type()
        self.assertEqual(win.ctrl.calls, [("type_text", "vie\bệ")])

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


def wait_until(predicate, timeout=10.0):
    import time

    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)
    app.processEvents()
    return predicate()


class SetupWindowTest(unittest.TestCase):
    def report(self, failing=None):
        from iphone_mirror.control import setup

        steps = [setup.Step(k, setup.OK, "fine") for k in setup.TITLES]
        r = setup.Report(steps, device={"ProductVersion": "18.1"}, udid="U1", bundle="b")
        r.step("start").state = setup.TODO
        if failing:
            key, action = failing
            r.step(key).state, r.step(key).actions = setup.FAIL, [action]
            for later in list(setup.TITLES)[list(setup.TITLES).index(key) + 1:]:
                r.step(later).state = setup.TODO
        r.step("start").actions = [setup.A_START] if r.ready else []
        return r

    def open(self, report, **kw):
        from iphone_mirror import setup_window

        p = mock.patch.object(setup_window.setup, "check", return_value=report)
        p.start()
        self.addCleanup(p.stop)
        w = setup_window.SetupWindow(**kw)
        w.show()
        self.assertTrue(wait_until(lambda: w.report is not None))
        self.addCleanup(w.close)
        return w

    def buttons(self, w):
        from PySide6.QtWidgets import QPushButton

        return {b.text(): b for b in w.findChildren(QPushButton) if b.isVisibleTo(w)}

    def test_ready_offers_turn_on_control(self):
        started = []
        w = self.open(self.report(), start_control=lambda: started.append(1))
        self.assertIn("Everything is set up", w.status.text())
        self.buttons(w)["Turn on control"].click()
        self.assertEqual(started, [1])
        self.assertFalse(w.isVisible())

    def test_failed_step_shows_its_fix_and_runs_it_in_the_background(self):
        from iphone_mirror import setup_window
        from iphone_mirror.control import setup

        w = self.open(self.report(("wda", setup.A_GET_WDA)))
        self.assertIn("Next: WebDriverAgent installed", w.status.text())
        self.assertNotIn("Turn on control", self.buttons(w))
        with mock.patch.object(setup_window.usb, "download_wda_ipa", return_value=Path("C:/x/WDA.ipa")), \
                mock.patch.object(setup_window, "_show_in_explorer") as explorer:
            self.buttons(w)["Download WebDriverAgent"].click()
            self.assertTrue(wait_until(lambda: "Saved" in w.note.text()))
        explorer.assert_called_once()
        self.assertIsNone(w._busy)

    def test_an_unexpected_action_error_is_reported_and_kept(self):
        from iphone_mirror import setup_window
        from iphone_mirror.control import setup

        w = self.open(self.report(("wda", setup.A_GET_WDA)))
        with mock.patch.object(setup_window.usb, "download_wda_ipa", side_effect=ValueError("Bad CRC-32")):
            self.buttons(w)["Download WebDriverAgent"].click()
            self.assertTrue(wait_until(lambda: w._busy is None))
        self.assertIn("Bad CRC-32", w.note.text())
        w._on_checked(self.report(("wda", setup.A_GET_WDA)))  # later checks keep the message
        self.assertTrue(w.note.isVisible())
        self.assertIn("Bad CRC-32", w.note.text())

    def test_esc_stops_the_periodic_checks(self):
        from PySide6.QtCore import Qt as QtNS

        w = self.open(self.report())
        self.assertTrue(w._timer.isActive())
        QTest.keyClick(w, QtNS.Key_Escape)
        self.assertFalse(w.isVisible())
        self.assertFalse(w._timer.isActive())
        self.assertTrue(w._stop.is_set())

    def test_control_ready_warns_about_expiry(self):
        win = make_window()
        win._tray = None
        win.ctrl = FakeController()
        with mock.patch("iphone_mirror.control.setup.expiry_warning", return_value="WebDriverAgent expires in about 5 hours."):
            win.on_control(ui.READY, "ready")
            self.assertTrue(wait_until(lambda: "expires" in win._bar_label()))


class TrayStartTest(unittest.TestCase):
    def test_hidden_window_shows_when_an_iphone_connects(self):
        win = make_window()
        self.assertFalse(win.isVisible())
        win.on_event("connecting", {"name": "Test iPhone", "ip": "192.168.1.5"})
        self.assertTrue(win.isVisible())
        win.close()

    def test_autostart_registry_round_trip_with_a_unicode_path(self):
        from iphone_mirror import autostart

        name = "PocketPane-test"
        moved = Path("C:/Users/Phương/Ứng dụng/pocketpane")
        try:
            with mock.patch.object(autostart, "ROOT", moved):
                self.assertTrue(autostart.set_enabled(True, name))
                self.assertIn("Phương\\Ứng dụng\\pocketpane\\pocketpane.pyw", autostart.current(name))
            autostart.refresh(name)  # the folder "moved" back: the command follows it
            self.assertEqual(autostart.current(name), autostart.command())
            self.assertFalse(autostart.set_enabled(False, name))
            self.assertIsNone(autostart.current(name))
        finally:
            autostart.set_enabled(False, name)

    def test_launcher_runs_from_another_folder(self):
        import subprocess

        root = Path(__file__).resolve().parent.parent
        out = subprocess.run([sys.executable, str(root / "pocketpane.pyw"), "--help"], cwd=tempfile.gettempdir(),
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("--tray", out.stdout)


if __name__ == "__main__":
    unittest.main()
