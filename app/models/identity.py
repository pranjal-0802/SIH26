from datetime import datetime, timezone
import hashlib
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base
from app.core.crypto import EncryptedString

class PersonnelIdentity(Base):
    """
    Encrypted PII vault.
    Stores personnel identity attributes under column-level AES-256-GCM.
    Physically decoupled from clinical and wellness telemetry.
    Database columns store ciphertext; Python attributes transparently decrypt at runtime.
    """
    __tablename__ = "personnel_identity"

    id = Column(Integer, primary_key=True, index=True)
    
    # AES-256-GCM Encrypted columns (SQL column name retains 'encrypted_' prefix for audit honesty)
    service_no = Column("encrypted_service_no", EncryptedString, nullable=False)
    name = Column("encrypted_name", EncryptedString, nullable=False)
    rank = Column("encrypted_rank", EncryptedString, nullable=False)
    phone = Column("encrypted_phone", EncryptedString, nullable=True)
    
    # Operational routing fields (non-PII)
    battalion_code = Column(String(64), index=True, nullable=False)
    company = Column(String(32), index=True, nullable=False)
    station = Column(String(64), nullable=False)
    
    # SHA-256 blinded search index for lookup without exposing plaintext
    service_no_hash = Column(String(64), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    @staticmethod
    def compute_service_hash(service_no: str) -> str:
        """One-way blinded hash for authenticated lookup."""
        return hashlib.sha256(service_no.strip().upper().encode("utf-8")).hexdigest()
