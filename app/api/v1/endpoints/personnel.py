from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.identity import PersonnelIdentity
from app.models.pseudonym import PseudonymMapping
from app.models.wellness import WellnessSignal
from app.models.case import AlertCase
from app.core.dependencies import RoleChecker
from app.audit.chain import append_audit_entry
from app.analytics.risk_model import check_crisis_indicators

router = APIRouter(prefix="/personnel", tags=["Personnel Self-Assessment"])

class CheckInRequest(BaseModel):
    mood_score: float = Field(..., ge=1.0, le=10.0, description="1 (Severe distress) to 10 (Optimal morale)")
    sleep_hours: float = Field(..., ge=0.0, le=16.0, description="Hours of sleep in last 24 hours")
    stress_rating: float = Field(..., ge=1.0, le=10.0, description="1 (Relaxed) to 10 (Extreme strain)")
    phq4_score: Optional[float] = Field(default=2.0, ge=0.0, le=12.0, description="PHQ-4 screening score")
    reflection_text: Optional[str] = Field(default=None, max_length=1000, description="Optional confidential reflections")

class CheckInResponse(BaseModel):
    status: str
    pseudo_id: str
    message: str
    is_crisis_override: bool
    recorded_at: str
    wellness_tips: List[str]

@router.get("/my-profile")
def get_my_record(
    user: User = Depends(RoleChecker(["personnel"])),
    db: Session = Depends(get_db)
):
    """
    Returns the personnel member's own sovereign profile.
    Decoupled pseudo_id is returned for anonymous check-in tracking.
    """
    pseudo_map = db.query(PseudonymMapping).filter(
        PseudonymMapping.pseudo_id == user.pseudo_id
    ).first()

    if not pseudo_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active pseudonym binding found for your account."
        )

    identity = db.query(PersonnelIdentity).filter(
        PersonnelIdentity.id == pseudo_map.personnel_identity_id
    ).first()

    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personnel identity record not found."
        )

    # Log self access
    append_audit_entry(
        db=db,
        actor_id=user.username,
        actor_role=user.role,
        action="VIEW_SELF_PROFILE",
        endpoint="/personnel/my-profile",
        details={"pseudo_id": user.pseudo_id, "battalion": identity.battalion_code}
    )

    return {
        "service_no": identity.service_no,
        "full_name": identity.name,
        "rank": identity.rank,
        "battalion": identity.battalion_code,
        "company": identity.company,
        "station": identity.station,
        "active_pseudo_id": user.pseudo_id
    }

