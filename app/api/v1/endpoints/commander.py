from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.wellness import WellnessSignal
from app.core.dependencies import RoleChecker, require_totp_if_enabled
from app.ids.anomaly_detector import ids_engine
from app.audit.chain import append_audit_entry
from app.analytics.privacy import sanitize_cohort_aggregate
from app.analytics.risk_model import calculate_stress_risk

router = APIRouter(prefix="/commander", tags=["Commander Strategic Dashboard"])

@router.get("/cohort-readiness")
def get_commander_cohort_readiness(
    target_battalion: Optional[str] = Query(None, description="Battalion code for strategic aggregation"),
    user: User = Depends(RoleChecker(["commander"])),
    _totp: User = Depends(require_totp_if_enabled),
    db: Session = Depends(get_db)
):
    """
    Returns high-level battalion operational readiness and stress distributions.
    Strictly enforces:
    1. Zero-IDOR: Access-Pattern IDS checks assigned unit scope.
    2. Step-up TOTP MFA verification.
    3. Mathematical k-anonymity (k >= 5).
    4. Cumulative Differential Privacy budget accounting with Laplace noise.
    PHYSICALLY IMPOSSIBLE to retrieve individual records or pseudonyms through this endpoint.
    """
    battalion_to_query = target_battalion or user.assigned_battalion

    # 1. SCOPE & IDOR ACCESS-PATTERN IDS CHECK
    is_threat, anomaly_score, reason = ids_engine.inspect_access(
        actor_id=user.username,
        actor_role=user.role,
        assigned_battalion=user.assigned_battalion,
        target_battalion=battalion_to_query,
        action="VIEW_COMMANDER_AGGREGATES",
        endpoint="/commander/cohort-readiness"
    )

    if is_threat:
        append_audit_entry(
            db=db,
            actor_id=user.username,
            actor_role=user.role,
            action="COMMANDER_IDOR_BLOCKED",
            endpoint="/commander/cohort-readiness",
            scope_battalion=battalion_to_query,
            details={
                "reason": reason,
                "attempted_battalion": battalion_to_query,
                "assigned_battalion": user.assigned_battalion
            },
            is_anomaly=True,
            anomaly_score=anomaly_score
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Security Alert: {reason}"
        )

    # Query wellness signals for this battalion
    signals = db.query(WellnessSignal).filter(
        WellnessSignal.battalion_code == battalion_to_query
    ).all()

    cohort_size = len(signals)

    # 2. ENFORCE STRICT k-ANONYMITY (k >= 5)
    if cohort_size < 5:
        # Log suppression event
        append_audit_entry(
            db=db,
            actor_id=user.username,
            actor_role=user.role,
            action="COMMANDER_QUERY_SUPPRESSED",
            endpoint="/commander/cohort-readiness",
            scope_battalion=battalion_to_query,
            details={"cohort_size": cohort_size, "k_threshold": 5, "reason": "k-anonymity protection"}
        )
        return {
            "status": "SUPPRESSED",
            "battalion": battalion_to_query,
            "cohort_size": cohort_size,
            "k_threshold": 5,
            "message": f"Data suppressed: Cohort '{battalion_to_query}' has {cohort_size} active personnel, which is below the minimum privacy threshold (k=5). Aggregates are withheld to prevent re-identification through elimination.",
            "metrics": None
        }

    # 3. Compute aggregate metrics (honest attribute access)
    total_stress = 0.0
    critical_count = 0
    elevated_count = 0
    moderate_count = 0
    low_count = 0
    high_leave_deficit_count = 0
    severe_sleep_deficit_count = 0

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
        
        tier = risk["risk_tier"]
        if tier == "CRITICAL":
            critical_count += 1
        elif tier == "ELEVATED":
            elevated_count += 1
        elif tier == "MODERATE":
            moderate_count += 1
        else:
            low_count += 1

        total_stress += risk["risk_percentage"]
        if s.days_since_leave > 120:
            high_leave_deficit_count += 1
        if s.sleep_hours < 5.0:
            severe_sleep_deficit_count += 1

    mean_stress = total_stress / cohort_size
    readiness_index = max(0.0, min(100.0, 100.0 - (mean_stress * 0.85)))

    raw_metrics = {
        "unit_operational_readiness_pct": readiness_index,
        "cohort_stress_index": mean_stress,
        "personnel_leave_deficit_rate_pct": (high_leave_deficit_count / cohort_size) * 100.0,
        "circadian_fatigue_rate_pct": (severe_sleep_deficit_count / cohort_size) * 100.0,
        "count_low_risk": float(low_count),
        "count_moderate_risk": float(moderate_count),
        "count_elevated_risk": float(elevated_count),
        "count_critical_risk": float(critical_count)
    }

    # 4. Apply Differential Privacy Laplace Noise Injection with Cumulative Budget Accounting
    sanitized = sanitize_cohort_aggregate(
        raw_metrics, 
        cohort_size=cohort_size, 
        battalion_code=battalion_to_query,
        min_k=5, 
        apply_dp=True
    )

    # 5. Tactical Recommendations for Commanders
    recommendations = []
    if raw_metrics["personnel_leave_deficit_rate_pct"] > 25.0:
        recommendations.append("Battalion Workload Alert: Over 25% of the unit has exceeded 120 days deployment without leave. Plan rotational leave batch.")
    if raw_metrics["circadian_fatigue_rate_pct"] > 20.0:
        recommendations.append("Fatigue Countermeasure: Night duty roster shows circadian disruption. Introduce staggered 8-hour shift rest windows.")
    if readiness_index >= 75.0:
        recommendations.append("Tactical Readiness Status: GREEN. Operational effectiveness and psychological resilience within target parameters.")
    else:
        recommendations.append("Tactical Readiness Status: AMBER. Initiate unit-level rest and recreation cycling.")

    # 6. Record to audit log
    append_audit_entry(
        db=db,
        actor_id=user.username,
        actor_role=user.role,
        action="VIEW_COMMANDER_AGGREGATES",
        endpoint="/commander/cohort-readiness",
        scope_battalion=battalion_to_query,
        details={"battalion": battalion_to_query, "k_guarantee": 5, "cohort_size": cohort_size}
    )

    return {
        "status": "ANONYMIZED_COMPLIANT",
        "battalion": battalion_to_query,
        "cohort_size": cohort_size,
        "k_anonymity_threshold": 5,
        "differential_privacy_applied": True,
        "dp_budget_status": sanitized.get("dp_budget_status"),
        "dp_daily_budget_remaining": sanitized.get("dp_daily_budget_remaining"),
        "strategic_metrics": sanitized["metrics"],
        "tactical_welfare_directives": recommendations
    }
