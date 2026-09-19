from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.identity import PersonnelIdentity
from app.models.pseudonym import PseudonymMapping
from app.models.wellness import WellnessSignal
from app.models.case import AlertCase
from app.core.dependencies import RoleChecker, require_totp_if_enabled
from app.ids.anomaly_detector import ids_engine
from app.audit.chain import append_audit_entry
from app.analytics.risk_model import calculate_stress_risk
from app.analytics.alert_engine import alert_engine
from app.analytics.explainability import generate_explainability_summary

router = APIRouter(prefix="/welfare", tags=["Welfare Officer Console"])

class BreakGlassRequest(BaseModel):
    pseudo_id: str = Field(..., description="The rotating pseudonym to re-identify (e.g. PX-7821)")
    emergency_justification: str = Field(..., min_length=15, description="Documented clinical justification for unmasking")
    dispatch_code: str = Field(..., description="Crisis intervention dispatch or medical ticket code")

class BreakGlassResponse(BaseModel):
    status: str
    pseudo_id: str
    real_name: str
    service_no: str
    rank: str
    phone: Optional[str]
    station: str
    company: str
    audit_sequence: int
    warning: str

class UpdateCaseStatusRequest(BaseModel):
    status: str = Field(..., description="New status: ACKNOWLEDGED, IN_PROGRESS, RESOLVED")
    clinical_notes: Optional[str] = Field(None, description="Confidential clinical/welfare notes")
    action_taken: Optional[str] = Field(None, description="Action taken (e.g. R&R Leave Sanctioned, Counseling Completed)")

@router.get("/alerts")
def get_prioritized_alerts(
    target_battalion: Optional[str] = Query(None, description="Battalion code to query"),
    user: User = Depends(RoleChecker(["welfare_officer"])),
    db: Session = Depends(get_db)
):
    """
    Returns the Game-Theoretic Prioritized Alert Queue for the Welfare Officer's assigned battalion.
    Access-Pattern IDS actively inspects query scope to prevent cross-battalion snooping.
    Crisis overrides bypass ranking to top priority unconditionally.
    Stateful: Excludes resolved cases from active capacity allocation.
    """
    battalion_to_query = target_battalion or user.assigned_battalion

    # 1. ACCESS-PATTERN IDS CHECK
    is_threat, anomaly_score, reason = ids_engine.inspect_access(
        actor_id=user.username,
        actor_role=user.role,
        assigned_battalion=user.assigned_battalion,
        target_battalion=battalion_to_query,
        action="VIEW_COHORT_ALERTS",
        endpoint="/welfare/alerts"
    )

    if is_threat:
        append_audit_entry(
            db=db,
            actor_id=user.username,
            actor_role=user.role,
            action="IDS_INTRUSION_INTERCEPTED",
            endpoint="/welfare/alerts",
            scope_battalion=battalion_to_query,
            details={"reason": reason, "attempted_battalion": battalion_to_query, "officer_assigned": user.assigned_battalion},
            is_anomaly=True,
            anomaly_score=anomaly_score
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Security Alert: {reason}"
        )

    # 2. Identify resolved cases to maintain stateful workflow
    resolved_cases = db.query(AlertCase.pseudo_id).filter(
        AlertCase.battalion_code == battalion_to_query,
        AlertCase.status == "RESOLVED"
    ).all()
    resolved_pseudo_ids = {r[0] for r in resolved_cases}

    # 3. Fetch wellness signals for the battalion
    signals = db.query(WellnessSignal).filter(
        WellnessSignal.battalion_code == battalion_to_query
    ).all()

    evaluations = []
    for s in signals:
        risk = calculate_stress_risk(
            phq4_score=s.phq4_score,
            mood_score=s.mood_score,
            sleep_hours=s.sleep_hours,
            stress_rating=s.stress_rating,
            days_since_leave=s.days_since_leave,
            denied_leaves=s.denied_leaves,
            deployment_hardship=s.deployment_hardship,
            night_shifts_ratio=s.night_shifts_ratio,
            sentiment_polarity=s.sentiment_polarity,
            reflection_text=s.reflection_text or ""
        )

        game_eval = alert_engine.evaluate_personnel_signal(
            pseudo_id=s.pseudo_id,
            risk_data=risk
        )

        explain = generate_explainability_summary(game_eval)
        game_eval["explainability"] = explain
        
        # Attach case status if exists
        case = db.query(AlertCase).filter(AlertCase.pseudo_id == s.pseudo_id).first()
        game_eval["case_status"] = case.status if case else "OPEN"
        game_eval["case_id"] = case.case_id if case else f"CASE-{s.pseudo_id}"
        
        evaluations.append(game_eval)

    # 4. Apply Game-Theoretic Prioritization with bounded capacity C and resolved case filtering
    prioritization_result = alert_engine.prioritize_cohort_alerts(
        evaluations, 
        resolved_pseudo_ids=resolved_pseudo_ids
    )
    prioritization_result["battalion"] = battalion_to_query

    # 5. Append authorized access to audit chain
    append_audit_entry(
        db=db,
        actor_id=user.username,
        actor_role=user.role,
        action="VIEW_COHORT_ALERTS",
        endpoint="/welfare/alerts",
        scope_battalion=battalion_to_query,
        details={
            "battalion": battalion_to_query,
            "allocated_alerts": prioritization_result["allocated_count"],
            "deferred_alerts": prioritization_result["deferred_count"]
        }
    )

    return prioritization_result


