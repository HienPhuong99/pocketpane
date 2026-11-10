"""License keys: only keys signed with the matching private key and not expired pass."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from iphone_mirror import license  # noqa: E402

SEED = bytes(range(32))


class LicenseTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(license, "PUBLIC_KEY", license.public_hex(SEED))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_valid_key(self):
        key = license.make(SEED, "Phương", "2030-01-01")
        self.assertEqual(license.check(f"  {key}\n", today="2030-01-01"), {"name": "Phương", "exp": "2030-01-01"})
        self.assertEqual(license.check(license.make(SEED, "A"))["exp"], None)

    def test_rejected_keys(self):
        key = license.make(SEED, "A", "2030-01-01")
        body, sig = key.split(".")
        other = license.make(bytes(32), "A")  # signed with someone else's private key
        forged = license._b64e(b'{"name": "A", "exp": null}') + "." + sig  # payload changed
        for bad in (None, "", "abc", "a.b", "a.b.c", "!.!", other, forged, body + "."):
            self.assertIsNone(license.check(bad), bad)
        self.assertIsNone(license.check(key, today="2030-01-02"))  # expired

    def test_app_asks_until_valid_or_cancel(self):
        from iphone_mirror.__main__ import ensure_license

        class FakeSettings(dict):
            def save(self):
                pass

        key = license.make(SEED, "A")
        with mock.patch("iphone_mirror.__main__.QInputDialog.getText", side_effect=[("bad", True), (key, True)]):
            s = FakeSettings()
            self.assertTrue(ensure_license(s))
            self.assertEqual(s["license"], key)
        with mock.patch("iphone_mirror.__main__.QInputDialog.getText", return_value=("", False)):
            self.assertFalse(ensure_license(FakeSettings()))
        with mock.patch("iphone_mirror.__main__.QInputDialog.getText", side_effect=AssertionError("asked")):
            self.assertTrue(ensure_license(FakeSettings(license=key)))  # stored key: no dialog


if __name__ == "__main__":
    unittest.main()