@router.post("/check-in", response_model=CheckInResponse)
def submit_check_in(
    payload: CheckInRequest,
    user: User = Depends(RoleChecker(["personnel"])),
    db: Session = Depends(get_db)
):
    """
    Confidential self-assessment check-in.
    Telemetry is encrypted with AES-256-GCM and bound only to pseudo_id.
    Includes immediate Crisis Hard-Override for acute self-harm/life-safety signals.
    """
    if not user.pseudo_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have an assigned pseudonym."
        )

    # Crisis indicator hard-override check
    is_crisis, crisis_reason = check_crisis_indicators(payload.reflection_text or "", payload.phq4_score or 0.0)

    # Sentiment calculation
    text_content = (payload.reflection_text or "").lower()
    neg_words = ["exhausted", "tired", "insomnia", "anxiety", "pain", "breakdown", "strained", "struggling"]
    pos_words = ["good", "strong", "ready", "calm", "happy", "energized", "peaceful", "steady"]
    
    score = 0.0
    for w in pos_words:
        if w in text_content:
            score += 0.2
    for w in neg_words:
        if w in text_content:
            score -= 0.35
    if is_crisis:
        score = -1.0
    sentiment = max(-1.0, min(1.0, score))

    existing = db.query(WellnessSignal).filter(
        WellnessSignal.pseudo_id == user.pseudo_id
    ).order_by(WellnessSignal.recorded_at.desc()).first()

    days_since_leave = existing.days_since_leave if existing else 60
    denied_leaves = existing.denied_leaves if existing else 0
    hardship = existing.deployment_hardship if existing else 3.0
    night_shifts = existing.night_shifts_ratio if existing else 0.35

    now_utc = datetime.now(timezone.utc)
    new_signal = WellnessSignal(
        pseudo_id=user.pseudo_id,
        battalion_code=user.assigned_battalion or "104-CRPF",
        phq4_score=payload.phq4_score or 2.0,
        mood_score=payload.mood_score,
        sleep_hours=payload.sleep_hours,
        stress_rating=payload.stress_rating,
        reflection_text=payload.reflection_text or "",
        days_since_leave=days_since_leave,
        denied_leaves=denied_leaves,
        deployment_hardship=hardship,
        night_shifts_ratio=night_shifts,
        sentiment_polarity=sentiment,
        is_crisis_override=is_crisis,
        crisis_rationale=crisis_reason if is_crisis else None,
        recorded_at=now_utc
    )

    db.add(new_signal)
    
    # If crisis detected, immediately create or escalate AlertCase
    if is_crisis:
        existing_case = db.query(AlertCase).filter(AlertCase.pseudo_id == user.pseudo_id).first()
        if existing_case:
            existing_case.status = "OPEN"
            existing_case.priority_tier = "CRITICAL"
            existing_case.is_crisis = True
            existing_case.clinical_notes = f"Escalated by crisis override: {crisis_reason}"
            existing_case.updated_at = now_utc
        else:
            new_case = AlertCase(
                case_id=f"CASE-{user.pseudo_id}",
                pseudo_id=user.pseudo_id,
                battalion_code=user.assigned_battalion or "104-CRPF",
                status="OPEN",
                priority_tier="CRITICAL",
                is_crisis=True,
                clinical_notes=f"Auto-generated via crisis override: {crisis_reason}"
            )
            db.add(new_case)

    db.commit()

    append_audit_entry(
        db=db,
        actor_id=user.username,
        actor_role=user.role,
        action="LIFE_SAFETY_CRISIS_DETECTED" if is_crisis else "SUBMIT_WELLNESS_CHECK_IN",
        endpoint="/personnel/check-in",
        details={
            "pseudo_id": user.pseudo_id,
            "is_crisis_override": is_crisis,
            "timestamp": now_utc.isoformat()
        },
        is_anomaly=is_crisis,
        anomaly_score=0.99 if is_crisis else 0.0
    )

    tips = [
        "Hydration & deep breathing reset: Practice 4-7-8 tactical breathing.",
        "Peer connection: Reach out to your designated buddy after shift.",
        "Confidential support: 24/7 tele-counseling is always available free of stigma."
    ]

    if is_crisis:
        tips.insert(0, "URGENT SUPPORT: You are not alone. Please speak with your Unit Medical Officer or call the confidential 24/7 helpline immediately (*774#).")

    return CheckInResponse(
        status="CRISIS_INTERVENTION_TRIGGERED" if is_crisis else "RECORDED_SECURELY",
        pseudo_id=user.pseudo_id,
        is_crisis_override=is_crisis,
        message=(
            "URGENT: Immediate welfare alert dispatched for your safety. Peer buddy notified."
            if is_crisis else
            "Your check-in has been encrypted and recorded under your private pseudo-ID."
        ),
        recorded_at=now_utc.isoformat(),
        wellness_tips=tips
    )

@router.get("/my-wellness-history")
def get_wellness_history(
    user: User = Depends(RoleChecker(["personnel"])),
    db: Session = Depends(get_db)
):
    """Returns self history of recorded telemetry."""
    records = db.query(WellnessSignal).filter(
        WellnessSignal.pseudo_id == user.pseudo_id
    ).order_by(WellnessSignal.recorded_at.desc()).limit(10).all()

    history = []
    for r in records:
        history.append({
            "recorded_at": r.recorded_at.isoformat(),
            "mood_score": r.mood_score,
            "sleep_hours": r.sleep_hours,
            "stress_rating": r.stress_rating,
            "phq4_score": r.phq4_score,
            "sentiment_polarity": r.sentiment_polarity,
            "is_crisis": r.is_crisis_override
        })

    return {"pseudo_id": user.pseudo_id, "history": history}
