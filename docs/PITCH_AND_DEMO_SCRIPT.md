# PRISMARINE: Hackathon Pitch & Live Demo Runbook
**Platform Name:** Prismarine (प्रिज़्मरीन)  
**Narrative Arc:** *"Formed under sustained pressure, structurally layered, and defined by clarity rather than opacity."*  
**Duration:** 5 - 7 Minutes  
**Target Audience:** Smart India Hackathon (SIH) Technical Jury & Defense/CAPF Leadership  

---

## 1. The Opening Hook (1 Minute)

> **"Respected Judges, our platform is named PRISMARINE — like the mineral: formed under sustained pressure, structurally layered, and defined by clarity rather than opacity.**
>
> **Personnel serving in the CRPF, BSF, ITBP, and Armed Forces operate under relentless operational pressure: remote postings, prolonged family separation, and irregular night sentry duties. Yet commercial HR wellness tools fail in the armed forces. Why? Because of FEAR: Fear that reporting fatigue will get a soldier's service weapon withdrawn, stall promotions, or expose them to commander surveillance.**
>
> **Prismarine is engineered from the ground up under that exact same philosophy: built like a defense system, not an HR tool. Security and privacy are enforced in transparent, auditable layers — column-level AES-256-GCM encryption, field-level RBAC, game-theoretic alert prioritization with crisis overrides, real-time access-pattern IDS, and an HMAC-SHA256 tamper-evident audit trail backed by external trust anchoring."**

---

## 2. Key Architectural Layers (Walkthrough)

### Layer 1: Threat Model on Paper (`docs/THREAT_MODEL.md`)
- STRIDE analysis and 3 attack trees:
  - **Insider Threats**: Commanders attempting to snoop on individual subordinate mental health.
  - **External Attackers**: Bulk exfiltration of troop psychological vulnerabilities.
  - **Gaming Personnel**: Stigma-driven under-reporting vs noisy over-reporting.
- **Defense Trust Separation**: The System Administrator has infrastructure maintenance rights but **zero access to medical/clinical telemetry by default**.

### Layer 2: Encrypted Core Backend & Decoupled Storage
- **Column-Level AES-256-GCM Encryption**: Unique 96-bit nonce and 128-bit authentication tag per field.
- **Physical Decoupling**: Identity (`personnel_identity`) is completely separated from wellness telemetry (`wellness_signals`). Decoupled records are linked only to rotating pseudonyms (`pseudo_id`, e.g., `PX-7821`).
- **Zero Fallback Secrets**: Secret keys are strictly loaded from environment with zero hardcoded defaults.

### Layer 3: Privacy-Preserving Analytics & Game-Theoretic Prioritization
- **Bounded Attention Optimization**: Welfare officer time is modeled as a bounded resource ($C=15$ cases/week).
- **Stigma-Masked Distress Detection**: Detects personnel with severe operational stressors (195+ days deployed, 3 denied leaves) who claim 0 distress out of weapon withdrawal fear, and boosts their priority!
- **Noise Suppression**: Discounts uncorroborated complaint spikes to prevent officer fatigue.
- **Life-Safety Crisis Override**: Explicit self-harm or acute crisis signals hard-override the algorithm to Rank #1 immediately. *"We never let an algorithm delay a life-safety response."*
- **Stateful Case Management**: Tracks lifecycle (`OPEN` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `RESOLVED`). Resolved cases exit the active queue.
- **$k$-Anonymity Guard ($k \ge 5$) & Cumulative DP Accounting**: Cohorts $< 5$ members are suppressed. Tracks rolling 24h $\epsilon$-budget.

### Layer 4: Access-Pattern IDS & HMAC-SHA256 Audit Trail
- **Access-Pattern Intrusion Detection System**: Detects cross-battalion queries (both welfare and commander IDOR attempts) in real time.
- **HMAC-SHA256 Hash Chain**: Keyed with an external secret held in application memory (never in DB). Even a rogue DBA with raw SQL write access cannot forge valid signatures.
- **External Trust Anchoring**: Commits chain heads to an external WORM anchor registry.
- **Step-Up TOTP MFA**: Mandated on break-glass unmasking and administrative auditing.

