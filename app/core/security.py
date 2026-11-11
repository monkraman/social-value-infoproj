import hashlib
import hmac
import json
import base64
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

if settings.JWT_SECRET_KEY and len(settings.JWT_SECRET_KEY) >= 32:
    SECRET_KEY = settings.JWT_SECRET_KEY
else:
    # No configured key: use a random one for this process. Tokens can't be forged,
    # but everyone is signed out when the server restarts. Set JWT_SECRET_KEY to avoid that.
    SECRET_KEY = secrets.token_urlsafe(48)
    print("[Security] JWT_SECRET_KEY is not set (or under 32 chars); using a random per-process key.")

# OWASP 2023 guidance for PBKDF2-HMAC-SHA256.
PBKDF2_ITERATIONS = 600_000
_LEGACY_ITERATIONS = 100_000


# ---------------------------------------------------------------------------
# Password policy
# ---------------------------------------------------------------------------
PASSWORD_MIN_LENGTH = 12
_COMMON_PASSWORDS = {
    "password", "password1", "password123", "admin", "admin123", "administrator", "welcome",
    "welcome1", "letmein", "qwerty", "qwerty123", "123456", "12345678", "123456789", "iloveyou",
    "infosys", "infosys123", "socialvalue", "changeme", "passw0rd",
}
# Rejected anywhere inside a password, so "Password1234!" style variations fail too.
_COMMON_WORDS = ("password", "passw0rd", "qwerty", "letmein", "welcome", "infosys", "socialvalue",
                 "changeme", "admin", "iloveyou", "12345")


def password_policy_errors(password: str, email: Optional[str] = None, name: Optional[str] = None) -> list[str]:
    """Returns the policy rules a password breaks (empty list = acceptable)."""
    errors = []
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"at least {PASSWORD_MIN_LENGTH} characters")
    if len(password) > 128:
        errors.append("at most 128 characters")
    if not re.search(r"[a-z]", password):
        errors.append("a lowercase letter")
    if not re.search(r"[A-Z]", password):
        errors.append("an uppercase letter")
    if not re.search(r"\d", password):
        errors.append("a number")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("a symbol")
    lowered = password.lower()
    stripped = re.sub(r"[^a-z]", "", lowered)
    if (lowered in _COMMON_PASSWORDS or stripped in _COMMON_PASSWORDS
            or any(word in lowered for word in _COMMON_WORDS)):
        errors.append("not a common password or word (e.g. 'password', 'infosys', 'qwerty')")
    personal = []
    if email:
        personal.append(email.split("@", 1)[0].lower())
    if name:
        personal.extend(part.lower() for part in name.split())
    if any(len(p) >= 4 and p in lowered for p in personal):
        errors.append("not your name or email")
    return errors


def validate_password_strength(password: str, email: Optional[str] = None, name: Optional[str] = None) -> None:
    errors = password_policy_errors(password, email, name)
    if errors:
        raise ValueError("Password must contain " + ", ".join(errors) + ".")


def generate_strong_password(length: int = 20) -> str:
    """Random password that always satisfies the policy."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*-_=+"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if not password_policy_errors(pw):
            return pw


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256, stored as pbkdf2_sha256$<iterations>$<salt>$<hash>."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${key.hex()}"


def _parse_hash(hashed_password: str) -> tuple[int, str, str]:
    parts = hashed_password.split("$")
    if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
        return int(parts[1]), parts[2], parts[3]
    salt, stored = hashed_password.split("$", 1)  # legacy salt$hash at 100k iterations
    return _LEGACY_ITERATIONS, salt, stored


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        iterations, salt, stored_hash = _parse_hash(hashed_password)
        computed = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return hmac.compare_digest(computed.hex(), stored_hash)
    except Exception:
        return False


def needs_rehash(hashed_password: str) -> bool:
    try:
        return _parse_hash(hashed_password)[0] < PBKDF2_ITERATIONS
    except Exception:
        return True


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed JWT (RFC 7519) using HS256."""
    header = {"alg": ALGORITHM, "typ": "JWT"}
    payload = data.copy()

    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload["exp"] = int(expire.timestamp())
    payload["iat"] = int(now.timestamp())

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Validates signature, algorithm and expiry; returns the payload or None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        if header.get("alg") != ALGORITHM:
            return None

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_encode(expected_sig), sig_b64):
            return None

        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        exp = payload.get("exp")
        if not exp or exp < int(datetime.now(timezone.utc).timestamp()):
            return None
        return payload
    except Exception:
        return None
