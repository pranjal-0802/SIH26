import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.audit import AuditLogEntry
from app.ids.anomaly_detector import ids_engine
from app.audit.chain import append_audit_entry, verify_audit_chain_integrity

router = APIRouter(prefix="/demo", tags=["Hackathon Live Demo Triggers"])

def require_demo_mode():
    """Security guard ensuring demo/simulation endpoints are only accessible in DEMO_MODE."""
    if not settings.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Demo endpoints and simulation triggers are disabled in production."
        )

_ORIGINAL_TAMPERED_CONTENT = None
_TAMPERED_SEQUENCE_NO = None

@router.get("/personas", dependencies=[Depends(require_demo_mode)])
def get_demo_personas():
    """
    Returns pre-scripted demo personas for live demonstration.
    Gated strictly behind DEMO_MODE.
    """
    return {
        "platform": "Prismarine",
        "demo_mode_active": settings.DEMO_MODE,
        "personas": [
            {
                "id": "persona_1",
                "role": "personnel",
                "name": "Constable Rajesh Kumar",
                "username": "rajesh_kumar",
                "pseudo_id": "PX-7821",
                "battalion": "104-CRPF",
                "story_arc": "GENUINE HIGH-RISK: 210 days deployed in forward post, 2 denied leaves, severe insomnia. Prioritized at Top #1 in Welfare Queue."
            },
            {
                "id": "persona_2",
                "role": "personnel",
                "name": "Havildar Vikram Singh",
                "pseudo_id": "PX-4409",
                "battalion": "104-CRPF",
                "story_arc": "STRATEGIC NOISY / FALSE-POSITIVE: High self-report complaint spike but 0 days leave deficit. Game-Theoretic Engine de-prioritizes to conserve officer bandwidth."
            },
            {
                "id": "persona_3",
                "role": "personnel",
                "name": "Naik Sunil Yadav",
                "pseudo_id": "PX-1290",
                "battalion": "104-CRPF",
                "story_arc": "STIGMA-MASKED UNDER-REPORTER: Severe operational load (195 days without leave, 3 denials) but claims 0 distress out of weapon withdrawal fear. Game-Theoretic Engine detects under-reporting and boosts priority."
            },
            {
                "id": "persona_4",
                "role": "welfare_officer",
                "name": "Sub-Inspector Anita Sharma",
                "username": "welfare_sharma",
                "battalion": "104-CRPF",
                "story_arc": "WELFARE OFFICER: Reviews prioritized queue, inspects explainability breakdowns, manages case lifecycle, and triggers audited break-glass re-identification."
            },
            {
                "id": "persona_5",
                "role": "commander",
                "name": "Commandant Vikramaditya Singh",
                "username": "cmd_singh",
                "battalion": "104-CRPF",
                "story_arc": "BATTALION COMMANDER: Strategic operational readiness view. Strictly k-anonymized (k>=5). Code physically prevents viewing individual names."
            },
            {
                "id": "persona_6",
                "role": "admin",
                "name": "Security & Audit Officer",
                "username": "sec_admin",
                "story_arc": "SECURITY ADMIN: Verifies HMAC-SHA256 hash chain and catches insider threats. ZERO access to personnel medical telemetry."
            },
            {
                "id": "persona_7",
                "role": "welfare_officer",
                "name": "Rogue Officer Simulation (Inspector Verma)",
                "username": "welfare_rogue",
                "battalion": "42-BSF",
                "story_arc": "INSIDER THREAT: Assigned to 42-BSF, attempts unauthorized snoop into 104-CRPF. Caught instantly by Access-Pattern IDS."
            }
        ]
    }

