# PRISMARINE: AI Personnel Stress & Welfare Monitoring Platform
### Zero-Trust, Defense-Grade Behavioral Analytics & Mental Resilience Platform
**Tailored for:** Central Armed Police Forces (CRPF, BSF, CISF, ITBP, SSB) & Indian Armed Forces  
**Classification:** RESTRICTED / DEFENSE SPECIFICATION  

> *"Prismarine — like the mineral: formed under sustained pressure, structurally layered, and defined by clarity rather than opacity. That's the design philosophy behind this platform — a system built under the same kind of sustained operational pressure it's meant to monitor, with security enforced in transparent, auditable layers (encryption → RBAC → IDS → hash-chained audit) rather than a black box."*

---

## 🛡️ Executive Overview

Personnel serving in uniformed defense and paramilitary forces operate under severe operational and physical stressors—hazardous high-altitude postings, counter-insurgency rotations, prolonged family separation, and irregular night sentry duties. 

Current stress identification depends on delayed manual observation or voluntary reporting, which is severely hindered by **career stigma anxiety** (fear of service weapon withdrawal, reassignment from operational units, or stalled promotion).

**PRISMARINE** resolves this challenge with a defense-grade, zero-trust architecture built on four transparent pillars:
1. **Cryptographic Core & Decoupled Storage**: Column-level **AES-256-GCM** authenticated encryption at rest; PII is physically decoupled from clinical telemetry and bound only to rotating pseudonyms (`pseudo_id`, e.g., `PX-7821`). Zero fallback secrets in code.
2. **Privacy-Preserving Analytics & Budget Accounting**: Strict $k$-Anonymity ($k \ge 5$) suppression on cohort queries and Differential Privacy Laplace noise injection with rolling 24h cumulative $\epsilon$-budget tracking.
3. **Game-Theoretic Alert Prioritization & Crisis Override**: Models Welfare Officer attention as a bounded resource ($C=15$ cases/week), detects **Stigma-Masked Under-Reporting** (Naik Sunil Yadav), discounts uncorroborated noise (Havildar Vikram Singh), and enforces an immediate **Life-Safety Crisis Override** bypassing all queues for self-harm signals.
4. **Stateful Case Management**: Full intervention lifecycle tracking (`OPEN` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `RESOLVED`). Resolved cases cleanly exit the active queue.
5. **Access-Pattern IDS & IDOR Defense**: Real-time anomaly detection intercepting cross-battalion snooping for both welfare officers and commanders.
6. **HMAC-SHA256 Audit Trail & External Trust Anchoring**: Keyed with an external secret never stored in the database, preventing rogue DBA forgery, and anchored periodically to an external WORM trust ledger.
7. **Installable Personnel PWA**: Lightweight, offline-capable mobile check-in interface with step-up TOTP MFA on privileged operations.

---

## 🏛️ System Architecture

```
[Personnel PWA]    [Welfare Officer Console]    [Commander Strategic View]    [Security Admin IDS]
      │                       │                             │                          │
      └───────────────────────┼─────────────────────────────┼──────────────────────────┘
                              ▼ HTTPS (TLS 1.3 / Explicit CORS)
               +───────────────────────────────────────────────────+
               |        FastAPI Gateway & Step-Up TOTP MFA         |
               |        (JWT + RFC 6238 TOTP Header Guard)         |
               +─────────────────────────┬─────────────────────────+
                                         │
               +─────────────────────────▼─────────────────────────+
               |       Field-Level RBAC & Access-Pattern IDS       |
               | (Prevents IDOR Probes & Cross-Unit Aggregations)  |
               +───────────┬───────────────────────────┬───────────+
                           │                           │
          Commander Query  │                           │ Welfare Officer Query
          (Aggregate Only) ▼                           ▼ (Pseudonymized Cohort)
               +────────────────────────+  +───────────────────────────────────+
               |  k-Anonymity Guard     |  | Game-Theoretic Alert Prioritizer  |
               |     (k >= 5 Guard)     |  |   (Bounded Officer Capacity C)    |
               |           +            |  |                 +                 |
               | DP Epsilon Accounting  |  |   Life-Safety Crisis Override     |
               | (Rolling 24h Tracker)  |  |                 +                 |
               |                        |  | Stateful Case Lifecycle (AlertCase|
               +───────────┬────────────+  +─────────────────┬─────────────────+
                           │                                 │
                           └────────────────┬────────────────┘
                                            │
               +────────────────────────────▼────────────────────────────+
               |             AES-256-GCM Cryptographic Vault             |
               |                                                         |
               | [personnel_identity]     (PII Vault, Zero Decryption FK)|
               | [wellness_signals]       (Encrypted Telemetry)          |
               | [pseudonym_mapping]      (Rotating Epoch Pseudonyms)    |
               | [welfare_alert_cases]    (Stateful Intervention Status) |
               | [tamper_evident_audit]   (HMAC-SHA256 Chain + WORM)     |
               +─────────────────────────────────────────────────────────+
```

