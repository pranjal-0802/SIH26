import hmac
import hashlib
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Text
from app.database import Base

GENESIS_PREV_HASH = "GENESIS_PRISMARINE_0000000000000000000000000000000000000000000000000000"

class AuditLogEntry(Base):
    """
    Cryptographic HMAC-SHA256 append-only audit trail.
    Each entry commits to the preceding block using HMAC-SHA256 keyed with AUDIT_HMAC_KEY_HEX.
    Because the HMAC key is held exclusively in application memory/HSM and NEVER stored in the database,
    a rogue DB administrator with full SQL write access cannot forge valid signatures.
    """
    __tablename__ = "tamper_evident_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    sequence_no = Column(Integer, unique=True, index=True, nullable=False)
    previous_hash = Column(String(64), nullable=False)
    entry_hash = Column(String(64), unique=True, index=True, nullable=False)
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    timestamp_iso = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(64), nullable=False)
    actor_role = Column(String(32), nullable=False)
    action = Column(String(64), nullable=False)  # e.g. VIEW_COHORT, BREAK_GLASS, IDS_INTERCEPT
    endpoint = Column(String(128), nullable=False)
    scope_battalion = Column(String(64), nullable=True)
    details_json = Column(Text, nullable=False)
    
    is_anomaly = Column(Boolean, default=False)
    anomaly_score = Column(Float, default=0.0)

    @staticmethod
    def compute_hmac(
        sequence_no: int,
        previous_hash: str,
        timestamp_iso: str,
        actor_id: str,
        actor_role: str,
        action: str,
        endpoint: str,
        details_json: str,
        hmac_key: bytes
    ) -> str:
        """
        Computes deterministic HMAC-SHA256 block hash linking to previous entry.
        Guarantees defense against rogue DB administrators.
        """
        material = f"{sequence_no}|{previous_hash}|{timestamp_iso}|{actor_id}|{actor_role}|{action}|{endpoint}|{details_json}".encode("utf-8")
        return hmac.new(hmac_key, material, hashlib.sha256).hexdigest()
