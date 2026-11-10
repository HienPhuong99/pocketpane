"""Tests for the USB control setup checks (control/setup.py). No iPhone needed."""
import datetime
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from iphone_mirror.control import setup, usb  # noqa: E402

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
BUNDLE = "com.example.WebDriverAgentRunner.xctrunner"
DEV = {"Identifier": "UDID1", "DeviceName": "Test iPhone", "ProductVersion": "18.1", "ProductType": "iPhone16,1"}


def profiles(*items):
    """pymobiledevice3 'provision list' output: [(application-identifier, expiration), ...]"""
    return json.dumps([{"Entitlements": {"application-identifier": a}, "ExpirationDate": e.isoformat()}
                       for a, e in items])


class ProfileTest(unittest.TestCase):
    def test_matching(self):
        def p(app_id):
            return {"Entitlements": {"application-identifier": app_id}}

        self.assertTrue(setup.profile_matches(p(f"TEAM1.{BUNDLE}"), BUNDLE))
        self.assertTrue(setup.profile_matches(p("TEAM1.*"), BUNDLE))
        self.assertTrue(setup.profile_matches(p("TEAM1.com.example.*"), BUNDLE))
        self.assertFalse(setup.profile_matches(p("TEAM1.com.other.app"), BUNDLE))
        self.assertFalse(setup.profile_matches(p("TEAM1.com.example.WebDriverAgentRunner"), BUNDLE))
        self.assertFalse(setup.profile_matches({}, BUNDLE))

    def test_expiry_is_the_newest_matching_profile(self):
        out = profiles((f"T.{BUNDLE}", NOW + datetime.timedelta(days=1)),
                       ("T.*", NOW + datetime.timedelta(days=5)),
                       ("T.com.other", NOW + datetime.timedelta(days=300)))
        with mock.patch.object(usb, "pmd3", return_value=(0, out, "")):
            self.assertEqual(setup.wda_expiry("UDID1", BUNDLE), NOW + datetime.timedelta(days=5))

    def test_expiry_unknown(self):
        with mock.patch.object(usb, "pmd3", return_value=(1, "", "boom")):
            self.assertIsNone(setup.wda_expiry("UDID1", BUNDLE))
        with mock.patch.object(usb, "pmd3", return_value=(0, profiles(("T.com.other", NOW)), "")):
            self.assertIsNone(setup.wda_expiry("UDID1", BUNDLE))


class ExpiryWarningTest(unittest.TestCase):
    def warning(self, expires):
        with mock.patch.object(usb, "usbmuxd_reachable", return_value=True), \
                mock.patch.object(usb, "list_devices", return_value=[DEV]), \
                mock.patch.object(usb, "find_wda_bundle", return_value=BUNDLE), \
                mock.patch.object(setup, "wda_expiry", return_value=expires):
            return setup.expiry_warning(now=NOW)

    def test_only_when_close(self):
        self.assertIn("about 5 hours", self.warning(NOW + datetime.timedelta(hours=5)))
        self.assertIsNone(self.warning(NOW + datetime.timedelta(days=4)))
        self.assertIsNone(self.warning(None))

    def test_never_raises(self):
        with mock.patch.object(usb, "usbmuxd_reachable", return_value=True), \
                mock.patch.object(usb, "list_devices", side_effect=usb.UsbError("locked")):
            self.assertIsNone(setup.expiry_warning())


class CheckTest(unittest.TestCase):
    def run_check(self, reachable=True, devices=(DEV,), dev_mode=True, bundle=BUNDLE, expires=None):
        with mock.patch.object(usb, "usbmuxd_reachable", return_value=reachable), \
                mock.patch.object(usb, "list_devices", return_value=list(devices)), \
                mock.patch.object(usb, "developer_mode_enabled", return_value=dev_mode), \
                mock.patch.object(usb, "find_wda_bundle", return_value=bundle), \
                mock.patch.object(setup, "wda_expiry", return_value=expires):
            return setup.check(now=NOW)

    def states(self, r):
        return {s.key: s.state for s in r.steps}

    def test_no_apple_driver(self):
        r = self.run_check(reachable=False)
        self.assertEqual(r.step("usbmuxd").state, setup.FAIL)
        self.assertEqual(r.step("usbmuxd").actions, [setup.A_GET_APPLE])
        self.assertEqual(r.step("device").state, setup.TODO)  # later steps are not checked
        self.assertFalse(r.ready)
        self.assertEqual(r.step("start").actions, [])

    def test_no_iphone(self):
        r = self.run_check(devices=())
        self.assertEqual(r.step("device").state, setup.FAIL)
        self.assertIn("cable", r.step("device").detail)

    def test_developer_mode_off(self):
        r = self.run_check(dev_mode=False)
        self.assertEqual(r.step("dev_mode").state, setup.FAIL)
        self.assertEqual(r.step("dev_mode").actions, [setup.A_REVEAL_DEV_MODE])

    def test_developer_mode_not_needed_before_ios_16(self):
        r = self.run_check(devices=(dict(DEV, ProductVersion="15.7"),), dev_mode=False, expires=NOW + datetime.timedelta(days=6))
        self.assertEqual(r.step("dev_mode").state, setup.SKIP)
        self.assertTrue(r.ready)

    def test_wda_missing(self):
        r = self.run_check(bundle=None)
        self.assertEqual(r.step("wda").state, setup.FAIL)
        self.assertEqual(r.step("wda").actions, [setup.A_GET_WDA, setup.A_SIDELOADLY])

    def test_signature_expired(self):
        r = self.run_check(expires=NOW - datetime.timedelta(hours=1))
        self.assertEqual(r.step("signature").state, setup.FAIL)
        self.assertFalse(r.ready)

    def test_signature_expiring_soon_is_a_warning(self):
        r = self.run_check(expires=NOW + datetime.timedelta(hours=20))
        self.assertEqual(r.step("signature").state, setup.WARN)
        self.assertIn("0.8 days left", r.step("signature").detail)
        self.assertTrue(r.ready)
        self.assertEqual(r.step("start").actions, [setup.A_START])

    def test_all_good(self):
        r = self.run_check(expires=NOW + datetime.timedelta(days=6))
        self.assertEqual(set(self.states(r).values()) - {setup.OK}, {setup.TODO})  # only 'start' left
        self.assertTrue(r.ready)
        self.assertEqual((r.udid, r.bundle), ("UDID1", BUNDLE))
        self.assertIn("Test iPhone (iPhone16,1), iOS 18.1", r.step("device").detail)

    def test_early_ios_17_warns(self):
        r = self.run_check(devices=(dict(DEV, ProductVersion="17.2"),), expires=NOW + datetime.timedelta(days=6))
        self.assertEqual(r.step("dev_mode").state, setup.WARN)
        self.assertTrue(r.ready)


if __name__ == "__main__":
    unittest.main()
