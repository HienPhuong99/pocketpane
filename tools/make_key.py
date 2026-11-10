"""Issue a PocketPane license key:  python tools/make_key.py "Name" [--days 365]

Signs with the private key in ~/.pocketpane/signing.key (created on first use). Keep that
file secret and backed up: whoever has it can issue keys, and without it new keys need a
new PUBLIC_KEY in iphone_mirror/license.py, which makes every key issued before invalid.
"""
import argparse
import datetime
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from iphone_mirror import license  # noqa: E402

KEY_FILE = Path.home() / ".pocketpane" / "signing.key"


def main():
    p = argparse.ArgumentParser(description="Issue a PocketPane license key.")
    p.add_argument("name", help="who the key is for")
    p.add_argument("--days", type=int, help="valid for this many days (default: forever)")
    args = p.parse_args()
    if not KEY_FILE.exists():
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        KEY_FILE.write_text(secrets.token_hex(32))
    seed = bytes.fromhex(KEY_FILE.read_text().strip())
    pub = license.public_hex(seed)
    if pub != license.PUBLIC_KEY:
        sys.exit(f'{KEY_FILE} does not match the app.\n'
                 f'Set PUBLIC_KEY = "{pub}" in iphone_mirror/license.py, then rebuild the .exe.')
    exp = (datetime.date.today() + datetime.timedelta(days=args.days)).isoformat() if args.days else None
    print(license.make(seed, args.name, exp))


if __name__ == "__main__":
    main()
