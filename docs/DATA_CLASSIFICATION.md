# Data Classification & Protection Specification
**Document Version:** 1.0.0  
**Classification:** RESTRICTED / DEFENSE SPECIFICATION  

This document defines the strict 4-tier data classification model for the CAPF & Armed Forces Personnel Stress and Welfare Monitoring System, establishing cryptographic guarantees and storage boundaries for every data element.

---

## 1. Classification Tiers Overview

```
Security Sensitivity Spectrum
┌────────────────────────────────────────────────────────────────────────┐
│ Level 4: Raw-Sensitive (Psychometric, Clinical & Suicidal Ideation)    │
│ Level 3: Pseudonymizable Operational (HR Telemetry & Leave History)    │
│ Level 2: Anonymized Aggregates (Cohort Statistics, k-Anonymity >= 5)   │
│ Level 1: Public / System Operational (Root Hash, Health Metrics)       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Field-Level Classification & Cryptographic Safeguards

| Data Field | Category | Classification Level | Storage Mechanism | Encryption Scheme | Access Boundary | De-Identification Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Service Number / UID** | PII / Identity | **Level 4** (Raw-Sensitive) | `personnel_identity` | AES-256-GCM (Unique Salt/IV per row) | Personnel (self), Admin (masked) | Decoupled via `pseudo_id` |
| **Full Name & Rank** | PII / Identity | **Level 4** (Raw-Sensitive) | `personnel_identity` | AES-256-GCM | Personnel (self) | Masked (`Cst. R*** K***`) |
| **Battalion / Company / Unit** | Operational | **Level 3** (Pseudonymizable) | `personnel_identity` | AES-256-GCM | Welfare Officer (assigned cohort only), Commander | Unit-level scope partition |
| **Phone & Emergency Contact** | PII / Identity | **Level 4** (Raw-Sensitive) | `personnel_identity` | AES-256-GCM | Personnel (self) | Strictly isolated |
| **PHQ-4 / PHQ-9 Mental Health Scores** | Clinical / Psych | **Level 4** (Raw-Sensitive) | `wellness_signals` | AES-256-GCM | Welfare Officer (pseudonymized), Personnel (self) | Bound solely to rotating `pseudo_id` |
| **Self-Reported Mood / Stress Rating** | Clinical / Psych | **Level 4** (Raw-Sensitive) | `wellness_signals` | AES-256-GCM | Welfare Officer (pseudonymized), Personnel (self) | Linked to rotating `pseudo_id` |
| **Sleep Quality & Hours** | Biometric / Lifestyle | **Level 4** (Raw-Sensitive) | `wellness_signals` | AES-256-GCM | Welfare Officer (pseudonymized), Personnel (self) | Linked to rotating `pseudo_id` |
| **Freeform Reflection Sentiment** | Psych Telemetry | **Level 4** (Raw-Sensitive) | `wellness_signals` | AES-256-GCM | Welfare Officer (pseudonymized), Personnel (self) | NLP sentiment extracted; raw text encrypted |
| **Days Since Last Leave** | HR / Operational | **Level 3** (Pseudonymizable) | `wellness_signals` | AES-256-GCM | Welfare Officer (pseudonymized) | Linked to rotating `pseudo_id` |
| **Leave Applications Denied Count** | HR / Operational | **Level 3** (Pseudonymizable) | `wellness_signals` | AES-256-GCM | Welfare Officer (pseudonymized) | Linked to rotating `pseudo_id` |
| **Deployment Hardship Score** | Operational | **Level 3** (Pseudonymizable) | `wellness_signals` | AES-256-GCM | Welfare Officer (pseudonymized) | Linked to rotating `pseudo_id` |
| **Night Duty Shift Ratio** | Operational | **Level 3** (Pseudonymizable) | `wellness_signals` | AES-256-GCM | Welfare Officer (pseudonymized) | Linked to rotating `pseudo_id` |
| **Cohort Average Stress Index** | Strategic Metric | **Level 2** (Safe Aggregate) | In-memory / Analytics | Plaintext / TLS in transit | Commander, Welfare Officer | Suppressed if $k < 5$; Laplace noise added |
| **Unit Leave Utilization Rate %** | Strategic Metric | **Level 2** (Safe Aggregate) | In-memory / Analytics | Plaintext / TLS in transit | Commander | Cohort level ($k \ge 5$) |
| **High/Medium Risk Personnel Count** | Strategic Metric | **Level 2** (Safe Aggregate) | In-memory / Analytics | Plaintext / TLS in transit | Commander | Count suppressed if $1 \le count < 5$ |
| **Audit Log Hash Chain** | Security Integrity | **Level 1** (Public / Auditable) | `tamper_evident_audit_log` | SHA-256 Chained Hash | Security Admin, Welfare Officer, Auditor | Cryptographic signature & hash |

---

## 3. Cryptographic Storage Guarantees

1. **Zero Plaintext at Rest**:
   Even if the underlying database (PostgreSQL/SQLite) disk volume is dumped or physically exfiltrated, no psychological assessment or personnel service number can be extracted without the master hardware security module / application encryption key.
2. **Rotating Pseudonymization Epochs**:
   The linkage table `pseudonym_mapping` maps `personnel_id` to `pseudo_id` using an epoch-based cryptographic token. This prevents longitudinal correlation attacks where an insider attempts to deduce identities by watching steady changes in a specific pseudonym over many months.
3. **Strict $k$-Anonymity Guarantees**:
   For any analytical or commander query over cohorts, if the cohort slice matches fewer than $k=5$ individuals, the backend mathematically suppresses the query and returns a standardized anonymity-preservation response:
   $$\text{Result} = \begin{cases} \text{Aggregate}(S), & \text{if } |S| \ge 5 \\ \text{SUPPRESSED\_ANONYMITY\_THRESHOLD}, & \text{if } |S| < 5 \end{cases}$$
