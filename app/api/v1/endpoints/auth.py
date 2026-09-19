from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.security import verify_password, create_access_token, verify_totp_code
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: str = "bearer"
    role: str
    username: str
    assigned_battalion: Optional[str] = None
    pseudo_id: Optional[str] = None
    requires_totp: bool = False
    message: str

class UserProfileResponse(BaseModel):
    id: int
    username: str
    role: str
    assigned_battalion: Optional[str]
    pseudo_id: Optional[str]
    is_totp_enabled: bool

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates users. Enforces TOTP MFA for privileged roles (Welfare, Commander, Admin).
    """
    user = db.query(User).filter(User.username == req.username, User.is_active == True).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service credentials"
        )

    # Check if privileged account requires TOTP MFA
    if user.is_totp_enabled:
        if not req.totp_code:
            # Signal client to prompt for TOTP code
            return LoginResponse(
                requires_totp=True,
                role=user.role,
                username=user.username,
                assigned_battalion=user.assigned_battalion,
                pseudo_id=user.pseudo_id,
                message="Multi-Factor Authentication Required: Submit 6-digit TOTP code."
            )
        
        # Verify provided TOTP code
        if not verify_totp_code(user.totp_secret, req.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired TOTP security token."
            )

    token = create_access_token(
        subject=user.username,
        role=user.role,
        assigned_battalion=user.assigned_battalion,
        pseudo_id=user.pseudo_id
    )

    return LoginResponse(
        access_token=token,
        role=user.role,
        username=user.username,
        assigned_battalion=user.assigned_battalion,
        pseudo_id=user.pseudo_id,
        requires_totp=False,
        message="Authentication successful."
    )

@router.get("/me", response_model=UserProfileResponse)
def get_profile(user: User = Depends(get_current_user)):
    """Returns currently authenticated user profile and scope."""
    return UserProfileResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        assigned_battalion=user.assigned_battalion,
        pseudo_id=user.pseudo_id,
        is_totp_enabled=user.is_totp_enabled
    )

