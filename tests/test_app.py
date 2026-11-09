"""Tests for the PocketPane additions that do not need an iPhone. Run:  python -m pytest tests"""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

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

    def test_frame_rate_cap(self):
        with tempfile.TemporaryDirectory() as d:
            rec = record.Recorder(Path(d), audio=False, stamp="cap")
            for i in range(20):  # all within a few ms: only the first passes the 30 fps cap
                rec.video(_frame(64, 64, i))
            rec.stop()
            self.assertEqual(rec.frames, 1)


if __name__ == "__main__":
    unittest.main()