---

## 3. Step-by-Step Live Demo Runbook

| Step | Action on UI | Talking Point for Judges |
| :--- | :--- | :--- |
| **Step 1** | Open `http://localhost:8000` | "This is Prismarine's unified operational console, starting with our responsive Soldier PWA." |
| **Step 2** | Submit check-in for `PX-7821` | "Constable Rajesh Kumar logs his daily rest and fatigue. Notice the real-time AES-256-GCM packing—his real name never touches the wellness table." |
| **Step 3** | Switch to **Welfare Officer Console** | "Sub-Inspector Anita Sharma reviews Battalion 104-CRPF. Notice the queue: Rajesh Kumar is prioritized at Rank #1 (+3.21 Utility) due to 210 days forward deployment and 2 denied leaves." |
| **Step 4** | Point to `PX-1290` (Sunil Yadav) | "Notice Sunil Yadav: tagged as **STIGMA-MASKED**. He claimed 0 distress, but our game-theoretic engine detected his 195 deployment days and 3 denied leaves, boosting his priority!" |
| **Step 5** | Click **Explain** on `PX-7821` | "Transparent AI: 42% Leave Deficit, 28% Sleep Deprivation. Directs a 14-day R&R leave and night sentry rotation." |
| **Step 6** | Click **Unmask (Break-Glass)** | "In emergency life safety, the officer supplies clinical justification and step-up TOTP. Unmasks Constable Rajesh Kumar and logs to the HMAC audit chain." |
| **Step 7** | Click **Resolve** on `PX-7821` | "Stateful case management: Case marked RESOLVED. Capacity counter updates from 10 to 9 cases handled." |
| **Step 8** | Switch to **Commander Strategic View** | "The Commandant's screen: strictly aggregated $k \ge 5$ metrics. No soldier names or pseudonyms exist here." |
| **Step 9** | Click **42-BSF (Triggers IDOR Block)** | "Live IDOR defense: A commander tries to aggregate another battalion's data. The Access-Pattern IDS intercepts and blocks it in real time!" |
| **Step 10** | Click **88-ITBP (N=3)** | "Small unit query: **Data Suppressed!** The $k$-anonymity guard ($k \ge 5$) blocks the query to prevent re-identification through elimination." |
| **Step 11** | Switch to **Security Operations & IDS** | "Our security command center: HMAC-SHA256 audit chain with external WORM trust anchoring." |
| **Step 12** | Click **⚡ Simulate Log Tampering** | "An adversary edits historical rows in SQLite/Postgres. We run verification: HMAC validation immediately fails and pinpoints the exact tampered sequence!" |
| **Step 13** | Click **🔄 Restore Chain** | "We restore integrity, verifying all blocks remain mathematically sound." |

---

## 4. "Known Limitations, By Design" (Preempting the Jury)

When judges probe technical edge cases, proactively present this slide:

1. **Differential Privacy Budget Window**:
   - *Design Boundary*: Rolling 24-hour window ($\epsilon = 5.0$).
   - *Rationale*: A static infinite budget eventually runs out; a rolling window balances longitudinal commander readiness insights against differential reconstruction attacks.
2. **IDS State Architecture**:
   - *Design Boundary*: Single-process in-memory sliding window cache for demo simplicity.
   - *Production Path*: Horizontally scales to Redis clusters in multi-node deployments with identical anomaly scoring algorithms.
3. **External Trust Anchoring**:
   - *Design Boundary*: Local JSON external WORM anchor registry.
   - *Production Path*: Easily configured to write to AWS CloudTrail, an immutable S3 Object Lock bucket, or an air-gapped defense syslog.
