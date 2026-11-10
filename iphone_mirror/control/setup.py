"""Step-by-step check of everything USB control needs, as data (no printing).

Used by the setup window in the app and by `python -m iphone_mirror.control doctor`.
Each step is ok / fail / warn / todo (not checked because an earlier step failed) /
skip (not needed on this iOS version). `action` names something the user (or the app) can
do about a failed step; the UI maps it to a button.
"""
import datetime
import importlib.metadata
import sys
from dataclasses import dataclass, field

from . import usb

OK, FAIL, WARN, TODO, SKIP = "ok", "fail", "warn", "todo", "skip"
EXPIRY_WARN_DAYS = 2  # warn when the WDA signature expires sooner than this

# actions the UI offers for a step
A_GET_APPLE = "get_apple_devices"  # open the Store page of Apple Devices
A_GET_ITUNES = "get_itunes"  # download iTunes from apple.com (also installs the USB driver)
A_REVEAL_DEV_MODE = "reveal_dev_mode"  # make the Developer Mode switch appear on the phone
A_GET_WDA = "get_wda"  # download WebDriverAgentRunner.ipa
A_SIDELOADLY = "open_sideloadly"  # open sideloadly.io
A_START = "start_control"  # try starting control (the last step: also checks the trust prompt)

TITLES = {
    "pmd3": "PocketPane's iPhone tools",
    "usbmuxd": "Apple USB driver (Apple Devices / iTunes)",
    "device": "iPhone connected and trusted",
    "dev_mode": "Developer Mode on the iPhone",
    "wda": "WebDriverAgent installed on the iPhone",
    "signature": "WebDriverAgent signature still valid",
    "start": "Start control",
}

HOW = {
    "usbmuxd": "Install \"Apple Devices\" from the Microsoft Store, or iTunes from apple.com if the Store "
               "says your Windows is too old (\"Get iTunes\"), open it once with the iPhone connected, then "
               "click Check again.",
    "device": "Connect the iPhone with a USB cable, unlock it and tap \"Trust\" (then enter the passcode).",
    "dev_mode": "Click \"Show Developer Mode\", then on the iPhone: Settings > Privacy & Security > "
                "Developer Mode > On. The phone restarts; unlock it and tap Turn On.",
    "wda": "Click \"Download WebDriverAgent\", then install the downloaded WebDriverAgentRunner.ipa with "
           "Sideloadly (sideloadly.io) using your Apple ID. A free Apple ID works for 7 days at a time.",
    "signature": "Install WebDriverAgentRunner.ipa again with Sideloadly to renew it (free Apple ID: every 7 days).",
    "start": "Click \"Turn on control\". The first start also downloads the Developer Disk Image (needs "
             "Internet). If the iPhone says \"Untrusted Developer\": Settings > General > VPN & Device "
             "Management > your Apple ID > Trust, then try again.",
}


DEV_MODE_OFF = "Developer Mode is off."
NO_WDA = "WebDriverAgent is not installed."


@dataclass
class Step:
    key: str
    state: str = TODO
    detail: str = ""
    actions: list = field(default_factory=list)

    @property
    def title(self):
        return TITLES[self.key]

    @property
    def how(self):
        return HOW.get(self.key, "")


@dataclass
class Report:
    steps: list
    device: dict = None
    udid: str = None
    bundle: str = None
    expires: datetime.datetime = None

    @property
    def ready(self):
        """Everything up to starting control checked out."""
        return all(s.state in (OK, WARN, SKIP) for s in self.steps if s.key != "start")

    def step(self, key):
        return next(s for s in self.steps if s.key == key)


def device_line(dev):
    name = dev.get("DeviceName") or "iPhone"
    model = dev.get("ProductType") or "?"
    return f"{name} ({model}), iOS {dev.get('ProductVersion') or '?'}"


def _parse_date(value):
    if isinstance(value, datetime.datetime):
        d = value
    else:
        try:
            d = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


def profile_match(profile, bundle):
    """How this provisioning profile covers the app `bundle`: "exact" ('TEAMID.bundle.id'),
    "wildcard" ('TEAMID.*', 'TEAMID.com.example.*') or None."""
    ent = profile.get("Entitlements") if isinstance(profile, dict) else None
    app_id = str((ent or {}).get("application-identifier") or "")
    if "." not in app_id or not bundle:
        return None
    pattern = app_id.split(".", 1)[1]
    if pattern.endswith("*"):
        return "wildcard" if bundle.startswith(pattern[:-1]) else None
    return "exact" if pattern == bundle else None


def profile_matches(profile, bundle):
    return profile_match(profile, bundle) is not None


def wda_expiry(udid, bundle, cancel=None):
    """Expiration date of the newest provisioning profile that covers the WDA bundle, or None
    if it cannot be told (no matching profile, or the list could not be read)."""
    try:
        code, out, _ = usb.pmd3("provision", "list", "--udid", udid, timeout=60, cancel=cancel)
    except usb.Cancelled:
        raise
    except usb.UsbError:  # timed out, or pymobiledevice3 could not start: unknown, not fatal
        return None
    if code:
        return None
    profiles = usb._json(out)
    if not isinstance(profiles, list):
        return None
    # the app's own (exact) profile decides; an unrelated wildcard profile (another team, an
    # enterprise app) must not hide that the WDA signature is about to expire
    for kind in ("exact", "wildcard"):
        dates = [_parse_date(p.get("ExpirationDate")) for p in profiles
                 if isinstance(p, dict) and profile_match(p, bundle) == kind]
        dates = [d for d in dates if d is not None]
        if dates:
            return max(dates)
    return None