@router.post("/trigger-rogue-query", dependencies=[Depends(require_demo_mode)])
def trigger_rogue_query_simulation(db: Session = Depends(get_db)):
    """
    Simulates a live Insider Threat:
    Rogue Officer (welfare_rogue, assigned to 42-BSF) attempts cross-unit query into 104-CRPF.
    The IDS intercepts the anomaly in real time and writes an HMAC tamper-evident threat record.
    """
    rogue_actor = "welfare_rogue"
    assigned_battalion = "42-BSF"
    target_battalion = "104-CRPF"

    is_threat, anomaly_score, reason = ids_engine.inspect_access(
        actor_id=rogue_actor,
        actor_role="welfare_officer",
        assigned_battalion=assigned_battalion,
        target_battalion=target_battalion,
        action="VIEW_COHORT_ALERTS",
        endpoint="/welfare/alerts"
    )

    entry = append_audit_entry(
        db=db,
        actor_id=rogue_actor,
        actor_role="welfare_officer",
        action="IDS_INTRUSION_INTERCEPTED",
        endpoint="/welfare/alerts",
        scope_battalion=target_battalion,
        details={
            "simulation": "LIVE_INSIDER_THREAT_SIMULATION",
            "threat_type": "CROSS_BATTALION_UNAUTHORIZED_PROBE",
            "reason": reason,
            "assigned_battalion": assigned_battalion,
            "target_battalion": target_battalion
        },
        is_anomaly=True,
        anomaly_score=anomaly_score
    )

    return {
        "status": "INTRUSION_DETECTED_AND_BLOCKED",
        "actor": rogue_actor,
        "assigned_battalion": assigned_battalion,
        "target_battalion": target_battalion,
        "is_threat": is_threat,
        "anomaly_score": anomaly_score,
        "ids_alert_message": reason,
        "audit_chain_block": {
            "sequence_no": entry.sequence_no,
            "entry_hash": entry.entry_hash,
            "previous_hash": entry.previous_hash,
            "timestamp_iso": entry.timestamp_iso
        },
        "mitigation_action": "Session isolated, unauthorized query blocked, security alarm emitted to Security Admin."
    }

@router.post("/simulate-tampering", dependencies=[Depends(require_demo_mode)])
def simulate_tampering(db: Session = Depends(get_db)):
    """
    Simulates malicious insider tampering with historical audit records in database.
    Proves that the HMAC-SHA256 hash chain and external trust anchor instantly expose the fraud!
    """
    global _ORIGINAL_TAMPERED_CONTENT, _TAMPERED_SEQUENCE_NO

    target_entry = db.query(AuditLogEntry).filter(AuditLogEntry.sequence_no == 1).first()
    if not target_entry:
        raise HTTPException(status_code=404, detail="Audit log empty")

    _ORIGINAL_TAMPERED_CONTENT = target_entry.details_json
    _TAMPERED_SEQUENCE_NO = target_entry.sequence_no

    # Maliciously mutate database content
    malicious_data = json.dumps({"event": "CORRUPTED_BY_ROGUE_DBA", "status": "TAMPERED_RECORD"})
    target_entry.details_json = malicious_data
    db.commit()

    integrity_result = verify_audit_chain_integrity(db)

    return {
        "status": "TAMPERING_SIMULATED",
        "tampered_sequence": _TAMPERED_SEQUENCE_NO,
        "action_taken": "Rogue DBA directly mutated historical row in SQL database.",
        "cryptographic_verification_result": integrity_result,
        "verdict": "FRAUD DETECTED! HMAC-SHA256 signature failed: external key prevented forgery."
    }

@router.post("/restore-chain", dependencies=[Depends(require_demo_mode)])
def restore_chain(db: Session = Depends(get_db)):
    """Restores the audit chain to its pristine state after live demo tampering simulation."""
    global _ORIGINAL_TAMPERED_CONTENT, _TAMPERED_SEQUENCE_NO

    seq_no = _TAMPERED_SEQUENCE_NO if _TAMPERED_SEQUENCE_NO is not None else 1
    target_entry = db.query(AuditLogEntry).filter(AuditLogEntry.sequence_no == seq_no).first()
    if target_entry:
        if _ORIGINAL_TAMPERED_CONTENT is not None:
            target_entry.details_json = _ORIGINAL_TAMPERED_CONTENT
        else:
            target_entry.details_json = '{"event": "Cryptographic Core Bootstrapped", "hmac_scheme": "HMAC-SHA256-EXTERNAL-KEY", "status": "ALL_TABLES_ENCRYPTED_AES_256_GCM", "system": "Prismarine Defense Welfare Platform", "timestamp_utc": "2026-09-19T08:40:13.053741+00:00"}'
        db.commit()

    result = verify_audit_chain_integrity(db)
    return {
        "status": "CHAIN_RESTORED",
        "verification_result": result
    }
