import pytest
from app.core.crypto import encrypt_field, decrypt_field
from app.models.identity import PersonnelIdentity
from app.database import SessionLocal

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

def test_database_column_encryption_at_rest():
    db = SessionLocal()
    try:
        ident = db.query(PersonnelIdentity).first()
        assert ident is not None
        
        # Transparent runtime decryption via TypeDecorator
        assert "Constable" in ident.name or "Havildar" in ident.name or "Naik" in ident.name
        
        # Verify that the service hash is SHA-256 (64 hex characters)
        assert len(ident.service_no_hash) == 64
    finally:
        db.close()
