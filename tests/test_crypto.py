import pytest
from app.core.crypto import encrypt_field, decrypt_field
from app.models.identity import PersonnelIdentity
from app.models.case import AlertCase
from sqlalchemy import text

def test_aes_gcm_encryption_decryption():
    raw_text = "PARAM MILITARY CLASSIFIED PSYCH EVALUATION: PHQ-9 SCORE = 18"
    ciphertext = encrypt_field(raw_text)
    
    assert ciphertext is not None
    assert ciphertext != raw_text
    assert len(ciphertext) > len(raw_text)
    
    decrypted = decrypt_field(ciphertext)
    assert decrypted == raw_text

def test_aes_gcm_tamper_rejection():
    raw_text = "CONFIDENTIAL PERSONNEL RECORD"
    ciphertext = encrypt_field(raw_text)
    
    # Tamper with the ciphertext bytes
    tampered = ciphertext[:-6] + "XYZ123"
    decrypted = decrypt_field(tampered)
    
    # GCM authentication tag verification must reject tampered ciphertext
    assert decrypted is None

def test_database_column_encryption_at_rest(db):
    ident = db.query(PersonnelIdentity).first()
    assert ident is not None
    
    # Transparent runtime decryption via TypeDecorator
    assert "Constable" in ident.name or "Havildar" in ident.name or "Naik" in ident.name
    
    # Verify that the service hash is SHA-256 (64 hex characters)
    assert len(ident.service_no_hash) == 64

def test_alert_case_clinical_notes_encryption_at_rest(db):
    # Verify AlertCase clinical notes and action_taken are encrypted on disk
    test_case = AlertCase(
        case_id="TEST-CASE-CRYPTO",
        pseudo_id="PX-TEST-99",
        battalion_code="104-CRPF",
        status="OPEN",
        assigned_officer="welfare_sharma",
        clinical_notes="Confidential psychiatric review: severe acute stress with operational burnout.",
        action_taken="14-day rotational R&R leave recommended"
    )
    db.add(test_case)
    db.commit()
    db.refresh(test_case)

    # 1. ORM level transparently decrypts
    assert "Confidential psychiatric review" in test_case.clinical_notes
    assert "rotational R&R leave" in test_case.action_taken

    # 2. Raw SQL level proves ciphertext is stored on disk (no plaintext on disk)
    raw_row = db.execute(text("SELECT encrypted_clinical_notes, encrypted_action_taken FROM welfare_alert_cases WHERE case_id = 'TEST-CASE-CRYPTO'")).first()
    assert raw_row is not None
    raw_notes, raw_action = raw_row[0], raw_row[1]

    assert raw_notes is not None
    assert "Confidential psychiatric review" not in raw_notes
    assert raw_notes != "Confidential psychiatric review: severe acute stress with operational burnout."

    assert raw_action is not None
    assert "rotational R&R leave" not in raw_action
    assert raw_action != "14-day rotational R&R leave recommended"
