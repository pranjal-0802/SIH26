// PRISMARINE Client Application Logic
// "Formed under sustained pressure, structurally layered, and defined by clarity rather than opacity."

const API_BASE = '/api/v1';

// Pre-seeded credentials for seamless hackathon demonstration
const PERSONAS = {
  personnel: {
    username: 'rajesh_kumar',
    password: 'password123',
    role: 'personnel',
    displayName: 'Constable Rajesh Kumar (PX-7821)',
    unit: '104-CRPF (Kupwara Forward Post)'
  },
  welfare: {
    username: 'welfare_sharma',
    password: 'password123',
    totp_code: '123456',
    role: 'welfare_officer',
    displayName: 'Sub-Inspector Anita Sharma (Welfare Officer)',
    unit: '104-CRPF'
  },
  commander: {
    username: 'cmd_singh',
    password: 'password123',
    totp_code: '123456',
    role: 'commander',
    displayName: 'Commandant Vikramaditya Singh',
    unit: '104-CRPF'
  },
  admin: {
    username: 'sec_admin',
    password: 'password123',
    totp_code: '123456',
    role: 'admin',
    displayName: 'Security Operations & Audit Officer',
    unit: 'Central Command'
  }
};

let currentRole = 'personnel';
let authTokens = {};
let cachedAlerts = [];

document.addEventListener('DOMContentLoaded', async () => {
  setupSliders();
  await preAuthenticateAllRoles();
  switchRole('personnel');
  
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js').catch(() => {});
  }
});

function setupSliders() {
  const sliders = [
    { id: 'p_mood', labelId: 'val_mood' },
    { id: 'p_stress', labelId: 'val_stress' }
  ];
  sliders.forEach(s => {
    const el = document.getElementById(s.id);
    const lbl = document.getElementById(s.labelId);
    if (el && lbl) {
      el.addEventListener('input', () => {
        lbl.textContent = el.value;
      });
    }
  });
}

async function preAuthenticateAllRoles() {
  for (const [key, p] of Object.entries(PERSONAS)) {
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: p.username,
          password: p.password,
          totp_code: p.totp_code || '123456'
        })
      });
      if (res.ok) {
        const data = await res.json();
        authTokens[key] = data.access_token;
      }
    } catch (e) {
      console.warn('Auth pre-fetch failed for', key, e);
    }
  }
}

function getAuthHeader(roleKey) {
  const headers = {
    'Authorization': `Bearer ${authTokens[roleKey] || ''}`,
    'Content-Type': 'application/json'
  };
  // Supply step-up TOTP header for privileged operations
  if (roleKey === 'welfare' || roleKey === 'commander' || roleKey === 'admin') {
    headers['X-TOTP-Code'] = '123456';
  }
  return headers;
}

window.switchRole = async function(roleKey) {
  currentRole = roleKey;
  
  document.querySelectorAll('.role-tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.role === roleKey);
  });
  
  document.querySelectorAll('.view-section').forEach(view => {
    view.classList.toggle('active', view.id === `view-${roleKey}`);
  });

  if (roleKey === 'personnel') {
    loadPersonnelHistory();
  } else if (roleKey === 'welfare') {
    loadWelfareAlerts();
  } else if (roleKey === 'commander') {
    loadCommanderData('104-CRPF');
  } else if (roleKey === 'admin') {
    loadAuditChain();
    loadIdsAlerts();
  }
};