---

## 🚀 Quickstart & Setup

### 1. Requirements
- Python 3.10+ (Tested on Python 3.12 / 3.14)
- `uv` (recommended) or standard `pip`

### 2. Configuration & Secrets Setup
Prismarine enforces a strict zero-fallback security posture. Secrets must be supplied via environment or `.env` file:
```bash
# Clone or navigate to directory
cd /home/pranjal/SIH/prsnl_SIH

# Copy environment template
cp .env.example .env

# Generate random 256-bit keys and populate .env:
# python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Installation
```bash
# Create virtual environment
uv venv .venv
source .venv/bin/activate

# Install exact pinned dependencies
uv pip install -r requirements.txt
```

### 4. Run Automated Verification Tests
```bash
pytest -v
```
*All 19 security, encryption, RBAC, k-anonymity, DP budget, game-theory, crisis override, IDOR defense, and HMAC audit tests will execute and pass.*

### 5. Launch the Application Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser at **`http://localhost:8000`** to access the unified operational interface.

---

## 🎭 Pre-Scripted Demo Personas (One-Click Switching)

| Persona | Role | Credentials | Narrative Arc |
| :--- | :--- | :--- | :--- |
| **Constable Rajesh Kumar** | Personnel | `rajesh_kumar` / `password123` | **Genuine High-Risk**: 210 days forward deployment, 2 denied leaves, severe insomnia. Prioritized Top #1 in Welfare Queue. |
| **Havildar Vikram Singh** | Personnel | `PX-4409` (Synthetic) | **Noisy / Low Corroboration**: High self-report complaint spike but 0 days leave deficit. De-prioritized by game-theoretic engine to prevent alert fatigue. |
| **Naik Sunil Yadav** | Personnel | `PX-1290` (Synthetic) | **Stigma-Masked Under-Reporting**: 195 days deployment, 3 denied leaves, but reports 0 distress out of weapon withdrawal fear. Engine detects mask and boosts priority. |
| **Sub-Inspector Anita Sharma** | Welfare Officer | `welfare_sharma` / `password123` / OTP: `123456` | **Authorized Welfare Staff**: Reviews prioritized alert queue, inspects factor attributions, manages case lifecycle, executes emergency Break-Glass protocol. |
| **Commandant V. Singh** | Commander | `cmd_singh` / `password123` / OTP: `123456` | **Battalion Commander**: Strategic view strictly $k$-anonymized ($k \ge 5$). Code physically blocks individual queries and cross-battalion IDOR attempts. |
| **Security & Audit Admin** | Admin | `sec_admin` / `password123` / OTP: `123456` | **Security Officer**: Verifies HMAC-SHA256 hash chain and external WORM anchor. ZERO access to personnel medical telemetry. |
| **Rogue Officer Simulation** | Rogue Insider | `welfare_rogue` / `password123` / OTP: `123456` | **Insider Threat**: Assigned to 42-BSF, attempts unauthorized snoop into 104-CRPF. Caught instantly by Access-Pattern IDS. |

---

## ⚡ Live Hackathon Demo Sequences

