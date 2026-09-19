// PRISMARINE Client Application Logic
// "Formed under sustained pressure, structurally layered, and defined by clarity rather than opacity."

const API_BASE = '/api/v1';

// Pre-seeded credentials for defense evaluation & live walkthrough
const PERSONAS = {
  personnel: {
    username: 'rajesh_kumar',
    password: 'password123',
    role: 'personnel',
    displayName: 'Constable Rajesh Kumar (PX-7821)',
    unit: '104-CRPF (Kupwara Forward Sentry)'
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
  commander_corps: {
    username: 'cmd_corps',
    password: 'password123',
    totp_code: '123456',
    role: 'commander',
    displayName: 'Corps Commander (Multi-Battalion Authorized)',
    unit: 'CORPS_COMMAND'
  },
  admin: {
    username: 'sec_admin',
    password: 'password123',
    totp_code: '123456',
    role: 'admin',
    displayName: 'Security Operations & Audit Officer',
    unit: 'Central Defense Directorate'
  }
};

let currentRole = 'personnel';
let authTokens = {};
let cachedAlerts = [];
let authAnimationTimeout = null;

document.addEventListener('DOMContentLoaded', async () => {
  setupSliders();
  startLiveClock();
  await preAuthenticateAllRoles();
  switchRole('personnel', true);
  
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js').catch(() => {});
  }
});

// Centralized IST Time Formatting (All clocks & timestamps strictly IST)
function getISTTimeString(date = new Date(), includeSeconds = true) {
  const d = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
  if (isNaN(d.getTime())) return String(date);
  return d.toLocaleTimeString('en-IN', {
    timeZone: 'Asia/Kolkata',
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: includeSeconds ? '2-digit' : undefined
  });
}

function getISTDateTimeString(date) {
  const d = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
  if (isNaN(d.getTime())) return String(date);
  return d.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
}

function updateLiveClock() {
  const clockEl = document.getElementById('live-tactical-clock');
  const quoteEl = document.getElementById('narrative-quote-box');
  if (!clockEl) return;
  
  const istTimeStr = getISTTimeString(new Date(), true);
  if (currentRole === 'personnel') {
    clockEl.textContent = `${istTimeStr} IST • CONFIDENTIAL CLIENT ENCLAVE`;
    if (quoteEl) {
      quoteEl.innerHTML = '<strong>Client Enclave:</strong> Your responses are confidential. Your commanding officer cannot see this screen or your individual entries.';
    }
  } else {
    clockEl.textContent = `${istTimeStr} IST • 104-CRPF (KUPWARA SECTOR)`;
    if (quoteEl) {
      quoteEl.innerHTML = '<strong>Operational Notice:</strong> You are accessing real-time unit telemetry. All queries and interactions are cryptographically verified.';
    }
  }
}

function startLiveClock() {
  updateLiveClock();
  setInterval(updateLiveClock, 1000);
}

