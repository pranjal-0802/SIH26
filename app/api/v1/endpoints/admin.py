from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.audit import AuditLogEntry
from app.core.dependencies import RoleChecker, require_totp_if_enabled
from app.audit.chain import verify_audit_chain_integrity, append_audit_entry

router = APIRouter(prefix="/admin", tags=["Security & Infrastructure Admin"])

@router.get("/audit-chain")
def get_audit_chain(
    limit: int = 50,
    user: User = Depends(RoleChecker(["admin"])),
    _totp: User = Depends(require_totp_if_enabled),
    db: Session = Depends(get_db)
):
    """
    Returns the immutable HMAC-SHA256 audit log blocks.
    Enforces step-up TOTP verification for administrative auditing.
    Admin has infrastructure oversight but zero access to clinical telemetry.
    """
    entries = db.query(AuditLogEntry).order_by(AuditLogEntry.sequence_no.desc()).limit(limit).all()
    chain_status = verify_audit_chain_integrity(db)

    blocks = []
    for e in entries:
        blocks.append({
            "sequence_no": e.sequence_no,
            "previous_hash": e.previous_hash,
            "entry_hash": e.entry_hash,
            "timestamp": e.timestamp.isoformat(),
            "timestamp_iso": e.timestamp_iso,
            "actor_id": e.actor_id,
            "actor_role": e.actor_role,
            "action": e.action,
            "endpoint": e.endpoint,
            "scope_battalion": e.scope_battalion,
            "details": e.details_json,
            "is_anomaly": e.is_anomaly,
            "anomaly_score": e.anomaly_score
        })

    return {
        "integrity_status": chain_status,
        "total_returned": len(blocks),
        "blocks": blocks
    }

@router.post("/verify-integrity")
def verify_integrity(
    user: User = Depends(RoleChecker(["admin"])),
    _totp: User = Depends(require_totp_if_enabled),
    db: Session = Depends(get_db)
):
    """
    Cryptographically verifies the entire HMAC-SHA256 hash chain and external anchor.
    Requires step-up TOTP verification.
    """
    result = verify_audit_chain_integrity(db)

    append_audit_entry(
        db=db,
        actor_id=user.username,
        actor_role=user.role,
        action="CRYPTOGRAPHIC_CHAIN_VERIFICATION",
        endpoint="/admin/verify-integrity",
        details={"result": result["valid"], "total_blocks": result["total_blocks"]}
    )

    return result

@router.get("/ids-alerts")
def get_ids_alerts(
    user: User = Depends(RoleChecker(["admin"])),
    _totp: User = Depends(require_totp_if_enabled),
    db: Session = Depends(get_db)
):
    """
    Returns real-time intrusion detection alerts and rogue query intercepts.
    Requires step-up TOTP verification.
    """
    alerts = db.query(AuditLogEntry).filter(
        AuditLogEntry.is_anomaly == True
    ).order_by(AuditLogEntry.sequence_no.desc()).all()

    items = []
    for a in alerts:
        items.append({
            "sequence_no": a.sequence_no,
            "timestamp": a.timestamp.isoformat(),
            "actor_id": a.actor_id,
            "actor_role": a.actor_role,
            "action": a.action,
            "anomaly_score": a.anomaly_score,
            "scope_battalion": a.scope_battalion,
            "details": a.details_json
        })

    return {
        "total_alerts": len(items),
        "alerts": items
    }