### Demo 1: Bounded Attention & Game-Theoretic Prioritization
1. Switch to **Welfare Officer Console** (`104-CRPF`).
2. Observe the queue: **`PX-7821` (Rajesh Kumar)** is ranked #1 with **+3.21 Expected Utility**.
3. Observe **`PX-1290` (Sunil Yadav)**: Tagged as `STIGMA-MASKED (UNDER-REPORTING)`. Despite claiming 0 distress, the engine factored his 195 deployment days and 3 denied leaves to boost his priority!
4. Observe **`PX-4409` (Vikram Singh)**: Tagged as `LOW CORROBORATION (NOISE)`. High complaint without operational stress is down-weighted to conserve welfare officer capacity ($C=15$).
5. Click **Explain** on `PX-7821` to show factor attributions and non-punitive intervention recommendations.
6. Click **Resolve** to demonstrate stateful case management (`RESOLVED`), reducing active caseload.

### Demo 2: The Emergency Break-Glass Unmasking
1. In the Welfare Console, click **Unmask** on `PX-7821`.
2. Enter crisis justification and step-up TOTP verification.
3. The system unmasks Constable Rajesh Kumar (Service #CRPF-104-7821) and outputs an **immutable audit sequence number**.

### Demo 3: Live IDOR Defense & Mathematical $k$-Anonymity
1. Switch to **Commander Strategic View** (`104-CRPF`).
2. Click **`42-BSF (Triggers IDOR Block)`**:
   - The Access-Pattern IDS catches the unauthorized cross-battalion attempt in real time and raises an alert block.
3. Click **`88-ITBP (N=3)`**:
   - The backend triggers the $k$-anonymity guard ($k \ge 5$).
   - The screen suppresses all metrics and warns that small cohorts are withheld to prevent re-identification through elimination.

### Demo 4: Live Database Tampering & External Trust Anchoring
1. Switch to **Security Operations & IDS**.
2. Click **`⚡ Simulate Log Tampering`**:
   - Simulates a rogue DBA mutating historical SQL rows directly.
   - Click **Verify Hash Chain**: The system verifies against the external HMAC key and external trust anchor, immediately exposing the altered block!
3. Click **`🔄 Restore Chain`** to return the chain to a verified state.

---

## 🔍 Known Limitations, By Design (Preempting the Jury)

1. **Differential Privacy Budget Exhaustion: Graceful Degradation vs. Hard Stop**:
   - *Design Choice*: Rolling 24-hour window ($\epsilon_{\text{daily}} = 5.0$) with **Graceful Privacy Degradation**.
   - *Operational Rationale*: In high-tempo defense operations, completely blinding a battalion commander by hard-blocking readiness queries (`HTTP 429`) during an active mission or crisis introduces severe operational risk.
   - *Mechanics*: When the daily budget is spent, the system does not refuse the query; instead, it automatically halves $\epsilon$ (doubling the Laplace noise variance) and flags `"dp_budget_status": "BUDGET_EXHAUSTED_EXTRA_NOISE"`. This actively destroys mathematical reconstruction fidelity while preserving directional macro-trends for command awareness. For installations requiring a zero-tolerance hard cutoff, configuring `DP_STRICT_ENFORCEMENT=true` immediately switches to query rejection.

2. **External Trust Anchoring: Host Write Boundary**:
   - *Design Choice*: Append-only JSON Lines ledger (`external_trust_anchor.jsonl`).
   - *Security Boundary*: The anchor only provides true defense-grade tamper resistance once written to a system the application host itself cannot unilaterally modify or overwrite. A local file on the same filesystem can be rewritten by any attacker possessing root host access.
   - *Demo Implementation*: Prismarine enforces strict append-only writes (never overwrites historical anchor records). Any attempt to forge or recalculate a tampered chain head creates an anchor history discrepancy detectable by diffing historical snapshots.
   - *Production Architecture*: The append stream forwards directly to an immutable external target outside the host trust perimeter: an air-gapped defense syslog server, a hardware security module (HSM), AWS CloudTrail, or an S3 Object Lock bucket in Compliance Mode with separate write-only IAM roles.

3. **IDS State Architecture**:
   - *Design Boundary*: Single-process in-memory sliding window cache for standalone deployment and demo simplicity.
   - *Production Path*: Horizontally scales to Redis / Valkey clusters in multi-node deployments with identical anomaly scoring and IP/cohort velocity tracking algorithms.
