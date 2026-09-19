# Threat Model: Prismarine Defense Welfare & Stress Monitoring Platform
**Platform:** Prismarine (प्रिज़्मरीन)  
**Document Version:** 2.0.0  
**Classification:** RESTRICTED / DEFENSE SPECIFICATION  
**Framework:** STRIDE + Attack-Tree Analysis  
**Security Posture:** Zero-Trust, Defense-in-Depth, Purpose-Limited Access  

> *"Prismarine — like the mineral: formed under sustained pressure, structurally layered, and defined by clarity rather than opacity."*

---

## 1. Executive Summary & Context

Personnel serving in Central Armed Police Forces (BSF, CRPF, CISF, ITBP, SSB, Assam Rifles) and the Indian Armed Forces operate under high-stress conditions: prolonged remote deployments, counter-insurgency operations, irregular operational shifts, and separation from family support networks. 

While proactive mental health and stress monitoring is an operational imperative, **the primary obstacle to adoption is lack of trust**:
1. **Career Stigmatization**: Personnel fear that reporting distress or low mood will result in withdrawal of weapon, removal from elite operational units, denied promotions, or disciplinary penalization.
2. **Surveillance Anxiety**: Personnel fear commanders will use monitoring tools for intrusive surveillance rather than confidential welfare support.
3. **High-Value Target for Adversaries**: Hostile foreign intelligence services or non-state actors targeting armed forces could exploit aggregated mental distress, psychological vulnerabilities, and deployment fatigue data for psychological warfare, blackmail, or tactical exploitation.

This threat model rigorously analyzes three adversary classes under STRIDE and attack-tree methodologies to guarantee confidentiality, psychological safety, and organizational integrity.

---

## 2. Adversary Classes & Profiles

```
Adversary Hierarchy
├── 1. Insider Threat (Authorized Users Misusing Privileges)
│   ├── 1.1 Commander snooping on individual subordinate mental health or unassigned units (IDOR)
│   ├── 1.2 Welfare Officer abusing break-glass re-identification
│   └── 1.3 Database Administrator attempting raw SQL data tampering
├── 2. External Attacker (Cyber Adversaries & State Actors)
│   ├── 2.1 API abuse & credential theft (MITM, session hijacking)
│   ├── 2.2 SQL injection / Database compromise / Data exfiltration
│   └── 2.3 Differential privacy reconstruction / Query-averaging attacks
└── 3. Gaming Personnel (Strategic & Malicious Reporting)
    ├── 3.1 Under-reporting distress due to career stigma (Stigma-Masked)
    ├── 3.2 Over-reporting distress to secure transfer or leave (Strategic Noise)
    └── 3.3 Acute life-safety crisis situations requiring algorithmic bypass
```

---

## 3. STRIDE Threat Analysis & Defense Architecture

| STRIDE Category | Threat Description | Attacker Profile | Impact | Architectural Mitigation |
| :--- | :--- | :--- | :--- | :--- |
| **Spoofing** | Impersonating a welfare officer or commander to access mental health records | External / Malicious Peer | Critical | Asymmetric JWT tokens, mandatory Step-Up TOTP MFA (RFC 6238) for privileged operations, short-lived sessions |
| **Tampering** | Rogue DBA rewriting historical audit records in database directly | Insider / Rogue DBA | Critical | **HMAC-SHA256 Chained Hash** keyed with secret held in application memory (never in DB) + **External WORM Trust Anchoring** |
| **Repudiation** | An officer performing unauthorized re-identification and denying the action | Insider (Welfare Officer) | High | Step-up TOTP verification, mandatory clinical emergency justification, immutable HMAC audit log entry |
| **Information Disclosure** | Commander discovering individual psych scores or aggregating other units (IDOR) | Commander / External Attacker | Catastrophic | Column-level AES-256-GCM encryption at rest; rotating pseudonyms (`PX-7821`); **Access-Pattern IDS scope checks blocking IDOR**; strict $k$-anonymity ($k \ge 5$) |
| **Denial of Service** | Query-averaging reconstruction attacks against Differential Privacy | External / Curious Commander | Medium | **Cumulative 24h DP Epsilon Budget Accounting**: tracks spent $\epsilon$; increases noise or suppresses queries when daily budget exhausted |
| **Elevation of Privilege** | Standard personnel user elevating to Welfare Officer or Commander | Authenticated Personnel | Critical | Field-level and role-level RBAC enforced directly in domain services and SQL query compilers, not merely UI gating |

---

## 4. Attack Trees

### Attack Tree 1: Insider Threat — Snooping on Subordinate Mental Health & IDOR Probes

```
Goal: Identify Individual Personnel Mental Health / Access Unauthorized Units
├── OR 1: Commander attempts cross-battalion aggregation (IDOR)
│   ├── Path 1.1: Call /api/v1/commander/cohort-readiness?target_battalion=42-BSF
│   └── MITIGATION: Access-Pattern IDS inspects requested battalion against user's assigned battalion. Blocks request with HTTP 403 (COMMANDER_IDOR_VIOLATION).
├── OR 2: Commander attempts direct API query for individual member
│   ├── Path 2.1: Call /api/v1/personnel/{id}/wellness
│   └── MITIGATION: RBAC middleware checks role. If 'commander', request is blocked with HTTP 403.
├── OR 3: Welfare Officer abuses Break-Glass Re-identification
│   ├── Path 3.1: Request re-identification without emergency justification or TOTP
│   └── MITIGATION: Endpoint enforces step-up TOTP MFA verification and mandatory documented clinical rationale; immediately etched into HMAC audit chain.
└── OR 4: Rogue Database Administrator inspects or alters raw DB tables
    ├── Path 4.1: Read 'personnel_identity' table
    │   └── MITIGATION: Columns (Name, Service No, Station) are encrypted with AES-256-GCM. Decryption keys are managed in ephemeral application memory, never stored in DB plaintext.
    └── Path 4.2: Modify historical audit log entries to conceal fraud
        └── MITIGATION: Cryptographic HMAC-SHA256. Without the external HMAC key (kept outside DB in app memory), the altered block fails verification and is caught by external trust anchor sync.
```

---

## 5. Security & Trust Principles in Prismarine

1. **Defense-in-Depth**: Security is enforced across client, network, gateway, service domain, and data storage layers.
2. **Separation of Duties**: Admin has infrastructure power but zero data visibility; Commander has aggregate operational insight but zero individual visibility; Welfare Officer has individual wellness insight under strict pseudonymization; Personnel have sovereign personal visibility.
3. **Crisis Non-Negotiable**: Acute self-harm signals hard-override algorithmic queues immediately for urgent life safety.
4. **Tamper-Evident Accountability**: Every query into sensitive records is permanently signed and etched into an immutable HMAC-SHA256 hash chain with external WORM trust anchoring.