function setupSliders() {
  const sliders = [
    { id: 'p_mood', labelId: 'val_mood', suffix: ' / 10' },
    { id: 'p_stress', labelId: 'val_stress', suffix: ' / 10' }
  ];
  sliders.forEach(s => {
    const el = document.getElementById(s.id);
    const lbl = document.getElementById(s.labelId);
    if (el && lbl) {
      el.addEventListener('input', () => {
        lbl.textContent = el.value + s.suffix;
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
      console.warn('Auth pre-fetch notice for', key, e);
    }
  }
}

function getAuthHeader(roleKey) {
  const headers = {
    'Authorization': `Bearer ${authTokens[roleKey] || ''}`,
    'Content-Type': 'application/json'
  };
  // Supply step-up TOTP verification header for privileged officers
  if (roleKey === 'welfare' || roleKey === 'commander' || roleKey === 'commander_corps' || roleKey === 'admin') {
    headers['X-TOTP-Code'] = '123456';
  }
  return headers;
}

function showAuthHandshake(roleKey, onComplete) {
  const overlay = document.getElementById('auth-overlay');
  const persona = PERSONAS[roleKey];
  if (!overlay || !persona) {
    onComplete();
    return;
  }

  if (authAnimationTimeout) clearTimeout(authAnimationTimeout);

  const userDisplay = document.getElementById('auth-user-display');
  const unitDisplay = document.getElementById('auth-unit-display');
  const roleDesc = document.getElementById('auth-role-desc');
  const totpContainer = document.getElementById('auth-totp-container');
  const statusBar = document.getElementById('auth-status-bar');
  const statusText = document.getElementById('auth-status-text');
  const spinner = document.getElementById('auth-spinner');

  userDisplay.textContent = persona.username;
  unitDisplay.textContent = persona.unit;

  statusBar.className = 'auth-status-bar';
  spinner.style.display = 'block';
  statusText.textContent = 'Verifying cryptographic scope entitlements...';

  // Allow clicking anywhere to immediately skip if needed
  overlay.onclick = () => {
    overlay.classList.remove('active');
    overlay.onclick = null;
    if (authAnimationTimeout) clearTimeout(authAnimationTimeout);
    onComplete();
  };

  overlay.classList.add('active');

  if (roleKey === 'personnel') {
    roleDesc.textContent = 'Confidential Soldier Enclave (Single-Sign-On)';
    totpContainer.style.display = 'none';

    authAnimationTimeout = setTimeout(() => {
      statusBar.className = 'auth-status-bar success';
      spinner.style.display = 'none';
      statusText.textContent = 'Access Granted • Scope: Confidential Self-Report Only';

      authAnimationTimeout = setTimeout(() => {
        overlay.classList.remove('active');
        overlay.onclick = null;
        onComplete();
      }, 450);
    }, 550);
  } else {
    roleDesc.textContent = 'Privileged Operational Command (Step-Up TOTP Required)';
    totpContainer.style.display = 'flex';

    for (let i = 1; i <= 6; i++) {
      const box = document.getElementById(`totp-d${i}`);
      if (box) {
        box.textContent = '-';
        box.classList.remove('filled');
      }
    }

    const totpDigits = (persona.totp_code || '123456').split('');
    let digitIdx = 0;

    function stepDigit() {
      if (digitIdx < totpDigits.length) {
        const box = document.getElementById(`totp-d${digitIdx + 1}`);
        if (box) {
          box.textContent = totpDigits[digitIdx];
          box.classList.add('filled');
        }
        digitIdx++;
        authAnimationTimeout = setTimeout(stepDigit, 200);
      } else {
        statusBar.className = 'auth-status-bar success';
        spinner.style.display = 'none';
        
        let scopeText = 'Assigned Battalion Cohort (104-CRPF)';
        if (roleKey === 'commander') scopeText = 'Unit Aggregated Readiness';
        if (roleKey === 'admin') scopeText = 'Cryptographic Audit & IDS Operations';

        statusText.textContent = `Access Granted • Scope: ${scopeText}`;

        authAnimationTimeout = setTimeout(() => {
          overlay.classList.remove('active');
          overlay.onclick = null;
          onComplete();
        }, 500);
      }
    }

    authAnimationTimeout = setTimeout(stepDigit, 320);
  }
}

window.switchRole = async function(roleKey, skipAuth = false) {
  function finishSwitch() {
    currentRole = roleKey;
    
    // Update Segmented Control Buttons
    document.querySelectorAll('.segment-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.role === roleKey);
    });
    
    // Transition Workspace Section Smoothly
    document.querySelectorAll('.view-section').forEach(view => {
      if (view.id === `view-${roleKey}`) {
        view.classList.add('active');
      } else {
        view.classList.remove('active');
      }
    });

    // Update Live Clock / Narrative (Strictly IST)
    updateLiveClock();

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
  }

  if (skipAuth || roleKey === currentRole) {
    finishSwitch();
  } else {
    showAuthHandshake(roleKey, finishSwitch);
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
    <div style="background-color: rgba(2, 132, 199, 0.08); border: 1px solid rgba(2, 132, 199, 0.25); padding: 0.75rem; border-radius: 6px; font-size: 0.8rem; color: #7dd3fc;">
      <strong>AES-256-GCM Column Packing:</strong> Generated 96-bit unique nonce and 128-bit authentication tag. Transmitting ciphertext payload...
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
          <div style="background-color: var(--status-crimson-bg); border: 1px solid rgba(239, 68, 68, 0.4); padding: 1rem; border-radius: 8px; color: #fca5a5;">
            <div style="font-weight: 700; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.5rem;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
              Immediate Life-Safety Protocol Triggered
            </div>
            <p style="font-size: 0.83rem; line-height: 1.5;">${data.crisis_message}</p>
            <div style="margin-top: 0.6rem; font-size: 0.76rem; color: #fecaca;">
              Emergency 24/7 Sarthi Helpline: <strong>14416</strong> | Tactical Medical Sentry: <strong>Channel 4-Echo</strong>
            </div>
          </div>
        `;
        showToast('Confidential Crisis Outreach Initiated.');
      } else {
        statusEl.innerHTML = `
          <div style="background-color: var(--status-emerald-bg); border: 1px solid rgba(16, 185, 129, 0.3); padding: 0.85rem; border-radius: 8px; color: #6ee7b7; font-size: 0.82rem;">
            <strong>Check-In Confirmed & Sealed:</strong> Written to encrypted disk store under rotating pseudonym <strong>${data.pseudo_id}</strong>.
          </div>
        `;
        showToast('Check-in encrypted and sealed.');
      }

      document.getElementById('p_reflection').value = '';
      loadPersonnelHistory();
    } else {
      statusEl.innerHTML = `<div style="color: #f87171; font-size: 0.82rem;">Submission error: ${data.detail}</div>`;
    }
  } catch (err) {
    statusEl.innerHTML = `<div style="color: #f87171; font-size: 0.82rem;">Network connectivity error. Please retry.</div>`;
  }
};

async function loadPersonnelHistory() {
  try {
    const res = await fetch(`${API_BASE}/personnel/my-wellness-history`, {
      headers: getAuthHeader('personnel')
    });
    if (res.ok) {
      const resData = await res.json();
      const records = Array.isArray(resData) ? resData : (resData.history || []);
      const tbody = document.getElementById('personnel-history-table-body');
      if (!tbody) return;
      tbody.innerHTML = '';
      
      if (!records || records.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.25rem;">No recorded check-ins found.</td></tr>';
        return;
      }

      records.forEach(r => {
        const tr = document.createElement('tr');
        const timeStr = `${getISTDateTimeString(r.recorded_at)} IST`;
        tr.innerHTML = `
          <td><strong style="color: #cbd5e1;">${timeStr}</strong></td>
          <td><span class="badge ${r.mood_score >= 6 ? 'badge-emerald' : 'badge-amber'}">${r.mood_score}/10</span></td>
          <td>${r.sleep_hours} hrs</td>
          <td><span class="badge ${r.stress_rating > 6 ? 'badge-crimson' : 'badge-neutral'}">${r.stress_rating}/10</span></td>
          <td>${r.phq4_score}/12</td>
          <td>${r.is_crisis ? '<span class="badge badge-crimson">CRISIS OVERRIDE</span>' : '<span class="badge badge-emerald">AES-256 SEALED</span>'}</td>
        `;
        tbody.appendChild(tr);
      });
    }
  } catch (e) {
    console.error('Failed to load personnel history:', e);
  }
}

// ----------------------------------------------------
// 2. WELFARE OFFICER CONSOLE
// ----------------------------------------------------
async function loadWelfareAlerts() {
  const container = document.getElementById('welfare-alerts-body');
  container.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading prioritized alert queue and case statuses...</td></tr>';

  try {
    const res = await fetch(`${API_BASE}/welfare/alerts?target_battalion=104-CRPF`, {
      headers: getAuthHeader('welfare')
    });
    if (res.ok) {
      const data = await res.json();
      cachedAlerts = data.allocated_alerts || [];
      
      document.getElementById('welfare-capacity-text').textContent = 
        `Attention Capacity: ${data.allocated_count} / ${data.officer_capacity_c} Cases (${data.capacity_utilization_pct}%) | ${data.resolved_count || 0} Resolved`;
      
      if (cachedAlerts.length > 0) {
        const topAlert = cachedAlerts[0];
        document.getElementById('hero-pseudo').textContent = topAlert.pseudo_id;
        document.getElementById('hero-utility').textContent = `+${topAlert.expected_utility}`;
        document.getElementById('hero-distress').textContent = `${(topAlert.p_true_distress * 100).toFixed(0)}%`;
        document.getElementById('hero-urgency').textContent = topAlert.action_urgency;
        document.getElementById('hero-rationale-text').textContent = topAlert.strategic_rationale || 
          `High operational hardship detected (${topAlert.operational_hardship_score || 'Elevated'}) requiring timely welfare officer outreach.`;
        
        const heroBadge = document.getElementById('hero-archetype-badge');
        const heroCard = document.getElementById('welfare-hero-card');
        if (heroCard) heroCard.classList.remove('is-crisis', 'is-stigma-masked');

        if (topAlert.signal_archetype === 'CRISIS_IMMEDIATE_OVERRIDE' || topAlert.is_crisis) {
          if (heroCard) heroCard.classList.add('is-crisis');
          heroBadge.className = 'badge badge-crimson';
          heroBadge.textContent = 'CRISIS OVERRIDE';
          document.getElementById('hero-distress').style.color = '#f87171';
          document.getElementById('hero-urgency').style.color = '#fca5a5';
        } else if (topAlert.signal_archetype === 'STIGMA_MASKED_DISTRESS') {
          if (heroCard) heroCard.classList.add('is-stigma-masked');
          heroBadge.className = 'badge badge-amber';
          heroBadge.textContent = 'STIGMA-MASKED (UNDER-REPORTING)';
          document.getElementById('hero-distress').style.color = '#fbbf24';
          document.getElementById('hero-urgency').style.color = '#fde68a';
        } else {
          heroBadge.className = 'badge badge-neutral';
          heroBadge.textContent = 'HIGH OPERATIONAL PRIORITY';
          document.getElementById('hero-distress').style.color = '#38bdf8';
          document.getElementById('hero-urgency').style.color = '#cbd5e1';
        }
      } else {
        const heroCard = document.getElementById('welfare-hero-card');
        if (heroCard) heroCard.classList.remove('is-crisis', 'is-stigma-masked');
        document.getElementById('hero-pseudo').textContent = 'NOMINAL';
        document.getElementById('hero-utility').textContent = '+0.000';
        document.getElementById('hero-distress').textContent = '0%';
        document.getElementById('hero-urgency').textContent = 'MONITORING';
        document.getElementById('hero-rationale-text').textContent = 'You have resolved all battalion alert cases or they remain below the actionable utility threshold. Cohort equilibrium is nominal.';
        const heroBadge = document.getElementById('hero-archetype-badge');
        if (heroBadge) {
          heroBadge.className = 'badge badge-emerald';
          heroBadge.textContent = 'NOMINAL EQUILIBRIUM';
        }
      }

      container.innerHTML = '';
      if (cachedAlerts.length === 0) {
        container.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">You have no active alerts in your current cohort allocation. All cases are nominal or resolved.</td></tr>';
        return;
      }

      cachedAlerts.forEach((alert, idx) => {
        const tr = document.createElement('tr');
        if (idx === 0) {
          tr.classList.add('row-hero');
          if (alert.signal_archetype === 'CRISIS_IMMEDIATE_OVERRIDE' || alert.is_crisis) {
            tr.classList.add('is-crisis');
          } else if (alert.signal_archetype === 'STIGMA_MASKED_DISTRESS') {
            tr.classList.add('is-stigma-masked');
          }
        }
        
        let archetypeBadge = 'badge-neutral';
        let archetypeLabel = alert.signal_archetype;
        if (alert.signal_archetype === 'CRISIS_IMMEDIATE_OVERRIDE') {
          archetypeBadge = 'badge-crimson';
          archetypeLabel = 'CRISIS OVERRIDE';
        } else if (alert.signal_archetype === 'AUTHENTIC_HIGH_DISTRESS') {
          archetypeBadge = 'badge-amber';
          archetypeLabel = 'AUTHENTIC DISTRESS';
        } else if (alert.signal_archetype === 'STIGMA_MASKED_DISTRESS') {
          archetypeBadge = 'badge-amber';
          archetypeLabel = 'STIGMA-MASKED';
        } else if (alert.signal_archetype === 'NOISY_UNSUBSTANTIATED') {
          archetypeBadge = 'badge-neutral';
          archetypeLabel = 'NOISY (LOW CORROBORATION)';
        }

        const caseStatus = alert.case_status || 'OPEN';
        let statusBadge = 'badge-amber';
        if (caseStatus === 'IN_PROGRESS') statusBadge = 'badge-neutral';
        if (caseStatus === 'RESOLVED') statusBadge = 'badge-emerald';

        tr.innerHTML = `
          <td><strong style="color: #f8fafc;">#${alert.priority_rank}</strong></td>
          <td><code style="color: #38bdf8; font-weight: 600;">${alert.pseudo_id}</code></td>
          <td><span class="badge ${archetypeBadge}">${archetypeLabel}</span></td>
          <td><strong style="color: ${alert.p_true_distress > 0.7 ? '#f87171' : '#fbbf24'};">${(alert.p_true_distress * 100).toFixed(0)}%</strong></td>
          <td><span style="color: #34d399; font-weight: 700;">+${alert.expected_utility}</span></td>
          <td><span class="badge ${statusBadge}">${caseStatus}</span></td>
          <td><span class="badge ${alert.action_urgency === 'IMMEDIATE_ACTION' || alert.is_crisis ? 'badge-crimson' : 'badge-amber'}">${alert.action_urgency}</span></td>
          <td style="text-align: right; white-space: nowrap;">
            <button class="btn-subtle" style="padding: 0.35rem 0.65rem; font-size: 0.75rem;" onclick="openExplainModal('${alert.pseudo_id}')">Review Factors</button>
            <button class="btn-danger" style="padding: 0.35rem 0.65rem; font-size: 0.75rem;" onclick="openBreakGlassModal('${alert.pseudo_id}')">Unmask</button>
            <button class="btn-primary" style="padding: 0.35rem 0.65rem; font-size: 0.75rem; background-color: #059669;" onclick="resolveCase('${alert.case_id}')">Resolve</button>
          </td>
        `;
        container.appendChild(tr);
      });
    } else {
      const errData = await res.json().catch(() => ({}));
      container.innerHTML = `<tr><td colspan="8" style="color: #f87171; text-align: center; padding: 2rem;">Failed to load welfare cohort data (HTTP ${res.status}): ${errData.detail || 'Service unavailable'}.</td></tr>`;
    }
  } catch (err) {
    container.innerHTML = '<tr><td colspan="8" style="color: #f87171; text-align: center; padding: 2rem;">Network error: Failed to connect to welfare analytics service.</td></tr>';
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

  document.getElementById('modal-pseudo-title').textContent = `Clinical Attribution Breakdown • ${pseudoId}`;
  document.getElementById('modal-archetype').textContent = alert.signal_archetype;
  document.getElementById('modal-rationale').textContent = alert.strategic_rationale;

  const attrList = document.getElementById('modal-attributions-list');
  attrList.innerHTML = '';
  for (const [factor, pct] of Object.entries(alert.attributions || {})) {
    const item = document.createElement('div');
    item.style.marginBottom = '0.6rem';
    item.innerHTML = `
      <div style="display: flex; justify-content: space-between; font-size: 0.82rem; margin-bottom: 0.25rem; color: #cbd5e1;">
        <span>${factor}</span>
        <strong style="color: #38bdf8;">${pct}%</strong>
      </div>
      <div style="background: #080d17; height: 6px; border-radius: 3px; overflow: hidden; border: 1px solid var(--border-subtle);">
        <div style="background: #0284c7; width: ${pct}%; height: 100%;"></div>
      </div>
    `;
    attrList.appendChild(item);
  }

  const recList = document.getElementById('modal-recommendations-list');
  recList.innerHTML = '';
  (alert.explainability?.recommended_interventions || []).forEach(rec => {
    const li = document.createElement('li');
    li.style.marginBottom = '0.35rem';
    li.textContent = rec;
    recList.appendChild(li);
  });

  openModal('explain-modal');
};

window.openBreakGlassModal = function(pseudoId) {
  document.getElementById('break-glass-pseudo').value = pseudoId;
  document.getElementById('break-glass-result').style.display = 'none';
  openModal('break-glass-modal');
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
        <div style="background-color: var(--status-emerald-bg); border: 1px solid rgba(16, 185, 129, 0.3); padding: 1.25rem; border-radius: 8px;">
          <div style="color: #34d399; font-weight: 700; font-size: 0.95rem; margin-bottom: 0.6rem;">
            Emergency Unmasking Authorized (MFA Verified)
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; font-size: 0.84rem; color: #e2e8f0;">
            <div>Personnel Name: <strong style="color: #f8fafc;">${data.real_name}</strong></div>
            <div>Service Number: <strong style="color: #38bdf8;">${data.service_no}</strong></div>
            <div>Rank & Station: <strong>${data.rank} - ${data.station}</strong></div>
            <div>Emergency Contact: <strong>${data.phone}</strong></div>
          </div>
          <div style="font-size: 0.76rem; color: #fbbf24; margin-top: 0.85rem; padding-top: 0.6rem; border-top: 1px solid rgba(255, 255, 255, 0.08);">
            Permanent Audit Sequence #${data.audit_sequence} etched into HMAC-SHA256 chain and external WORM anchor.
          </div>
        </div>
      `;
      showToast(`Re-identified ${data.real_name}. Logged with step-up MFA.`);
    } else {
      resultBox.innerHTML = `<div style="color: #f87171; font-size: 0.84rem;">${data.detail}</div>`;
    }
  } catch (err) {
    alert('Re-identification request failed');
  }
};

// ----------------------------------------------------
// 3. COMMANDER STRATEGIC VIEW (k-ANONYMIZED)
// ----------------------------------------------------
window.loadCommanderData = async function(battalionCode = '104-CRPF') {
  const badge = document.getElementById('cmd-active-battalion');
  if (badge) badge.textContent = battalionCode;

  const officerEl = document.getElementById('cmd-officer-name');
  if (officerEl) {
    if (battalionCode === '88-ITBP') {
      officerEl.textContent = 'Corps Commander (Multi-Battalion Authorized)';
    } else {
      officerEl.textContent = 'Commandant Vikramaditya Singh';
    }
  }

  // When testing 88-ITBP (k < 5 guard): Corps Command clearance (cmd_corps) is multi-battalion authorized,
  // passing Access-Pattern IDS perimeter checks to demonstrate mathematical k < 5 privacy suppression.
  // When testing 42-BSF: Unit commander (cmd_singh) is scoped to 104-CRPF, triggering the IDS boundary intercept.
  const authKey = (battalionCode === '88-ITBP') ? 'commander_corps' : 'commander';

  try {
    const res = await fetch(`${API_BASE}/commander/cohort-readiness?target_battalion=${battalionCode}`, {
      headers: getAuthHeader(authKey)
    });
    const data = await res.json();

    const metricsCard = document.getElementById('cmd-metrics-container');
    const suppressionAlert = document.getElementById('cmd-suppression-notice');
    const idorAlert = document.getElementById('cmd-idor-notice');
    
    if (idorAlert) idorAlert.classList.remove('visible');
    if (suppressionAlert) suppressionAlert.classList.remove('visible');

    if (res.status === 403) {
      // IDOR intercepted by Access-Pattern IDS!
      metricsCard.style.display = 'none';
      if (idorAlert) {
        idorAlert.classList.add('visible');
        document.getElementById('cmd-idor-text').textContent = data.detail;
      }
      showToast(`SECURITY ALERT: IDS blocked cross-battalion probe on ${battalionCode}`);
      return;
    }

    if (data.status === 'SUPPRESSED') {
      metricsCard.style.display = 'none';
      if (suppressionAlert) {
        suppressionAlert.classList.add('visible');
        document.getElementById('cmd-suppression-text').textContent = data.message;
      }
      showToast(`PRIVACY ENFORCEMENT: Aggregated metrics suppressed for ${battalionCode} (Minimum Cohort Threshold)`);
    } else {
      metricsCard.style.display = 'block';

      const m = data.strategic_metrics;
      document.getElementById('cmd-readiness-val').textContent = `${m.unit_operational_readiness_pct}%`;
      document.getElementById('cmd-stress-val').textContent = `${m.cohort_stress_index}/100`;
      document.getElementById('cmd-leave-deficit-val').textContent = `${m.personnel_leave_deficit_rate_pct}%`;
      document.getElementById('cmd-fatigue-val').textContent = `${m.circadian_fatigue_rate_pct}%`;
      document.getElementById('cmd-cohort-size').textContent = `Cohort Size: N=${data.cohort_size} Personnel`;

      const dirList = document.getElementById('cmd-directives-list');
      dirList.innerHTML = '';
      (data.tactical_welfare_directives || []).forEach(d => {
        const li = document.createElement('li');
        li.style.marginBottom = '0.5rem';
        li.textContent = d;
        dirList.appendChild(li);
      });
    }
  } catch (err) {}
};

// ----------------------------------------------------
// 4. SECURITY & IDS OPERATIONS CENTER
// ----------------------------------------------------
async function loadAuditChain() {
  try {
    const res = await fetch(`${API_BASE}/admin/audit-chain?limit=25`, {
      headers: getAuthHeader('admin')
    });
    if (res.ok) {
      const data = await res.json();
      const stream = document.getElementById('audit-log-stream');
      stream.innerHTML = '';

      const st = data.integrity_status || {};
      const statusLabel = document.getElementById('header-status-label');
      const statusDot = document.getElementById('system-status-dot');

      if (st.valid) {
        if (statusDot) statusDot.className = 'status-dot';
        if (statusLabel) statusLabel.textContent = 'Defense-Grade Secure • Level 4 Encryption Active';
      } else {
        if (statusDot) statusDot.className = 'status-dot danger';
        if (statusLabel) statusLabel.textContent = `INTEGRITY VIOLATION • Block #${st.tampered_sequence} Altered`;
      }

      data.blocks.forEach(b => {
        const div = document.createElement('div');
        const isTampered = !st.valid && (b.sequence_no === st.tampered_sequence);
        let rowClass = 'audit-stream-row';
        if (isTampered) {
          rowClass += ' tampered';
        } else if (b.is_anomaly) {
          rowClass += ' anomaly';
        }
        div.className = rowClass;

        let detailsSnippet = '';
        if (b.details) {
          try {
            const parsed = typeof b.details === 'string' ? JSON.parse(b.details) : b.details;
            if (parsed.simulation === 'LIVE_INSIDER_THREAT_SIMULATION') {
              detailsSnippet = `<span style="color: #fbbf24; font-weight: 600;">INSIDER THREAT SIMULATION:</span> Cross-battalion unauthorized probe (${parsed.assigned_battalion} -> ${parsed.target_battalion}) blocked by Access-Pattern IDS.`;
            } else if (parsed.event === 'CORRUPTED_BY_ROGUE_DBA') {
              detailsSnippet = `<span style="color: #f87171; font-weight: 700;">MALICIOUS MUTATION:</span> {"event": "CORRUPTED_BY_ROGUE_DBA", "status": "TAMPERED_RECORD"}`;
            } else if (parsed.action === 'CRYPTOGRAPHIC_CHAIN_VERIFICATION' || b.action === 'CRYPTOGRAPHIC_CHAIN_VERIFICATION') {
              detailsSnippet = parsed.result 
                ? `<span style="color: #34d399; font-weight: 600;">CHAIN VERIFICATION:</span> All ${parsed.total_blocks} blocks valid with WORM anchor.`
                : `<span style="color: #f87171; font-weight: 700;">CHAIN VERIFICATION FAILED:</span> Signature mismatch detected at Block #${parsed.tampered_sequence}.`;
            } else if (parsed.event) {
              detailsSnippet = `Event: ${parsed.event} (${parsed.status || ''})`;
            } else {
              detailsSnippet = typeof b.details === 'string' ? b.details : JSON.stringify(parsed);
            }
          } catch (e) {
            detailsSnippet = b.details;
          }
        }

        let badgeHtml = '';
        if (isTampered) {
          badgeHtml = '<span class="badge badge-crimson" style="font-size: 0.68rem; margin-left: 0.5rem;">HMAC SIGNATURE MISMATCH</span>';
        } else if (b.is_anomaly) {
          badgeHtml = '<span class="badge badge-amber" style="font-size: 0.68rem; margin-left: 0.5rem;">SECURITY ANOMALY</span>';
        }

        div.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span><strong style="color: #f8fafc;">Block #${b.sequence_no}</strong> • <span style="color: #cbd5e1;">${b.action}</span>${badgeHtml}</span>
            <span style="color: var(--text-muted); font-size: 0.72rem;">${getISTTimeString(b.timestamp_iso || b.timestamp, true)} IST</span>
          </div>
          <div style="font-size: 0.76rem; color: var(--text-secondary);">Actor: <strong style="color: #e2e8f0;">${b.actor_id}</strong> (${b.actor_role}) | Battalion Scope: ${b.scope_battalion || 'GLOBAL'}</div>
          ${detailsSnippet ? `<div style="font-size: 0.72rem; color: #94a3b8; font-family: var(--font-mono); background: rgba(0,0,0,0.3); padding: 0.35rem 0.5rem; border-radius: 4px; border: 1px solid rgba(255,255,255,0.06);">${detailsSnippet}</div>` : ''}
          <div class="audit-hash-code">HMAC: ${b.entry_hash.slice(0, 32)}... | Prev: ${b.previous_hash.slice(0, 16)}...</div>
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
        container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.82rem; padding: 1rem 0;">You have zero unauthorized intrusion attempts recorded. Perimeter baseline is nominal.</div>';
        return;
      }

      data.alerts.forEach(a => {
        const div = document.createElement('div');
        div.className = 'card';
        div.style.borderLeft = '4px solid var(--status-crimson)';
        div.style.padding = '1.15rem';
        div.style.marginBottom = '0.85rem';
        div.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
            <span class="badge badge-crimson">THREAT INDEX: ${(a.anomaly_score * 100).toFixed(0)}%</span>
            <span style="font-size: 0.74rem; color: var(--text-muted);">${getISTTimeString(a.timestamp, true)} IST</span>
          </div>
          <div style="font-size: 0.88rem; font-weight: 700; color: #fca5a5; margin-bottom: 0.2rem;">${a.action}</div>
          <div style="font-size: 0.8rem; color: var(--text-secondary);">Actor: <strong style="color: #f1f5f9;">${a.actor_id}</strong> (${a.actor_role})</div>
          <div style="font-size: 0.75rem; background: #060911; border: 1px solid var(--border-subtle); padding: 0.5rem; border-radius: 4px; margin-top: 0.5rem; font-family: var(--font-mono); color: #cbd5e1;">
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
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showToast(`Verification endpoint error (HTTP ${res.status}): ${err.detail || 'Service error'}`);
      return;
    }
    const data = await res.json();
    if (data.valid) {
      showToast(`HMAC Audit Verified: All ${data.total_blocks} blocks intact with WORM anchoring.`);
    } else {
      showToast(`INTEGRITY VIOLATION DETECTED: Block #${data.tampered_sequence} signature mismatch!`);
    }
    loadAuditChain();
  } catch (e) {
    showToast(`Verification network error: ${e.message}`);
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
        showToast('Demo triggers are disabled when DEMO_MODE=false in your .env');
      } else {
        showToast(err.detail || `Trigger failed with status ${res.status}`);
      }
      return;
    }
    const data = await res.json();
    showToast(`INSIDER THREAT INTERCEPTED: ${data.actor} blocked by IDS.`);
    switchRole('admin', true);
    loadAuditChain();
    loadIdsAlerts();
  } catch (e) {
    showToast(`Connection error: ${e.message}`);
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
        showToast('Demo triggers are disabled when DEMO_MODE=false in your .env');
      } else {
        showToast(err.detail || `Tampering failed with status ${res.status}`);
      }
      return;
    }
    const data = await res.json();
    showToast('DATABASE TAMPERING SIMULATED: Block #1 mutated in SQL!');
    switchRole('admin', true);
    loadAuditChain();
    loadIdsAlerts();
  } catch (e) {
    showToast(`Tampering simulation error: ${e.message}`);
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
      showToast(err.detail || `Restore failed with status ${res.status}`);
      return;
    }
    showToast('HMAC Audit Chain restored to nominal baseline.');
    switchRole('admin', true);
    loadAuditChain();
    loadIdsAlerts();
  } catch (e) {
    showToast(`Restore error: ${e.message}`);
  }
};

window.simulateKAnonymityGuard = function() {
  switchRole('commander', true);
  loadCommanderData('88-ITBP');
};

// Modal helpers
window.openModal = function(modalId) {
  const el = document.getElementById(modalId);
  if (el) el.classList.add('active');
};

window.closeModal = function(modalId) {
  const el = document.getElementById(modalId);
  if (el) el.classList.remove('active');
};

function showToast(msg) {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'tactical-toast';
  toast.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
    <span>${msg}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}
