"""Tests for the PocketPane additions that do not need an iPhone. Run:  python -m pytest tests"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from iphone_mirror import config  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
