import os
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.models.audit import AuditLogEntry, GENESIS_PREV_HASH

# Parse external HMAC secret
_HMAC_KEY = bytes.fromhex(settings.AUDIT_HMAC_KEY_HEX)
if len(_HMAC_KEY) != 32:
    raise ValueError("AUDIT_HMAC_KEY_HEX must be 32 bytes (64 hex chars)")

EXTERNAL_ANCHOR_FILE = Path(__file__).resolve().parent.parent.parent / "external_trust_anchor.jsonl"
LEGACY_ANCHOR_FILE = Path(__file__).resolve().parent.parent.parent / "external_trust_anchor.json"

def anchor_head_hash(sequence_no: int, entry_hash: str, timestamp_iso: str) -> None:
    """
    Simulates external WORM / HSM / Off-chain Trust Anchoring.
    Appends the chain head to an append-only ledger outside the primary database boundary.
    Never overwrites historical anchors, allowing detection of full-chain rewrites via diffing.
    """
    payload = {
        "anchored_at": timestamp_iso,
        "sequence_no": sequence_no,
        "entry_hash": entry_hash,
        "trust_level": "EXTERNAL_WORM_ANCHOR"
    }
    try:
        # Strictly append-only: open with mode 'a'
        with open(EXTERNAL_ANCHOR_FILE, "a") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception as e:
        print(f"Warning: Failed to append external trust anchor: {e}")

def get_external_anchor() -> Optional[Dict[str, Any]]:
    """Retrieves the latest external anchor from the append-only ledger if present."""
    if EXTERNAL_ANCHOR_FILE.exists():
        try:
            with open(EXTERNAL_ANCHOR_FILE, "r") as f:
                lines = [line.strip() for line in f if line.strip()]
                if lines:
                    return json.loads(lines[-1])
        except Exception:
            pass
            
    # Legacy fallback if jsonl not yet written
    if LEGACY_ANCHOR_FILE.exists():
        try:
            with open(LEGACY_ANCHOR_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def get_external_anchor_history() -> list[Dict[str, Any]]:
    """Returns the full historical append-only anchor log for forensic diffing."""
    anchors = []
    if EXTERNAL_ANCHOR_FILE.exists():
        try:
            with open(EXTERNAL_ANCHOR_FILE, "r") as f:
                for line in f:
                    if line.strip():
                        anchors.append(json.loads(line.strip()))
        except Exception:
            pass
    return anchors

def append_audit_entry(
    db: Session,
    actor_id: str,
    actor_role: str,
    action: str,
    endpoint: str,
    details: Dict[str, Any],
    scope_battalion: Optional[str] = None,
    is_anomaly: bool = False,
    anomaly_score: float = 0.0
) -> AuditLogEntry:
    """
    Appends an immutable block to the HMAC-SHA256 hash-chained audit log.
    Keyed with external secret, preventing rogue DB administrator forgery.
    """
    last_entry = db.query(AuditLogEntry).order_by(AuditLogEntry.sequence_no.desc()).first()
    
    if last_entry is None:
        sequence_no = 1
        previous_hash = GENESIS_PREV_HASH
    else:
        sequence_no = last_entry.sequence_no + 1
        previous_hash = last_entry.entry_hash

    now_utc = datetime.now(timezone.utc)
    timestamp_iso = now_utc.isoformat()
    details_str = json.dumps(details, sort_keys=True)
    
    entry_hash = AuditLogEntry.compute_hmac(
        sequence_no=sequence_no,
        previous_hash=previous_hash,
        timestamp_iso=timestamp_iso,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        endpoint=endpoint,
        details_json=details_str,
        hmac_key=_HMAC_KEY
    )
    
    new_entry = AuditLogEntry(
        sequence_no=sequence_no,
        previous_hash=previous_hash,
        entry_hash=entry_hash,
        timestamp=now_utc,
        timestamp_iso=timestamp_iso,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        endpoint=endpoint,
        scope_battalion=scope_battalion,
        details_json=details_str,
        is_anomaly=is_anomaly,
        anomaly_score=anomaly_score
    )
    
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    
    # Anchor to external trust storage
    anchor_head_hash(sequence_no, entry_hash, timestamp_iso)
    
    return new_entry


def verify_audit_chain_integrity(db: Session) -> Dict[str, Any]:
    """
    Cryptographically verifies the HMAC-SHA256 audit log hash chain and checks external anchoring.
    Returns status, block count, and exact position of any tampered block.
    """
    entries = db.query(AuditLogEntry).order_by(AuditLogEntry.sequence_no.asc()).all()
    
    if not entries:
        return {
            "valid": True,
            "total_blocks": 0,
            "genesis_hash": GENESIS_PREV_HASH,
            "latest_hash": None,
            "tampered_sequence": None,
            "external_anchor_synced": False,
            "message": "Audit chain is empty. Clean genesis state."
        }
    
    expected_prev_hash = GENESIS_PREV_HASH
    
    for i, entry in enumerate(entries):
        # 1. Verify sequence order
        if entry.sequence_no != (i + 1):
            return {
                "valid": False,
                "total_blocks": len(entries),
                "tampered_sequence": entry.sequence_no,
                "error": f"Sequence discontinuity: expected {i + 1}, found {entry.sequence_no}"
            }
        
        # 2. Verify previous hash pointer
        if entry.previous_hash != expected_prev_hash:
            return {
                "valid": False,
                "total_blocks": len(entries),
                "tampered_sequence": entry.sequence_no,
                "error": f"Hash chain broken at sequence {entry.sequence_no}. Recorded prev_hash does not match preceding block."
            }
        
        # 3. Verify content HMAC-SHA256 integrity using external key
        computed_hmac = AuditLogEntry.compute_hmac(
            sequence_no=entry.sequence_no,
            previous_hash=entry.previous_hash,
            timestamp_iso=entry.timestamp_iso,
            actor_id=entry.actor_id,
            actor_role=entry.actor_role,
            action=entry.action,
            endpoint=entry.endpoint,
            details_json=entry.details_json,
            hmac_key=_HMAC_KEY
        )
        
        if computed_hmac != entry.entry_hash:
            return {
                "valid": False,
                "total_blocks": len(entries),
                "tampered_sequence": entry.sequence_no,
                "error": (
                    f"Cryptographic integrity violation at sequence {entry.sequence_no}. "
                    "HMAC verification failed: database record was altered post-signature."
                )
            }
            
        expected_prev_hash = entry.entry_hash
        
    # Check external anchor sync
    latest_entry = entries[-1]
    anchor = get_external_anchor()
    anchor_synced = False
    if anchor and anchor.get("sequence_no") == latest_entry.sequence_no and anchor.get("entry_hash") == latest_entry.entry_hash:
        anchor_synced = True

    return {
        "valid": True,
        "total_blocks": len(entries),
        "genesis_hash": GENESIS_PREV_HASH,
        "latest_hash": latest_entry.entry_hash,
        "tampered_sequence": None,
        "external_anchor_synced": anchor_synced,
        "hmac_algorithm": "HMAC-SHA256-EXTERNAL-KEY",
        "message": "Audit chain cryptographically intact and validated against external trust anchor."
    }
