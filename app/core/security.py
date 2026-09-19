import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Dict
import bcrypt
import pyotp
from jose import jwt, JWTError

from app.config import settings

def hash_password(password: str) -> str:
    """Hashes a password using direct bcrypt with salt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), 
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def get_token_lifetime_for_role(role: str) -> timedelta:
    """Returns token expiration duration tailored to privilege level."""
    role_lower = role.lower()
    if role_lower == "personnel":
        minutes = settings.TOKEN_EXPIRE_MINUTES_PERSONNEL
    elif role_lower == "welfare_officer":
        minutes = settings.TOKEN_EXPIRE_MINUTES_WELFARE
    elif role_lower == "commander":
        minutes = settings.TOKEN_EXPIRE_MINUTES_COMMANDER
    elif role_lower == "admin":
        minutes = settings.TOKEN_EXPIRE_MINUTES_ADMIN
    else:
        minutes = 60
    return timedelta(minutes=minutes)


def create_access_token(
    subject: str, 
    role: str, 
    assigned_battalion: Optional[str] = None,
    pseudo_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Creates a signed JWT access token embedding role and battalion scope."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + get_token_lifetime_for_role(role)
        
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "assigned_battalion": assigned_battalion,
        "pseudo_id": pseudo_id,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": settings.APP_CODE
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
            issuer=settings.APP_CODE
        )
        return payload
    except JWTError:
        return None


# ==========================================
# TOTP Multi-Factor Authentication (RFC 6238)
# ==========================================

def generate_totp_secret() -> str:
    """Generates a random Base32 TOTP secret for privileged accounts."""
    return pyotp.random_base32()


def get_totp_provisioning_uri(username: str, secret: str) -> str:
    """Returns the otpauth:// URI for QR code generation."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name=settings.APP_NAME)


def verify_totp_code(secret: str, code: str) -> bool:
    """
    Verifies a 6-digit TOTP code (RFC 6238).
    Demo master-code bypass is strictly gated behind settings.DEMO_MODE=True.
    """
    if not secret or not code:
        return False
    
    # Controlled presentation aid: ONLY active when explicitly configured in DEMO_MODE
    if settings.DEMO_MODE and code in ("123456", "000000"):
        return True
        
    try:
        totp = pyotp.TOTP(secret)
        return bool(totp.verify(code, valid_window=1))
    except Exception:
        return False