// ----------------------------------------------------
// 1. PERSONNEL SELF-ASSESSMENT PWA
// ----------------------------------------------------
window.submitCheckIn = async function(e) {
  e.preventDefault();
  const mood = parseFloat(document.getElementById('p_mood').value);
  const sleep = parseFloat(document.getElementById('p_sleep').value);
  const stress = parseFloat(document.getElementById('p_stress').value);
  const phq4 = parseFloat(document.getElementById('p_phq4').value);
  const reflection = document.getElementById('p_reflection').value;

  const statusEl = document.getElementById('checkin-encryption-status');
  statusEl.style.display = 'block';
  statusEl.innerHTML = `
    <div style="color: var(--accent-cyan); font-size: 0.8rem; margin-bottom: 0.5rem;">
      <span class="badge badge-cyan">AES-256-GCM Packing</span> Generating 96-bit nonce & IV...
    </div>
  `;

  try {
    const res = await fetch(`${API_BASE}/personnel/check-in`, {
      method: 'POST',
      headers: getAuthHeader('personnel'),
      body: JSON.stringify({
        mood_score: mood,
        sleep_hours: sleep,
        stress_rating: stress,
        phq4_score: phq4,
        reflection_text: reflection
      })
    });

    const data = await res.json();
    if (res.ok) {
      if (data.is_crisis_override) {
        statusEl.innerHTML = `
          <div style="color: #fca5a5; font-size: 0.85rem; background: rgba(239, 68, 68, 0.15); padding: 0.5rem; border-radius: 4px; border: 1px solid var(--accent-crimson);">
            🚨 <strong>CRISIS LIFE-SAFETY OVERRIDE ACTIVATED:</strong> Algorithmic queue bypassed. Immediate confidential support dispatched.
          </div>
        `;
        showToast('CRISIS OVERRIDE: Priority assistance alert dispatched.');
      } else {
        statusEl.innerHTML = `
          <div style="color: var(--accent-green); font-size: 0.8rem;">
            ✓ Check-in encrypted and recorded under pseudonym <strong>${data.pseudo_id}</strong>.
            Real identity decoupled. Signed with HMAC-SHA256.
          </div>
        `;
        showToast('Assessment encrypted & submitted.');
      }
      loadPersonnelHistory();
    } else {
      statusEl.innerHTML = `<span style="color: var(--accent-crimson)">Error: ${data.detail || 'Submission failed'}</span>`;
    }
  } catch (err) {
    statusEl.innerHTML = `<span style="color: var(--accent-crimson)">Network error during submission</span>`;
  }
};

