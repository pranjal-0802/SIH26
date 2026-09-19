import os
import base64
import json
from typing import Any, Optional
try:
    from Crypto.Cipher import AES
except ImportError:
    from Cryptodome.Cipher import AES
from sqlalchemy.types import TypeDecorator, String, Text
from app.config import settings

# Parse master key from hex
_AES_KEY = bytes.fromhex(settings.AES_MASTER_KEY_HEX)
if len(_AES_KEY) != 32:
    raise ValueError("AES_MASTER_KEY_HEX must be a 64-character hex string (32 bytes / 256 bits)")


def encrypt_field(plaintext: Optional[Any]) -> Optional[str]:
    """
    Encrypts arbitrary data using AES-256-GCM.
    Produces base64-encoded string: nonce(12B) + tag(16B) + ciphertext.
    """
    if plaintext is None:
        return None
    
    # Standardize plaintext to string
    if not isinstance(plaintext, str):
        if isinstance(plaintext, (int, float, bool)):
            raw_str = str(plaintext)
        else:
            raw_str = json.dumps(plaintext)
    else:
        raw_str = plaintext

    nonce = os.urandom(12)  # NIST standard 96-bit nonce for GCM
    cipher = AES.new(_AES_KEY, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(raw_str.encode("utf-8"))
    
    # Pack: nonce (12 bytes) + tag (16 bytes) + ciphertext
    payload = nonce + tag + ciphertext
    return base64.b64encode(payload).decode("ascii")


def decrypt_field(encrypted_str: Optional[str]) -> Optional[str]:
    """
    Decrypts an AES-256-GCM base64-encoded ciphertext payload.
    Verifies authenticity tag to prevent tampering.
    """
    if not encrypted_str:
        return None
    
    try:
        raw_payload = base64.b64decode(encrypted_str.encode("ascii"))
        if len(raw_payload) < 28:
            # 12 (nonce) + 16 (tag) = 28 minimum bytes
            return None
        
        nonce = raw_payload[:12]
        tag = raw_payload[12:28]
        ciphertext = raw_payload[28:]
        
        cipher = AES.new(_AES_KEY, AES.MODE_GCM, nonce=nonce)
        decrypted_bytes = cipher.decrypt_and_verify(ciphertext, tag)
        return decrypted_bytes.decode("utf-8")
    except Exception:
        # Authentication failed or ciphertext corrupted
        return None


# ==========================================
# SQLAlchemy TypeDecorators for Seamless DB Integration
# ==========================================

class EncryptedString(TypeDecorator):
    """SQLAlchemy column type decorator that automatically encrypts/decrypts strings."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect: Any) -> Optional[str]:
        if value is None:
            return None
        return encrypt_field(value)

    def process_result_value(self, value: Optional[str], dialect: Any) -> Optional[str]:
        if value is None:
            return None
        return decrypt_field(value)


class EncryptedFloat(TypeDecorator):
    """SQLAlchemy column type decorator that automatically encrypts/decrypts floats."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[float], dialect: Any) -> Optional[str]:
        if value is None:
            return None
        return encrypt_field(str(value))

    def process_result_value(self, value: Optional[str], dialect: Any) -> Optional[float]:
        if value is None:
            return None
        dec = decrypt_field(value)
        return float(dec) if dec is not None else None


class EncryptedInt(TypeDecorator):
    """SQLAlchemy column type decorator that automatically encrypts/decrypts ints."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[int], dialect: Any) -> Optional[str]:
        if value is None:
            return None
        return encrypt_field(str(value))

    def process_result_value(self, value: Optional[str], dialect: Any) -> Optional[int]:
        if value is None:
            return None
        dec = decrypt_field(value)
        return int(dec) if dec is not None else None


class EncryptedJSON(TypeDecorator):
    """SQLAlchemy column type decorator for structured JSON objects."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[Any], dialect: Any) -> Optional[str]:
        if value is None:
            return None
        return encrypt_field(json.dumps(value))

    def process_result_value(self, value: Optional[str], dialect: Any) -> Optional[Any]:
        if value is None:
            return None
        dec = decrypt_field(value)
        return json.loads(dec) if dec is not None else None
