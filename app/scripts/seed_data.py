import os
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

import app.database
from app.database import Base
from app.models.user import User
from app.models.identity import PersonnelIdentity
from app.models.pseudonym import PseudonymMapping
from app.models.wellness import WellnessSignal
from app.models.audit import AuditLogEntry, GENESIS_PREV_HASH
from app.models.case import AlertCase
from app.core.security import hash_password
from app.audit.chain import append_audit_entry

def seed_database(bind_engine=None, session_factory=None):
    """Initializes tables and populates realistic seeded synthetic CAPF data."""
    target_engine = bind_engine or app.database.engine
    target_session_factory = session_factory or app.database.SessionLocal

    # Create all tables
    Base.metadata.create_all(bind=target_engine)
    
    # Auto-migrate legacy columns if present in SQLite
    try:
        with target_engine.connect() as conn:
            from sqlalchemy import text
            res = conn.execute(text("PRAGMA table_info(welfare_alert_cases)"))
            cols = [r[1] for r in res.fetchall()]
            if "action_taken" in cols and "encrypted_action_taken" not in cols:
                conn.execute(text("ALTER TABLE welfare_alert_cases RENAME COLUMN action_taken TO encrypted_action_taken"))
                conn.commit()
            if "clinical_notes" in cols and "encrypted_clinical_notes" not in cols:
                conn.execute(text("ALTER TABLE welfare_alert_cases RENAME COLUMN clinical_notes TO encrypted_clinical_notes"))
                conn.commit()
    except Exception:
        pass
    
    db: Session = target_session_factory()
    try:
        # Check if already seeded
        if db.query(User).first() is not None:
            print("Database already seeded. Skipping initial generation.")
            return

        print("Initializing Cryptographic Core & Seeding Synthetic Records...")

        # 1. Seed Users for each Role
        users_data = [
            # Personnel Persona
            {
                "username": "rajesh_kumar",
                "password": "password123",
                "role": "personnel",
                "assigned_battalion": "104-CRPF",
                "pseudo_id": "PX-7821",
                "is_totp_enabled": False,
                "totp_secret": None
            },
            # Welfare Officer (104-CRPF)
            {
                "username": "welfare_sharma",
                "password": "password123",
                "role": "welfare_officer",
                "assigned_battalion": "104-CRPF",
                "pseudo_id": None,
                "is_totp_enabled": True,
                "totp_secret": "JBSWY3DPEHPK3PXP"
            },
            # Rogue Welfare Officer (42-BSF) for IDS simulation
            {
                "username": "welfare_rogue",
                "password": "password123",
                "role": "welfare_officer",
                "assigned_battalion": "42-BSF",
                "pseudo_id": None,
                "is_totp_enabled": True,
                "totp_secret": "JBSWY3DPEHPK3PXP"
            },
            # Commander (104-CRPF)
            {
                "username": "cmd_singh",
                "password": "password123",
                "role": "commander",
                "assigned_battalion": "104-CRPF",
                "pseudo_id": None,
                "is_totp_enabled": True,
                "totp_secret": "JBSWY3DPEHPK3PXP"
            },
            # Commander (88-ITBP)
            {
                "username": "cmd_itbp",
                "password": "password123",
                "role": "commander",
                "assigned_battalion": "88-ITBP",
                "pseudo_id": None,
                "is_totp_enabled": True,
                "totp_secret": "JBSWY3DPEHPK3PXP"
            },
            # Corps Commander (Multi-Battalion Authorized)
            {
                "username": "cmd_corps",
                "password": "password123",
                "role": "commander",
                "assigned_battalion": "CORPS_COMMAND",
                "pseudo_id": None,
                "is_totp_enabled": True,
                "totp_secret": "JBSWY3DPEHPK3PXP"
            },
            # Security / System Admin (No health data access)
            {
                "username": "sec_admin",
                "password": "password123",
                "role": "admin",
                "assigned_battalion": None,
                "pseudo_id": None,
                "is_totp_enabled": True,
                "totp_secret": "JBSWY3DPEHPK3PXP"
            }
        ]

        for u in users_data:
            user_obj = User(
                username=u["username"],
                hashed_password=hash_password(u["password"]),
                role=u["role"],
                assigned_battalion=u["assigned_battalion"],
                pseudo_id=u["pseudo_id"],
                is_totp_enabled=u["is_totp_enabled"],
                totp_secret=u["totp_secret"]
            )
            db.add(user_obj)
        db.commit()

        # 2. Seed Personnel Identities & Decoupled Wellness Signals
        # Story Personas and Cohorts
        personnel_cohort = [
            # Story Persona 1: Genuine High Distress (Constable Rajesh Kumar)
            {
                "service_no": "CRPF-104-7821",
                "name": "Constable Rajesh Kumar",
                "rank": "Constable / GD",
                "phone": "+91-98765-01001",
                "battalion": "104-CRPF",
                "company": "Bravo",
                "station": "Kupwara (High Altitude / Forward Post)",
                "pseudo_id": "PX-7821",
                # Wellness telemetry
                "phq4": 9.0,
                "mood": 2.5,
                "sleep": 3.5,
                "stress": 9.2,
                "reflection": "Feeling overwhelming exhaustion and family anxiety after cancelled leave. Severe insomnia during night duties.",
                "days_since_leave": 210,
                "denied_leaves": 2,
                "hardship": 4.8,
                "night_shifts": 0.65,
                "sentiment": -0.82
            },
            # Story Persona 2: Noisy / Low Corroboration (Havildar Vikram Singh)
            {
                "service_no": "CRPF-104-4409",
                "name": "Havildar Vikram Singh",
                "rank": "Head Constable",
                "phone": "+91-98765-01002",
                "battalion": "104-CRPF",
                "company": "Alpha",
                "station": "Transit Camp (Peace Station)",
                "pseudo_id": "PX-4409",
                # Wellness telemetry
                "phq4": 10.0,
                "mood": 3.0,
                "sleep": 7.5,
                "stress": 8.5,
                "reflection": "Want urgent inter-battalion transfer to hometown headquarters immediately.",
                "days_since_leave": 22,
                "denied_leaves": 0,
                "hardship": 1.2,
                "night_shifts": 0.10,
                "sentiment": -0.45
            },
            # Story Persona 3: Stigma-Masked Under-Reporting (Naik Sunil Yadav)
            {
                "service_no": "CRPF-104-1290",
                "name": "Naik Sunil Yadav",
                "rank": "Head Constable / GD",
                "phone": "+91-98765-01003",
                "battalion": "104-CRPF",
                "company": "Charlie",
                "station": "Dantewada (Intense Operations)",
                "pseudo_id": "PX-1290",
                # Wellness telemetry: under-reporting self scores despite harsh conditions
                "phq4": 1.0,
                "mood": 8.5,
                "sleep": 4.0,
                "stress": 2.0,
                "reflection": "Duty comes first. No complaints at all, everything is standard.",
                "days_since_leave": 195,
                "denied_leaves": 3,
                "hardship": 4.6,
                "night_shifts": 0.70,
                "sentiment": 0.10
            },
            # Regular Battalion 104-CRPF Personnel (N=12 more to complete cohort of 15)
            {
                "service_no": "CRPF-104-3011",
                "name": "Constable Amit Sharma",
                "rank": "Constable",
                "phone": "+91-98765-01004",
                "battalion": "104-CRPF",
                "company": "Alpha",
                "station": "Kupwara",
                "pseudo_id": "PX-3011",
                "phq4": 2.0,
                "mood": 7.5,
                "sleep": 6.5,
                "stress": 3.0,
                "reflection": "Feeling steady. Regular team camaraderie.",
                "days_since_leave": 75,
                "denied_leaves": 0,
                "hardship": 3.0,
                "night_shifts": 0.35,
                "sentiment": 0.40
            },
            {
                "service_no": "CRPF-104-5522",
                "name": "Sub-Inspector R. K. Nair",
                "rank": "Sub-Inspector",
                "phone": "+91-98765-01005",
                "battalion": "104-CRPF",
                "company": "Alpha",
                "station": "Kupwara",
                "pseudo_id": "PX-5522",
                "phq4": 4.0,
                "mood": 6.0,
                "sleep": 5.5,
                "stress": 5.0,
                "reflection": "Operational tempo is high this week, managing fatigue.",
                "days_since_leave": 110,
                "denied_leaves": 1,
                "hardship": 3.5,
                "night_shifts": 0.45,
                "sentiment": 0.05
            },
            {
                "service_no": "CRPF-104-6633",
                "name": "Constable Deepak Verma",
                "rank": "Constable",
                "phone": "+91-98765-01006",
                "battalion": "104-CRPF",
                "company": "Bravo",
                "station": "Kupwara",
                "pseudo_id": "PX-6633",
                "phq4": 3.0,
                "mood": 7.0,
                "sleep": 6.0,
                "stress": 4.0,
                "reflection": "Routine patrol duties completed without incidents.",
                "days_since_leave": 80,
                "denied_leaves": 0,
                "hardship": 3.2,
                "night_shifts": 0.30,
                "sentiment": 0.35
            },
            {
                "service_no": "CRPF-104-7744",
                "name": "Head Constable Mohan Lal",
                "rank": "Head Constable",
                "phone": "+91-98765-01007",
                "battalion": "104-CRPF",
                "company": "Charlie",
                "station": "Kupwara",
                "pseudo_id": "PX-7744",
                "phq4": 6.0,
                "mood": 5.0,
                "sleep": 5.0,
                "stress": 6.5,
                "reflection": "Minor joint aches in cold weather, resting off-duty.",
                "days_since_leave": 140,
                "denied_leaves": 1,
                "hardship": 4.0,
                "night_shifts": 0.50,
                "sentiment": -0.15
            },
            {
                "service_no": "CRPF-104-8855",
                "name": "Constable Gurpreet Singh",
                "rank": "Constable",
                "phone": "+91-98765-01008",
                "battalion": "104-CRPF",
                "company": "Alpha",
                "station": "Kupwara",
                "pseudo_id": "PX-8855",
                "phq4": 1.0,
                "mood": 8.0,
                "sleep": 7.0,
                "stress": 2.5,
                "reflection": "Good morale. Celebrated unit sports day.",
                "days_since_leave": 45,
                "denied_leaves": 0,
                "hardship": 2.5,
                "night_shifts": 0.20,
                "sentiment": 0.60
            },
            {
                "service_no": "CRPF-104-9966",
                "name": "Constable Sanjay Patil",
                "rank": "Constable",
                "phone": "+91-98765-01009",
                "battalion": "104-CRPF",
                "company": "Bravo",
                "station": "Kupwara",
                "pseudo_id": "PX-9966",
                "phq4": 2.0,
                "mood": 7.5,
                "sleep": 6.5,
                "stress": 3.0,
                "reflection": "All well. Family contacted over satellite phone.",
                "days_since_leave": 60,
                "denied_leaves": 0,
                "hardship": 2.8,
                "night_shifts": 0.25,
                "sentiment": 0.50
            },
            {
                "service_no": "CRPF-104-1177",
                "name": "Inspector B. S. Rathore",
                "rank": "Inspector",
                "phone": "+91-98765-01010",
                "battalion": "104-CRPF",
                "company": "Charlie",
                "station": "Kupwara",
                "pseudo_id": "PX-1177",
                "phq4": 4.0,
                "mood": 6.5,
                "sleep": 6.0,
                "stress": 5.0,
                "reflection": "Administrative burden is high, but managing successfully.",
                "days_since_leave": 105,
                "denied_leaves": 0,
                "hardship": 3.0,
                "night_shifts": 0.35,
                "sentiment": 0.10
            }
        ]

        # Seed 42-BSF Cohort (6 personnel)
        for i in range(1, 7):
            personnel_cohort.append({
                "service_no": f"BSF-42-{2000+i}",
                "name": f"BSF Personnel #{i}",
                "rank": "Constable / GD",
                "phone": f"+91-98765-0200{i}",
                "battalion": "42-BSF",
                "company": "Echo",
                "station": "Jaisalmer Border Post",
                "pseudo_id": f"BSF-{2000+i}",
                "phq4": float(i % 5),
                "mood": float(10 - (i % 5)),
                "sleep": 6.5,
                "stress": float(2 + (i % 4)),
                "reflection": "Desert border patrol duties routine.",
                "days_since_leave": 40 + (i * 15),
                "denied_leaves": i % 2,
                "hardship": 2.5,
                "night_shifts": 0.30,
                "sentiment": 0.20
            })

        # Seed small 88-ITBP Cohort (Only 3 personnel - triggers k-anonymity suppression demo!)
        for i in range(1, 4):
            personnel_cohort.append({
                "service_no": f"ITBP-88-{3000+i}",
                "name": f"ITBP Personnel #{i}",
                "rank": "Constable",
                "phone": f"+91-98765-0300{i}",
                "battalion": "88-ITBP",
                "company": "High Altitude Outpost",
                "station": "Ladakh Forward Post",
                "pseudo_id": f"ITBP-{3000+i}",
                "phq4": 5.0,
                "mood": 5.0,
                "sleep": 5.0,
                "stress": 6.0,
                "reflection": "Sub-zero temperatures, intense physical exertion.",
                "days_since_leave": 150,
                "denied_leaves": 1,
                "hardship": 4.9,
                "night_shifts": 0.50,
                "sentiment": -0.10
            })

        for p in personnel_cohort:
            # 1. Add Personnel Identity (Column-level encrypted via TypeDecorator)
            s_hash = PersonnelIdentity.compute_service_hash(p["service_no"])
            ident = PersonnelIdentity(
                service_no=p["service_no"],
                name=p["name"],
                rank=p["rank"],
                phone=p["phone"],
                battalion_code=p["battalion"],
                company=p["company"],
                station=p["station"],
                service_no_hash=s_hash
            )
            db.add(ident)
            db.flush()

            # 2. Add Pseudonym Mapping
            pseudo_map = PseudonymMapping(
                pseudo_id=p["pseudo_id"],
                personnel_identity_id=ident.id,
                salt=os.urandom(16).hex(),
                rotation_epoch=1,
                is_active=True
            )
            db.add(pseudo_map)

            # 3. Add Decoupled Encrypted Wellness Signal
            wellness = WellnessSignal(
                pseudo_id=p["pseudo_id"],
                battalion_code=p["battalion"],
                phq4_score=p["phq4"],
                mood_score=p["mood"],
                sleep_hours=p["sleep"],
                stress_rating=p["stress"],
                reflection_text=p["reflection"],
                days_since_leave=p["days_since_leave"],
                denied_leaves=p["denied_leaves"],
                deployment_hardship=p["hardship"],
                night_shifts_ratio=p["night_shifts"],
                sentiment_polarity=p["sentiment"],
                is_crisis_override=False
            )
            db.add(wellness)

        # 4. Seed initial AlertCase for top priority case PX-7821
        top_case = AlertCase(
            case_id="CASE-104-7821",
            pseudo_id="PX-7821",
            battalion_code="104-CRPF",
            status="OPEN",
            priority_tier="CRITICAL",
            clinical_notes="Flagged for severe leave deficit (210 days) and circadian insomnia.",
            action_taken="Queued for welfare officer evaluation"
        )
        db.add(top_case)

        db.commit()

        # 5. Genesis Entry for HMAC-SHA256 Tamper-Evident Audit Chain
        append_audit_entry(
            db=db,
            actor_id="SYSTEM_INITIALIZER",
            actor_role="SYSTEM",
            action="GENESIS_INITIALIZATION",
            endpoint="/internal/init",
            details={
                "event": "Cryptographic Core Bootstrapped",
                "system": "Prismarine Defense Welfare Platform",
                "status": "ALL_TABLES_ENCRYPTED_AES_256_GCM",
                "hmac_scheme": "HMAC-SHA256-EXTERNAL-KEY",
                "timestamp_utc": datetime.now(timezone.utc).isoformat()
            }
        )

        print("Synthetic dataset successfully generated and encrypted at rest!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()

