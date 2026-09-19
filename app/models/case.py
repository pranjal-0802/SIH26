from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from app.database import Base

class AlertCase(Base):
    """
    Stateful Welfare Case Management.
    Enables tracking of intervention lifecycle (OPEN -> ACKNOWLEDGED -> IN_PROGRESS -> RESOLVED).
    Eliminates stateless alert recalculation so resolved cases leave the active queue.
    """
    __tablename__ = "welfare_alert_cases"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(32), unique=True, index=True, nullable=False)
    pseudo_id = Column(String(32), index=True, nullable=False)
    battalion_code = Column(String(64), index=True, nullable=False)
    
    status = Column(String(32), default="OPEN", index=True, nullable=False)  # OPEN, ACKNOWLEDGED, IN_PROGRESS, RESOLVED
    priority_tier = Column(String(32), default="ELEVATED", nullable=False)   # CRITICAL, ELEVATED, MODERATE, LOW
    is_crisis = Column(Boolean, default=False, nullable=False)
    
    assigned_officer = Column(String(64), nullable=True)
    action_taken = Column(String(128), nullable=True)  # e.g. R&R Leave Granted, Peer Buddy Assigned, Counseling Scheduled
    clinical_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
