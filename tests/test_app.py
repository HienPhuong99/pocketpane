"""Tests for the PocketPane additions that do not need an iPhone. Run:  python -m pytest tests"""
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import av  # noqa: E402
import numpy as np  # noqa: E402

from iphone_mirror import config, record  # noqa: E402


class MigrateSettingsTest(unittest.TestCase):
    def test_copies_old_settings_once(self):
        with tempfile.TemporaryDirectory() as d:
            old, new = Path(d) / "old" / "settings.json", Path(d) / "new" / "settings.json"
            old.parent.mkdir()
            old.write_text(json.dumps({"name": "Desk", "mac": "021122334455"}), encoding="utf-8")
            self.assertTrue(config.migrate_old_settings(new, old))
            self.assertEqual(json.loads(new.read_text(encoding="utf-8"))["mac"], "021122334455")
            old.write_text(json.dumps({"name": "Other"}), encoding="utf-8")
            self.assertFalse(config.migrate_old_settings(new, old))  # never overwrites
            self.assertEqual(json.loads(new.read_text(encoding="utf-8"))["name"], "Desk")

    def test_nothing_to_migrate(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(config.migrate_old_settings(Path(d) / "a.json", Path(d) / "missing.json"))


def _frame(w, h, i):
    img = np.full((h, w, 3), (i * 7) % 256, dtype=np.uint8)
    return av.VideoFrame.from_ndarray(img, format="rgb24").reformat(format="yuv420p")


class RecorderTest(unittest.TestCase):
    def test_records_video_and_audio(self):
        with tempfile.TemporaryDirectory() as d:
            rec = record.Recorder(Path(d), audio=True, stamp="test")
            for i in range(12):
                rec._last_video = -1  # bypass the frame-rate cap: frames come faster than real time here
                rec.video(_frame(321, 641, i))  # odd sizes are cropped to even ones
                rec.audio(np.zeros((1024, 2), dtype=np.int16))
                time.sleep(0.01)
            paths = rec.stop()
            self.assertEqual([p.name for p in paths], ["iPhone test.mp4"])
            with av.open(str(paths[0])) as f:
                v = f.streams.video[0]
                self.assertEqual((v.width, v.height), (320, 640))
                self.assertEqual(len(f.streams.audio), 1)
                self.assertGreaterEqual(sum(1 for _ in f.decode(video=0)), 10)

    def test_rotation_starts_a_new_part(self):
        with tempfile.TemporaryDirectory() as d:
            rec = record.Recorder(Path(d), audio=False, stamp="rot")
            for i, size in enumerate([(200, 400)] * 3 + [(400, 200)] * 3):
                rec._last_video = -1
                rec.video(_frame(*size, i))
            paths = rec.stop()
            self.assertEqual([p.name for p in paths], ["iPhone rot.mp4", "iPhone rot (2).mp4"])
            with av.open(str(paths[1])) as f:
                self.assertEqual(f.streams.video[0].width, 400)

    def test_stop_does_not_hang_when_the_encoder_died(self):
        with tempfile.TemporaryDirectory() as d:
            blocker = Path(d) / "file"
            blocker.write_text("x")
            rec = record.Recorder(blocker, audio=True, stamp="dead")  # folder is a file: mkdir fails
            for i in range(record.QUEUE + 50):
                rec._last_video = -1
                rec.video(_frame(64, 64, i))
                rec.audio(np.zeros((1024, 2), dtype=np.int16))
            t = time.monotonic()
            self.assertEqual(rec.stop(), [])
            self.assertLess(time.monotonic() - t, 3)
            self.assertFalse(rec.alive)
            self.assertTrue(rec.error)

    def test_audio_is_never_dropped(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(record, "QUEUE", 2):
            rec = record.Recorder(Path(d), audio=True, stamp="aud")
            rec._last_video = -1
            rec.video(_frame(64, 64, 0))
            for _ in range(40):
                rec.audio(np.full((1024, 2), 1000, dtype=np.int16))
                rec._last_video = -1
                rec.video(_frame(64, 64, 1))  # mostly dropped: the queue is tiny
            paths = rec.stop()
            with av.open(str(paths[0])) as f:
                samples = sum(fr.samples for fr in f.decode(audio=0))
        self.assertGreater(rec.dropped, 0)
        self.assertGreaterEqual(samples, 39 * 1024)

    def test_a_killed_recording_is_still_playable(self):
        with tempfile.TemporaryDirectory() as d:
            code = (
                "import sys, time, os, av, numpy as np\n"
                f"sys.path.insert(0, {str(Path(__file__).resolve().parent.parent)!r})\n"
                "from iphone_mirror import record\n"
                f"rec = record.Recorder({d!r}, audio=True, stamp='kill')\n"
                "for i in range(150):\n"
                "    img = np.full((64, 64, 3), i % 256, np.uint8)\n"
                "    rec.video(av.VideoFrame.from_ndarray(img, format='rgb24'))\n"
                "    rec.audio(np.zeros((1024, 2), np.int16))\n"
                "    time.sleep(0.034)\n"
                "time.sleep(0.5)\n"
                "os._exit(1)\n"
            )
            subprocess.run([sys.executable, "-c", code], timeout=60)
            path = Path(d) / "iPhone kill.mp4"
            with av.open(str(path)) as f:  # not finished, yet readable
                frames = sum(1 for _ in f.decode(video=0))
        self.assertGreater(frames, 30)  # all but the last fragment (key frame every 2 s)

    def test_static_screen_records_the_frame_already_shown(self):
        from iphone_mirror.airplay import Receiver

        rx = Receiver(config.Settings(Path(tempfile.mkdtemp()) / "s.json"), lambda *a: None, lambda *a: None)
        rx.decoder.last_frame = _frame(64, 128, 1)
        rx._mirror_owner = object()  # a session is mirroring, but the screen does not change
        with tempfile.TemporaryDirectory() as d:
            rx.start_recording(Path(d))
            paths = rx.stop_recording()
            self.assertEqual(len(paths), 1)
            with av.open(str(paths[0])) as f:
                self.assertEqual(sum(1 for _ in f.decode(video=0)), 1)

    def test_frame_rate_cap(self):
        with tempfile.TemporaryDirectory() as d:
            rec = record.Recorder(Path(d), audio=False, stamp="cap")
            for i in range(20):  # all within a few ms: only the first passes the 30 fps cap
                rec.video(_frame(64, 64, i))
            rec.stop()
            self.assertEqual(rec.frames, 1)


class AdvertiseTest(unittest.TestCase):
    """Real mDNS on this machine: skipped where multicast does not work."""

    def test_hide_and_show_in_screen_mirroring(self):
        from zeroconf import Zeroconf

        from iphone_mirror import net
        from iphone_mirror.airplay import Receiver

        name = f"PocketPane Test {time.time_ns() % 100000}"
        old_port, net.PORT = net.PORT, 7161
        settings = config.Settings(Path(tempfile.mkdtemp()) / "s.json")
        settings["name"] = name
        events = []
        rx = Receiver(settings, on_frame=lambda *a: None, on_event=lambda e, i: events.append(e))
        try:
            rx.start()
            deadline = time.monotonic() + 15
            while "listening" not in events and time.monotonic() < deadline:
                time.sleep(0.1)

            def seen():
                z = Zeroconf()
                try:
                    return z.get_service_info("_airplay._tcp.local.", f"{name}._airplay._tcp.local.", 2500) is not None
                finally:
                    z.close()

            if not seen():
                self.skipTest("mDNS lookups do not work here")
            rx.set_advertised(False)
            time.sleep(1.5)
            self.assertFalse(seen())
            rx.set_advertised(True)
            time.sleep(1.5)
            self.assertTrue(seen())
            for on in (False, True, False, True, False):  # quick clicks: the last one wins
                rx.set_advertised(on)
            rx._mdns.submit(lambda: None).result(timeout=20)  # wait for the queued changes
            self.assertFalse(seen())
            self.assertFalse(rx.advertised)
        finally:
            rx.stop()
            net.PORT = old_port


if __name__ == "__main__":
    unittest.main()