@router.post("/break-glass", response_model=BreakGlassResponse)
def break_glass_reidentify(
    req: BreakGlassRequest,
    user: User = Depends(RoleChecker(["welfare_officer"])),
    _totp: User = Depends(require_totp_if_enabled),
    db: Session = Depends(get_db)
):
    """
    Emergency Re-Identification Protocol.
    Unmasks a pseudo_id to its real service identity under strict life-safety criteria.
    Requires step-up TOTP verification and permanent hash-chained audit logging.
    """
    pseudo_map = db.query(PseudonymMapping).filter(
        PseudonymMapping.pseudo_id == req.pseudo_id
    ).first()

    if not pseudo_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pseudonym '{req.pseudo_id}' not found in active registry."
        )

    identity = db.query(PersonnelIdentity).filter(
        PersonnelIdentity.id == pseudo_map.personnel_identity_id
    ).first()

    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked personnel identity record missing."
        )

    # Unit scope validation
    if user.assigned_battalion and identity.battalion_code != user.assigned_battalion:
        append_audit_entry(
            db=db,
            actor_id=user.username,
            actor_role=user.role,
            action="UNAUTHORIZED_REIDENTIFICATION_ATTEMPT",
            endpoint="/welfare/break-glass",
            scope_battalion=identity.battalion_code,
            details={
                "target_pseudo_id": req.pseudo_id,
                "target_battalion": identity.battalion_code,
                "officer_battalion": user.assigned_battalion,
                "justification": req.emergency_justification
            },
            is_anomaly=True,
            anomaly_score=0.99
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: Personnel belongs to '{identity.battalion_code}', outside your assigned battalion '{user.assigned_battalion}'."
        )

    # Log the authorized break-glass event to the tamper-evident audit log
    audit_entry = append_audit_entry(
        db=db,
        actor_id=user.username,
        actor_role=user.role,
        action="BREAK_GLASS_REIDENTIFY",
        endpoint="/welfare/break-glass",
        scope_battalion=identity.battalion_code,
        details={
            "pseudo_id": req.pseudo_id,
            "dispatch_code": req.dispatch_code,
            "emergency_justification": req.emergency_justification,
            "unmasked_service_hash": identity.service_no_hash
        },
        is_anomaly=False
    )

    return BreakGlassResponse(
        status="REIDENTIFICATION_SUCCESSFUL",
        pseudo_id=req.pseudo_id,
        real_name=identity.name,
        service_no=identity.service_no,
        rank=identity.rank,
        phone=identity.phone,
        station=identity.station,
        company=identity.company,
        audit_sequence=audit_entry.sequence_no,
        warning="This emergency unmasking has been permanently signed and etched into the HMAC-SHA256 audit chain."
    )


@router.patch("/cases/{case_id}/status")
def update_case_status(
    case_id: str,
    req: UpdateCaseStatusRequest,
    user: User = Depends(RoleChecker(["welfare_officer"])),
    db: Session = Depends(get_db)
):
    """
    Updates welfare case status (OPEN -> ACKNOWLEDGED -> IN_PROGRESS -> RESOLVED).
    Ensures stateful workflow management rather than static recomputed leaderboards.
    """
    valid_statuses = ["OPEN", "ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED"]
    status_upper = req.status.upper()
    if status_upper not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of {valid_statuses}"
        )

    case = db.query(AlertCase).filter(AlertCase.case_id == case_id).first()
    if not case:
        # Auto-create case if not yet created
        pseudo = case_id.replace("CASE-", "")
        case = AlertCase(
            case_id=case_id,
            pseudo_id=pseudo,
            battalion_code=user.assigned_battalion or "104-CRPF",
            status=status_upper,
            assigned_officer=user.username,
            clinical_notes=req.clinical_notes,
            action_taken=req.action_taken
        )
        db.add(case)
    else:
        case.status = status_upper
        case.assigned_officer = user.username
        if req.clinical_notes:
            case.clinical_notes = req.clinical_notes
        if req.action_taken:
            case.action_taken = req.action_taken
        case.updated_at = datetime.now(timezone.utc)

    db.commit()

    append_audit_entry(
        db=db,
        actor_id=user.username,
        actor_role=user.role,
        action="UPDATE_WELFARE_CASE_STATUS",
        endpoint=f"/welfare/cases/{case_id}/status",
        scope_battalion=case.battalion_code,
        details={
            "case_id": case_id,
            "pseudo_id": case.pseudo_id,
            "new_status": status_upper,
            "action_taken": req.action_taken
        }
    )

    return {
        "status": "UPDATED",
        "case_id": case.case_id,
        "pseudo_id": case.pseudo_id,
        "new_status": case.status,
        "action_taken": case.action_taken,
        "updated_at": case.updated_at.isoformat()
    }
