from typing import List, Optional
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.security import decode_access_token, verify_totp_code
from app.ids.anomaly_detector import ids_engine
from app.audit.chain import append_audit_entry

security_scheme = HTTPBearer(auto_error=True)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Validates JWT bearer token and resolves the authenticated User."""
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or corrupted authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload: missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user record no longer exists or is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return user


class RoleChecker:
    """Dependency that enforces role-based access control with IDS anomaly interception."""
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [r.lower() for r in allowed_roles]

    def __call__(
        self, 
        request: Request,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        user_role = user.role.lower()
        if user_role not in self.allowed_roles:
            # Audit unauthorized access attempt
            append_audit_entry(
                db=db,
                actor_id=user.username,
                actor_role=user.role,
                action="RBAC_PRIVILEGE_DENIAL",
                endpoint=request.url.path,
                details={"required_roles": self.allowed_roles, "user_role": user.role},
                is_anomaly=True,
                anomaly_score=0.85
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Operation requires roles {self.allowed_roles}. Current role is '{user.role}'."
            )
        return user


def require_totp_if_enabled(
    user: User = Depends(get_current_user),
    x_totp_code: Optional[str] = Header(None, alias="X-TOTP-Code")
) -> User:
    """Enforces Time-Based One-Time Password verification on privileged actions."""
    if user.is_totp_enabled:
        if not x_totp_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Multi-Factor Authentication Required: Missing 'X-TOTP-Code' header."
            )
        if not verify_totp_code(user.totp_secret, x_totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired TOTP code."
            )
    return user