def days_left(expires, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return (expires - now).total_seconds() / 86400


def expiry_warning(cancel=None, now=None):
    """A short warning if the WDA on the connected iPhone expires within EXPIRY_WARN_DAYS
    (checked when control starts), else None. Never raises."""
    try:
        if not usb.usbmuxd_reachable():
            return None
        devices = usb.list_devices(cancel=cancel)
        if not devices:
            return None
        udid = devices[0].get("Identifier") or devices[0].get("UniqueDeviceID")
        bundle = usb.find_wda_bundle(udid, cancel=cancel)
        expires = wda_expiry(udid, bundle, cancel=cancel) if bundle else None
    except usb.UsbError:
        return None
    if expires is None:
        return None
    left = days_left(expires, now)
    if left >= EXPIRY_WARN_DAYS:
        return None
    hours = max(0, round(left * 24))
    return (f"WebDriverAgent expires in about {hours} hours. Install WebDriverAgentRunner.ipa again "
            "with Sideloadly before then (right-click > Set Up iPhone Control).")


APPLE_DEVICES_MIN_BUILD = 19045  # Windows 10 22H2: the Store refuses Apple Devices on older builds


def apple_actions(build=None):
    """Apple Devices where the Store offers it, else iTunes: both install Apple's USB service."""
    if build is None:
        build = sys.getwindowsversion().build if sys.platform == "win32" else APPLE_DEVICES_MIN_BUILD
    return [A_GET_APPLE, A_GET_ITUNES] if build >= APPLE_DEVICES_MIN_BUILD else [A_GET_ITUNES]


def check(cancel=None, now=None) -> Report:
    """Run every check, stopping at the first failure (later steps stay TODO)."""
    steps = [Step(k) for k in TITLES]
    report = Report(steps)
    s = {st.key: st for st in steps}

    def done():
        s["start"].actions = [A_START] if report.ready else []
        return report

    try:
        v = importlib.metadata.version("pymobiledevice3")
        s["pmd3"].state, s["pmd3"].detail = OK, f"pymobiledevice3 {v}"
    except importlib.metadata.PackageNotFoundError:
        s["pmd3"].state, s["pmd3"].detail = FAIL, usb.MSG_NO_PMD3
        return done()

    if not usb.usbmuxd_reachable():
        s["usbmuxd"].state, s["usbmuxd"].detail = FAIL, "Apple's USB service is not running."
        s["usbmuxd"].actions = apple_actions()
        return done()
    s["usbmuxd"].state = OK

    try:
        devices = usb.list_devices(cancel=cancel)
    except usb.UsbError as e:
        s["device"].state, s["device"].detail = FAIL, str(e)
        return done()
    if not devices:
        s["device"].state, s["device"].detail = FAIL, usb.MSG_NO_DEVICE
        return done()
    dev = report.device = devices[0]
    udid = report.udid = dev.get("Identifier") or dev.get("UniqueDeviceID")
    ios = usb.parse_version(dev.get("ProductVersion"))
    s["device"].state = OK
    s["device"].detail = device_line(dev) + ("  (several iPhones connected: the first one is used)"
                                             if len(devices) > 1 else "")

    if ios[0] and ios[0] < 16:
        s["dev_mode"].state, s["dev_mode"].detail = SKIP, f"Not needed on iOS {ios[0]}."
    else:
        try:
            on = usb.developer_mode_enabled(udid, cancel=cancel)
        except usb.UsbError as e:
            s["dev_mode"].state, s["dev_mode"].detail = FAIL, str(e)
            return done()
        if not on:
            s["dev_mode"].state, s["dev_mode"].detail = FAIL, DEV_MODE_OFF
            s["dev_mode"].actions = [A_REVEAL_DEV_MODE]
            return done()
        s["dev_mode"].state = OK
        if (17, 0) <= ios < (17, 4):
            s["dev_mode"].state, s["dev_mode"].detail = WARN, usb.MSG_IOS_17_EARLY

    try:
        bundle = report.bundle = usb.find_wda_bundle(udid, cancel=cancel)
    except usb.UsbError as e:
        s["wda"].state, s["wda"].detail = FAIL, str(e)
        return done()
    if not bundle:
        s["wda"].state, s["wda"].detail = FAIL, NO_WDA
        s["wda"].actions = [A_GET_WDA, A_SIDELOADLY]
        return done()
    s["wda"].state, s["wda"].detail = OK, bundle

    expires = report.expires = wda_expiry(udid, bundle, cancel=cancel)
    sig = s["signature"]
    if expires is None:
        sig.state, sig.detail = WARN, "Could not read the expiry date (it is checked when control starts)."
    else:
        left = days_left(expires, now)
        when = expires.astimezone().strftime("%Y-%m-%d %H:%M")
        if left <= 0:
            sig.state, sig.detail = FAIL, f"Expired on {when}."
            sig.actions = [A_SIDELOADLY]
            return done()
        sig.state = WARN if left < EXPIRY_WARN_DAYS else OK
        sig.detail = f"Valid until {when} ({left:.1f} days left)."
        if sig.state == WARN:
            sig.actions = [A_SIDELOADLY]
    return done()
