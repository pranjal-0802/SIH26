import pytest
from app.database import SessionLocal
from app.models.audit import AuditLogEntry
from app.audit.chain import append_audit_entry, verify_audit_chain_integrity, get_external_anchor

def test_hmac_hash_chain_integrity_and_anchoring():
    db = SessionLocal()
    try:
        status_clean = verify_audit_chain_integrity(db)
        assert status_clean["valid"] is True
        assert status_clean["total_blocks"] >= 1
        assert status_clean["external_anchor_synced"] is True

        entry = append_audit_entry(
            db=db,
            actor_id="TEST_SECURITY_OFFICER",
            actor_role="ADMIN",
            action="SECURITY_PATROL_CHECK",
            endpoint="/test/patrol",
            details={"perimeter": "NORTH_SECTOR_SECURE"}
        )
        assert entry.sequence_no > 1

        # Check external anchor updated
        anchor = get_external_anchor()
        assert anchor is not None
        assert anchor["sequence_no"] == entry.sequence_no
        assert anchor["entry_hash"] == entry.entry_hash

        status_after_add = verify_audit_chain_integrity(db)
        assert status_after_add["valid"] is True
        assert status_after_add["external_anchor_synced"] is True

        # Simulate rogue DBA modifying details in database directly
        original_details = entry.details_json
        entry.details_json = '{"perimeter": "MODIFIED_BY_ROGUE_DBA"}'
        db.commit()

        # Chain verification must immediately fail due to HMAC signature mismatch
        status_tampered = verify_audit_chain_integrity(db)
        assert status_tampered["valid"] is False
        assert status_tampered["tampered_sequence"] == entry.sequence_no
        assert "HMAC verification failed" in status_tampered["error"]

        # Restore original content
        entry.details_json = original_details
        db.commit()

        status_restored = verify_audit_chain_integrity(db)
        assert status_restored["valid"] is True
    finally:
        db.close()
