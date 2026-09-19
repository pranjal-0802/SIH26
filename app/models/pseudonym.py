import os
import hashlib
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base

class PseudonymMapping(Base):
    """
    Decoupling layer between identity and wellness telemetry.
    Maps personnel identity to a rotating pseudo_id (e.g. PX-7821).
    """
    __tablename__ = "pseudonym_mapping"

    id = Column(Integer, primary_key=True, index=True)
    pseudo_id = Column(String(32), unique=True, index=True, nullable=False)
    personnel_identity_id = Column(Integer, index=True, nullable=False)
    
    # Epoch-based salt for cryptographic rotation
    salt = Column(String(64), nullable=False)
    rotation_epoch = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @staticmethod
    def generate_pseudo_id(identity_id: int, epoch: int = 1) -> tuple[str, str]:
        """
        Generates an uncorrelatable rotating pseudo_id with format 'PX-XXXX'.
        Returns (pseudo_id, salt).
        """
        salt = os.urandom(16).hex()
        raw = f"{identity_id}:{epoch}:{salt}".encode("utf-8")
        h = hashlib.sha256(raw).hexdigest()
        # Take 4 alphanumeric characters for human readability in defense logs: PX-7821
        pseudo_id = f"PX-{h[:4].upper()}"
        return pseudo_id, salt

