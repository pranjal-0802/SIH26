# System Architecture & Trust Boundaries Specification
**Document Version:** 1.0.0  
**Classification:** RESTRICTED / DEFENSE SPECIFICATION  

---

## 1. High-Level Architecture Diagram

```
+─────────────────────────────────────────────────────────────────────────────────────────────+
|                                    ZONE 0: CLIENT LAYER                                    |
|                                                                                             |
|   +────────────────────────+    +────────────────────────+    +─────────────────────────+   |
|   | Personnel PWA Mobile   |    | Welfare Officer Console|    | Commander Cohort View   |   |
|   | (Daily Check-in, Mood, |    | (Prioritized Queue,    |    | (Tactical Readiness,    |   |
|   | Sleep, Self-History)   |    | Explainable Alerts)    |    | k-Anonymized Heatmaps)  |   |
|   +───────────┬────────────+    +───────────┬────────────+    +────────────┬────────────+   |
|               │                             │                              │                |
+───────────────┼─────────────────────────────┼──────────────────────────────┼────────────────+
                │ HTTPS (TLS 1.3)             │ HTTPS (TLS 1.3)              │ HTTPS (TLS 1.3)
════════════════╪═════════════════════════════╪══════════════════════════════╪════════════════
[TRUST BOUNDARY 1: Edge & Ingress Authentication]
════════════════╪═════════════════════════════╪══════════════════════════════╪════════════════
+───────────────┼─────────────────────────────┼──────────────────────────────┼────────────────+
|               ▼                             ▼                              ▼                |
|   +─────────────────────────────────────────────────────────────────────────────────────+   |
|   |                        FASTAPI SECURE API GATEWAY & ROUTER                          |   |
|   | - TLS Termination & Strict CORS Policy                                              |   |
|   | - Token Bucket Rate Limiting (Anti-DoS / Anti-Scraping)                             |   |
|   +─────────────────────────────────────────┬───────────────────────────────────────────+   |
|                                             │                                               |
|                                             ▼                                               |
|   +─────────────────────────────────────────────────────────────────────────────────────+   |
|   |                             ZERO-TRUST AUTHENTICATOR                                |   |
|   | - JWT Bearer Token Signature Validation (RS256 / HS256)                             |   |
|   | - TOTP MFA Verification (Welfare Officers, Commanders, Admins)                      |   |
|   | - Session Expiration Lifecycle (1h Privileged, 24h Personnel)                       |   |
|   +─────────────────────────────────────────┬───────────────────────────────────────────+   |
|                                             │                                               |
|                                             ▼                                               |
|   +─────────────────────────────────────────────────────────────────────────────────────+   |
|   |                      FIELD-LEVEL & COHORT-LEVEL RBAC ENGINE                         |   |
|   | - Rejects non-self queries for 'Personnel'                                          |   |
|   | - Confines 'WelfareOfficer' queries strictly to assigned Battalion ID               |   |
|   | - Physically strips individual-level query pathways for 'Commander'                |   |
|   | - Disallows 'Admin' access to clinical and personnel records                        |   |
|   +─────────────────────────────────────────┬───────────────────────────────────────────+   |
|                                             │                                               |
+─────────────────────────────────────────────┼───────────────────────────────────────────────+
                                              │ Verified Context
══════════════════════════════════════════════╪═══════════════════════════════════════════════
[TRUST BOUNDARY 2: Core Processing & Behavioral Analytics Engine]
══════════════════════════════════════════════╪═══════════════════════════════════════════════
+─────────────────────────────────────────────┼───────────────────────────────────────────────+
|                                             ▼                                               |
|   +─────────────────────────────────────────────────────────────────────────────────────+   |
|   |                        ACCESS-PATTERN INTRUSION DETECTOR (IDS)                      |   |
|   | - Real-time monitoring of query scope, frequency, and anomaly scoring              |   |
|   | - Detects unauthorized cross-battalion attempts & bulk exfiltration velocity        |   |
|   | - Emits automatic security intercept & alerts Security Admin                        |   |
|   +───────────────────────┬─────────────────────────────────────────┬───────────────────+   |
|                           │ Intercept Passed                        │ Logs All Actions      |
|                           ▼                                         ▼                       |
|   +──────────────────────────────────────────────────+  +───────────────────────────────+   |
|   |       PRIVACY-PRESERVING ANALYTICS CORE          |  |   TAMPER-EVIDENT AUDIT CHAIN  |   |
|   | - k-Anonymity Guard (Suppresses N < 5)           |  | - SHA-256 Hash-Chained Log    |   |
|   | - Differential Privacy Laplace Noise Generator   |  | - Cryptographic Chain Verifier|   |
|   | - Behavioral Stress & Burnout Risk Model         |  | - Immutable Audit Trail       |   |
|   | - Game-Theoretic Alert Prioritization Engine     |  +───────────────────────────────+   |
|   |   (Bounded Welfare Officer Capacity C Optimization)                                     |
|   | - Feature-Attribution Explainability Layer       |                                      |
|   +───────────────────────┬──────────────────────────+                                      |
|                           │                                                                 |
+───────────────────────────┼─────────────────────────────────────────────────────────────────+
                            │ Decoupled CRUD Queries
════════════════════════════╪═════════════════════════════════════════════════════════════════
[TRUST BOUNDARY 3: Cryptographic Storage Vault]
════════════════════════════════════════════╪═════════════════════════════════════════════════
+───────────────────────────┼─────────────────────────────────────────────────────────────────+
|                           ▼                                                                 |
|   +─────────────────────────────────────────────────────────────────────────────────────+   |
|   |                   AES-256-GCM COLUMN ENCRYPTION TYPE DECORATORS                     |   |
|   | - Per-field authenticated encryption with dynamic 96-bit IVs                        |   |
|   | - Key material stored in memory/HSM; zero plaintext written to disk                 |   |
|   +───────────────────────────────────────┬─────────────────────────────────────────────+   |
|                                           │ Ciphertext Only                                 |
|                                           ▼                                                 |
|   +─────────────────────────────────────────────────────────────────────────────────────+   |
|   |                          ISOLATED DATABASE RELATIONS                                |   |
|   |                                                                                     |   |
|   |  [personnel_identity]              [wellness_signals]           [pseudonym_mapping] |   |
|   |  - id                             - id                         - pseudo_id          |   |
|   |  - encrypted_service_no           - pseudo_id (FK)             - personnel_id_hash  |   |
|   |  - encrypted_name                 - encrypted_psych_scores     - rotation_epoch     |   |
|   |  - encrypted_rank                 - encrypted_sleep_metrics    - active_status      |   |
|   |  - battalion_code                 - encrypted_hr_metrics                            |   |
|   |  (NO DIRECT FK TO SIGNALS)        (NO PII ATTRIBUTES)          (RESTRICTED ACCESS)  |   |
|   +─────────────────────────────────────────────────────────────────────────────────────+   |
+─────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 2. Trust Boundaries & Security Enclaves

### Boundary 1: Edge & Ingress Boundary
- **Threat Mitigated**: Unauthenticated probing, API scraping, denial-of-service, session spoofing.
- **Enforcement**: TLS 1.3 encryption in transit, strict HTTP security headers (HSTS, CSP, X-Frame-Options), JSON Web Signature validation, and TOTP verification on all privileged endpoints.

### Boundary 2: Domain Logic & RBAC Enforcement Boundary
- **Threat Mitigated**: Horizontal privilege escalation, commander snooping on individuals, unauthorized cross-cohort inspection.
- **Enforcement**: FastAPI dependency injection enforcing `RoleChecker` and `CohortScopeGuard`. The Commander route controller has **no code references** or execution paths to query individual record tables.

### Boundary 3: Cryptographic Storage Boundary
- **Threat Mitigated**: Physical server theft, database backup compromise, insider DB admin snooping, SQL injection extraction of plaintext.
- **Enforcement**: SQLAlchemy column-level AES-256-GCM encryption. Even a direct `SELECT * FROM wellness_signals` by a root DB admin yields only random cipher bytes and authentication tags.

---

## 3. The Pseudonymization Isolation Principle

The database physically separates identity from wellness data into two decoupled schemas:
1. `personnel_identity`: Contains PII (Service Number, Full Name, Contact Info). Has no wellness columns.
2. `wellness_signals`: Contains psychological scores, sleep quality, and leave deficit metrics. It links **only** to a rotating `pseudo_id` (e.g., `PX-7821`).
3. `pseudonym_mapping`: Maps real personnel hashes to active rotating pseudo IDs.

**The Re-identification Protocol ("Break-Glass"):**
Re-linking an individual from `pseudo_id` back to their service number is physically blocked during routine operations. Re-identification is only permitted for authorized Welfare Officers under an audited **Emergency Welfare Intervention** flow requiring:
- Dual-factor confirmation.
- Documented clinical emergency rationale (e.g., "Active suicidal ideation detected, dispatching crisis counselor").
- Immediate immutable entry written into the tamper-evident hash chain.
- Automatic notification sent to the Security & Audit Officer.
