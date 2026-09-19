from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, index=True)  # personnel, welfare_officer, commander, admin
    assigned_battalion = Column(String(64), nullable=True, index=True)
    pseudo_id = Column(String(32), nullable=True, index=True)  # Populated for personnel role
    totp_secret = Column(String(64), nullable=True)
    is_totp_enabled = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

