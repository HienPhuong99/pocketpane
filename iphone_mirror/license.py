"""License keys: a signed note saying who may use this copy.

A key is base64url(JSON payload) + "." + base64url(Ed25519 signature). The app holds only
the public key; tools/make_key.py signs with the private key in ~/.pocketpane/signing.key.
"""
# ponytail: the check is plain Python and a key is not tied to a PC, so anyone with the
# source can delete the check and a key can be passed on. It stops casual copying only.
# Add a machine id to the payload if passed-on keys become a problem.
import base64
import json
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

PUBLIC_KEY = "a92889c8383f2a5858e3533fdd846376c46e4a59c51814d1628a9ce195505ae2"  # hex; tools/make_key.py prints the value that matches your signing key


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def public_hex(seed: bytes) -> str:
    key = Ed25519PrivateKey.from_private_bytes(seed).public_key()
    return key.public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def make(seed: bytes, name: str, exp: str | None = None) -> str:
    """Sign a key for `name`, valid through `exp` (YYYY-MM-DD) or forever."""
    body = json.dumps({"name": name, "exp": exp}).encode()
    return _b64e(body) + "." + _b64e(Ed25519PrivateKey.from_private_bytes(seed).sign(body))


def check(key, today: str | None = None):
    """The key's payload ({"name", "exp"}) if it is genuine and not expired, else None."""
    try:
        body, sig = (key or "").strip().split(".")
        body = _b64d(body)
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(PUBLIC_KEY)).verify(_b64d(sig), body)
        info = json.loads(body)
    except (ValueError, InvalidSignature):
        return None
    if info.get("exp") and info["exp"] < (today or time.strftime("%Y-%m-%d")):
        return None
    return info
