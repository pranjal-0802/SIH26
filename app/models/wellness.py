from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from app.database import Base
from app.core.crypto import EncryptedString, EncryptedFloat, EncryptedInt

class WellnessSignal(Base):
    """
    Decoupled clinical and operational telemetry.
    Contains zero direct PII (linked strictly to pseudo_id).
    Database columns store AES-256-GCM ciphertext; runtime attributes decrypt transparently.
    """
    __tablename__ = "wellness_signals"

    id = Column(Integer, primary_key=True, index=True)
    pseudo_id = Column(String(32), index=True, nullable=False)
    battalion_code = Column(String(64), index=True, nullable=False)
    
    # Psychometric & Self-Report Signals (Encrypted on disk via AES-256-GCM)
    phq4_score = Column("encrypted_phq4_score", EncryptedFloat, nullable=False)
    mood_score = Column("encrypted_mood_score", EncryptedFloat, nullable=False)
    sleep_hours = Column("encrypted_sleep_hours", EncryptedFloat, nullable=False)
    stress_rating = Column("encrypted_stress_rating", EncryptedFloat, nullable=False)
    reflection_text = Column("encrypted_reflection_text", EncryptedString, nullable=True)
    
    # Objective HR & Operational Indicators (Encrypted on disk)
    days_since_leave = Column("encrypted_days_since_leave", EncryptedInt, nullable=False)
    denied_leaves = Column("encrypted_denied_leaves", EncryptedInt, nullable=False)
    deployment_hardship = Column("encrypted_deployment_hardship", EncryptedFloat, nullable=False)
    night_shifts_ratio = Column("encrypted_night_shifts_ratio", EncryptedFloat, nullable=False)
    
    # Non-reversible sentiment polarity (-1.0 to +1.0)
    sentiment_polarity = Column(Float, default=0.0)
    
    # Life-safety crisis hard-override flag (bypasses ranking algorithm)
    is_crisis_override = Column(Boolean, default=False, index=True)
    crisis_rationale = Column(String(255), nullable=True)
    
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