async function loadPersonnelHistory() {
  try {
    const res = await fetch(`${API_BASE}/personnel/my-wellness-history`, {
      headers: getAuthHeader('personnel')
    });
    if (res.ok) {
      const data = await res.json();
      const tbody = document.getElementById('personnel-history-table-body');
      tbody.innerHTML = '';
      (data.history || []).forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${new Date(r.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
          <td><span class="badge ${r.mood_score >= 6 ? 'badge-green' : 'badge-amber'}">${r.mood_score}/10</span></td>
          <td>${r.sleep_hours} hrs</td>
          <td><span class="badge ${r.stress_rating > 6 ? 'badge-crimson' : 'badge-cyan'}">${r.stress_rating}/10</span></td>
          <td>${r.phq4_score}/12</td>
          <td>${r.is_crisis ? '<span class="badge badge-crimson">CRISIS FLAG</span>' : '<span class="badge badge-green">AES-256</span>'}</td>
        `;
        tbody.appendChild(tr);
      });
    }
  } catch (e) {}
}

// ----------------------------------------------------
// 2. WELFARE OFFICER CONSOLE
// ----------------------------------------------------
async function loadWelfareAlerts() {
  const container = document.getElementById('welfare-alerts-body');
  container.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">Evaluating game-theoretic alert ranking & case statuses...</td></tr>';

  try {
    const res = await fetch(`${API_BASE}/welfare/alerts?target_battalion=104-CRPF`, {
      headers: getAuthHeader('welfare')
    });
    if (res.ok) {
      const data = await res.json();
      cachedAlerts = data.allocated_alerts || [];
      
      document.getElementById('welfare-capacity-text').textContent = 
        `${data.allocated_count} / ${data.officer_capacity_c} Slots Allocated (${data.capacity_utilization_pct}% Capacity) | ${data.resolved_count || 0} Cases Handled`;
      
      container.innerHTML = '';
      cachedAlerts.forEach((alert) => {
        const tr = document.createElement('tr');
        
        let archetypeBadge = 'badge-cyan';
        let archetypeLabel = alert.signal_archetype;
        if (alert.signal_archetype === 'CRISIS_IMMEDIATE_OVERRIDE') {
          archetypeBadge = 'badge-crimson';
          archetypeLabel = '🚨 CRISIS OVERRIDE';
        } else if (alert.signal_archetype === 'AUTHENTIC_HIGH_DISTRESS') {
          archetypeBadge = 'badge-crimson';
          archetypeLabel = 'AUTHENTIC DISTRESS';
        } else if (alert.signal_archetype === 'STIGMA_MASKED_DISTRESS') {
          archetypeBadge = 'badge-amber';
          archetypeLabel = 'STIGMA-MASKED (UNDER-REPORTING)';
        } else if (alert.signal_archetype === 'NOISY_UNSUBSTANTIATED') {
          archetypeBadge = 'badge-purple';
          archetypeLabel = 'LOW CORROBORATION (NOISE)';
        }

        const caseStatus = alert.case_status || 'OPEN';
        let statusBadge = 'badge-amber';
        if (caseStatus === 'IN_PROGRESS') statusBadge = 'badge-cyan';
        if (caseStatus === 'RESOLVED') statusBadge = 'badge-green';

        tr.innerHTML = `
          <td><strong>#${alert.priority_rank}</strong></td>
          <td><span class="badge badge-cyan" style="font-family: monospace;">${alert.pseudo_id}</span></td>
          <td><span class="badge ${archetypeBadge}">${archetypeLabel}</span></td>
          <td><strong>${(alert.p_true_distress * 100).toFixed(0)}%</strong></td>
          <td><span style="color: ${alert.expected_utility > 1.5 ? 'var(--accent-green)' : 'var(--accent-amber)'}; font-weight: 700;">+${alert.expected_utility}</span></td>
          <td><span class="badge ${statusBadge}">${caseStatus}</span></td>
          <td><span class="badge ${alert.action_urgency === 'IMMEDIATE_ACTION' || alert.is_crisis ? 'badge-crimson' : 'badge-amber'}">${alert.action_urgency}</span></td>
          <td>
            <button class="btn-primary" style="padding: 0.2rem 0.4rem; font-size: 0.7rem;" onclick="openExplainModal('${alert.pseudo_id}')">Explain</button>
            <button class="btn-danger" style="padding: 0.2rem 0.4rem; font-size: 0.7rem;" onclick="openBreakGlassModal('${alert.pseudo_id}')">Unmask</button>
            <button class="btn-primary" style="padding: 0.2rem 0.4rem; font-size: 0.7rem; background: var(--accent-green);" onclick="resolveCase('${alert.case_id}')">Resolve</button>
          </td>
        `;
        container.appendChild(tr);
      });
    }
  } catch (err) {
    container.innerHTML = '<tr><td colspan="8" style="color: var(--accent-crimson);">Failed to load welfare alerts</td></tr>';
  }
}

window.resolveCase = async function(caseId) {
  try {
    const res = await fetch(`${API_BASE}/welfare/cases/${caseId}/status`, {
      method: 'PATCH',
      headers: getAuthHeader('welfare'),
      body: JSON.stringify({
        status: 'RESOLVED',
        clinical_notes: 'Welfare officer completed supportive counseling and R&R leave sanction.',
        action_taken: 'R&R Leave Sanctioned + Buddy Support Initiated'
      })
    });
    if (res.ok) {
      showToast(`Case ${caseId} marked RESOLVED. Queue updated.`);
      loadWelfareAlerts();
    }
  } catch (e) {
    alert('Failed to resolve case');
  }
};

window.openExplainModal = function(pseudoId) {
  const alert = cachedAlerts.find(a => a.pseudo_id === pseudoId);
  if (!alert) return;

  const modal = document.getElementById('explain-modal');
  document.getElementById('modal-pseudo-title').textContent = `Clinical Attribution: ${pseudoId}`;
  document.getElementById('modal-archetype').textContent = alert.signal_archetype;
  document.getElementById('modal-rationale').textContent = alert.strategic_rationale;

  const attrList = document.getElementById('modal-attributions-list');
  attrList.innerHTML = '';
  for (const [factor, pct] of Object.entries(alert.attributions || {})) {
    const item = document.createElement('div');
    item.style.marginBottom = '0.5rem';
    item.innerHTML = `
      <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 0.2rem;">
        <span>${factor}</span>
        <strong>${pct}%</strong>
      </div>
      <div style="background: #060913; height: 6px; border-radius: 3px; overflow: hidden;">
        <div style="background: var(--accent-cyan); width: ${pct}%; height: 100%;"></div>
      </div>
    `;
    attrList.appendChild(item);
  }

  const recList = document.getElementById('modal-recommendations-list');
  recList.innerHTML = '';
  (alert.explainability?.recommended_interventions || []).forEach(rec => {
    const li = document.createElement('li');
    li.style.marginBottom = '0.35rem';
    li.style.fontSize = '0.8rem';
    li.textContent = rec;
    recList.appendChild(li);
  });

  modal.classList.add('active');
};

window.closeModal = function(modalId) {
  document.getElementById(modalId).classList.remove('active');
};

window.openBreakGlassModal = function(pseudoId) {
  document.getElementById('break-glass-pseudo').value = pseudoId;
  document.getElementById('break-glass-result').style.display = 'none';
  document.getElementById('break-glass-modal').classList.add('active');
};

window.executeBreakGlass = async function() {
  const pseudoId = document.getElementById('break-glass-pseudo').value;
  const just = document.getElementById('bg-justification').value;
  const dispatch = document.getElementById('bg-dispatch').value;

  try {
    const res = await fetch(`${API_BASE}/welfare/break-glass`, {
      method: 'POST',
      headers: getAuthHeader('welfare'),
      body: JSON.stringify({
        pseudo_id: pseudoId,
        emergency_justification: just,
        dispatch_code: dispatch
      })
    });

    const data = await res.json();
    const resultBox = document.getElementById('break-glass-result');
    resultBox.style.display = 'block';

    if (res.ok) {
      resultBox.innerHTML = `
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid var(--accent-green); padding: 0.75rem; border-radius: 6px;">
          <h4 style="color: var(--accent-green); margin-bottom: 0.5rem;">Emergency Re-Identification Granted</h4>
          <p style="font-size: 0.85rem;"><strong>Personnel Name:</strong> ${data.real_name}</p>
          <p style="font-size: 0.85rem;"><strong>Service No:</strong> ${data.service_no}</p>
          <p style="font-size: 0.85rem;"><strong>Rank & Station:</strong> ${data.rank} - ${data.station} (${data.company})</p>
          <p style="font-size: 0.85rem;"><strong>Contact:</strong> ${data.phone}</p>
          <div style="font-size: 0.75rem; color: var(--accent-amber); margin-top: 0.5rem;">
            ⚠ Immutable Audit Sequence #${data.audit_sequence} etched into HMAC-SHA256 chain.
          </div>
        </div>
      `;
      showToast(`Re-identified ${data.real_name}. Logged with step-up MFA.`);
    } else {
      resultBox.innerHTML = `<div style="color: var(--accent-crimson);">${data.detail}</div>`;
    }
  } catch (err) {
    alert('Re-identification request failed');
  }
};

// ----------------------------------------------------
// 3. COMMANDER STRATEGIC VIEW (k-ANONYMIZED)
// ----------------------------------------------------
window.loadCommanderData = async function(battalionCode) {
  const badge = document.getElementById('cmd-active-battalion');
  if (badge) badge.textContent = battalionCode;

  try {
    const res = await fetch(`${API_BASE}/commander/cohort-readiness?target_battalion=${battalionCode}`, {
      headers: getAuthHeader('commander')
    });
    const data = await res.json();

    const metricsCard = document.getElementById('cmd-metrics-container');
    const suppressionAlert = document.getElementById('cmd-suppression-notice');
    const idorAlert = document.getElementById('cmd-idor-notice');
    if (idorAlert) idorAlert.style.display = 'none';

    if (res.status === 403) {
      // IDOR intercepted by IDS!
      metricsCard.style.display = 'none';
      suppressionAlert.style.display = 'none';
      if (idorAlert) {
        idorAlert.style.display = 'block';
        document.getElementById('cmd-idor-text').textContent = data.detail;
      }
      showToast(`ACCESS DENIED: IDS blocked unauthorized cross-battalion query on ${battalionCode}`);
      return;
    }

    if (data.status === 'SUPPRESSED') {
      metricsCard.style.display = 'none';
      suppressionAlert.style.display = 'block';
      document.getElementById('cmd-suppression-text').textContent = data.message;
    } else {
      metricsCard.style.display = 'block';
      suppressionAlert.style.display = 'none';

      const m = data.strategic_metrics;
      document.getElementById('cmd-readiness-val').textContent = `${m.unit_operational_readiness_pct}%`;
      document.getElementById('cmd-stress-val').textContent = `${m.cohort_stress_index}/100`;
      document.getElementById('cmd-leave-deficit-val').textContent = `${m.personnel_leave_deficit_rate_pct}%`;
      document.getElementById('cmd-fatigue-val').textContent = `${m.circadian_fatigue_rate_pct}%`;
      document.getElementById('cmd-cohort-size').textContent = `Cohort: N=${data.cohort_size} (k>=5 Satisfied)`;
      
      // DP budget display
      const dpBudgetEl = document.getElementById('cmd-dp-budget');
      if (dpBudgetEl) {
        dpBudgetEl.textContent = `DP Budget: ${data.dp_daily_budget_remaining} ε remaining / 24h (${data.dp_budget_status})`;
      }

      const dirList = document.getElementById('cmd-directives-list');
      dirList.innerHTML = '';
      (data.tactical_welfare_directives || []).forEach(d => {
        const li = document.createElement('li');
        li.style.marginBottom = '0.5rem';
        li.style.fontSize = '0.85rem';
        li.textContent = d;
        dirList.appendChild(li);
      });
    }
  } catch (err) {}
};

// ----------------------------------------------------
// 4. SECURITY & IDS CENTER
// ----------------------------------------------------
async function loadAuditChain() {
  try {
    const res = await fetch(`${API_BASE}/admin/audit-chain?limit=15`, {
      headers: getAuthHeader('admin')
    });
    if (res.ok) {
      const data = await res.json();
      const stream = document.getElementById('audit-log-stream');
      stream.innerHTML = '';

      const st = data.integrity_status;
      const integrityBadge = document.getElementById('audit-integrity-badge');
      if (st.valid) {
        integrityBadge.className = 'badge badge-green';
        integrityBadge.textContent = `HMAC VALID (${st.total_blocks} Blocks | WORM Anchor Synced)`;
      } else {
        integrityBadge.className = 'badge badge-crimson';
        integrityBadge.textContent = `CHAIN BROKEN AT #${st.tampered_sequence}`;
      }

      data.blocks.forEach(b => {
        const div = document.createElement('div');
        div.className = `log-entry ${b.is_anomaly ? 'anomaly' : ''}`;
        div.innerHTML = `
          <div style="display: flex; justify-content: space-between;">
            <span><strong>Block #${b.sequence_no}</strong> [${b.action}]</span>
            <span style="color: var(--text-muted);">${new Date(b.timestamp_iso || b.timestamp).toLocaleTimeString()}</span>
          </div>
          <div>Actor: <strong>${b.actor_id}</strong> (${b.actor_role}) | Scope: ${b.scope_battalion || 'GLOBAL'}</div>
          <div class="log-hash">HMAC: ${b.entry_hash.slice(0, 24)}... | Prev: ${b.previous_hash.slice(0, 16)}...</div>
        `;
        stream.appendChild(div);
      });
    }
  } catch (e) {}
}

async function loadIdsAlerts() {
  try {
    const res = await fetch(`${API_BASE}/admin/ids-alerts`, {
      headers: getAuthHeader('admin')
    });
    if (res.ok) {
      const data = await res.json();
      const container = document.getElementById('ids-alerts-container');
      container.innerHTML = '';

      if (data.alerts.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem;">No intrusion attempts detected. Security baseline clear.</div>';
        return;
      }

      data.alerts.forEach(a => {
        const div = document.createElement('div');
        div.className = 'card';
        div.style.borderLeft = '4px solid var(--accent-crimson)';
        div.style.padding = '0.75rem';
        div.style.marginBottom = '0.5rem';
        div.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
            <span class="badge badge-crimson">THREAT SCORE: ${(a.anomaly_score * 100).toFixed(0)}%</span>
            <span style="font-size: 0.75rem; color: var(--text-muted);">${new Date(a.timestamp).toLocaleTimeString()}</span>
          </div>
          <div style="font-size: 0.85rem; font-weight: 700; color: #fca5a5;">${a.action}</div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">Actor: <strong>${a.actor_id}</strong> (${a.actor_role})</div>
          <div style="font-size: 0.75rem; background: #060913; padding: 0.4rem; border-radius: 4px; margin-top: 0.35rem; font-family: monospace;">
            ${a.details}
          </div>
        `;
        container.appendChild(div);
      });
    }
  } catch (e) {}
}

window.runChainVerification = async function() {
  try {
    const res = await fetch(`${API_BASE}/admin/verify-integrity`, {
      method: 'POST',
      headers: getAuthHeader('admin')
    });
    const data = await res.json();
    if (data.valid) {
      showToast(`HMAC Audit Verified: All ${data.total_blocks} blocks intact with WORM anchoring.`);
    } else {
      showToast(`INTEGRITY VIOLATION at Block #${data.tampered_sequence}!`);
    }
    loadAuditChain();
  } catch (e) {
    alert('Verification failed');
  }
};

// ----------------------------------------------------
// 5. HACKATHON LIVE DEMO TRIGGERS
// ----------------------------------------------------
window.triggerRogueQuery = async function() {
  try {
    const res = await fetch(`${API_BASE}/demo/trigger-rogue-query`, {
      method: 'POST',
      headers: getAuthHeader('admin')
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      if (res.status === 404) {
        alert('Demo triggers are disabled when DEMO_MODE=false in your .env');
      } else {
        alert(err.detail || `Trigger failed with status ${res.status}`);
      }
      return;
    }
    const data = await res.json();
    showToast(`INSIDER THREAT INTERCEPTED: ${data.actor} blocked by IDS.`);
    switchRole('admin');
  } catch (e) {
    alert(`Connection error: ${e.message}`);
  }
};

window.simulateTampering = async function() {
  try {
    const res = await fetch(`${API_BASE}/demo/simulate-tampering`, {
      method: 'POST',
      headers: getAuthHeader('admin')
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      if (res.status === 404) {
        alert('Demo triggers are disabled when DEMO_MODE=false in your .env');
      } else {
        alert(err.detail || `Tampering failed with status ${res.status}`);
      }
      return;
    }
    const data = await res.json();
    showToast('DATABASE TAMPERING SIMULATED: HMAC signature failed!');
    switchRole('admin');
  } catch (e) {
    alert(`Tampering simulation error: ${e.message}`);
  }
};

window.restoreChain = async function() {
  try {
    const res = await fetch(`${API_BASE}/demo/restore-chain`, {
      method: 'POST',
      headers: getAuthHeader('admin')
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || `Restore failed with status ${res.status}`);
      return;
    }
    showToast('HMAC Audit Chain restored.');
    switchRole('admin');
  } catch (e) {
    alert(`Restore error: ${e.message}`);
  }
};

function showToast(msg) {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span style="color: var(--accent-cyan);">⚡</span> ${msg}`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}
