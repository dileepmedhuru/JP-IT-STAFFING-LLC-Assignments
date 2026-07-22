// ═══════════════════════════════════════════════════════════════════
//  Singing Bowl Export Desk – script.js
//  All frontend logic – fetch API calls, DOM updates, state management
// ═══════════════════════════════════════════════════════════════════

const API = 'http://localhost:5000';   // Flask backend base URL

// ── App state ────────────────────────────────────────────────────────────────
const state = {
  pdfPath:     null,
  pdfUrl:      null,
  leads:       [],
  currentStep: 1,
};

// ── Workflow step highlighter ─────────────────────────────────────────────────
function setStep(n) {
  state.currentStep = n;
  for (let i = 1; i <= 4; i++) {
    const el = document.getElementById(`step${i}`);
    if (!el) continue;
    el.classList.remove('active', 'done');
    if (i < n)  el.classList.add('done');
    if (i === n) el.classList.add('active');
  }
}

// Default email template
const DEFAULT_TEMPLATE = `<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
  <h2 style="color:#b8860b;">Handcrafted Singing Bowl Export Catalog</h2>
  <p>Dear <strong>{{ownerName}}</strong>,</p>
  <p>We are delighted to reach out to <strong>{{businessName}}</strong> regarding our
     exclusive collection of handcrafted singing bowls from the Himalayan region.</p>
  <p>We offer competitive wholesale pricing, custom packaging, and reliable
     international shipping to <strong>{{country}}</strong>.</p>
  <p>Please find our full export catalog attached for your reference.</p>
  <p>📱 WhatsApp: <strong>{{whatsappNumber}}</strong></p>
  <hr style="border:none;border-top:1px solid #eee;margin:20px 0;"/>
  <p style="font-size:12px;color:#999;">
    <a href="{{unsubscribeUrl}}">Unsubscribe</a>
  </p>
</div>`;

// ─────────────────────────────────────────────────────────────────────────────
//  INIT
// ─────────────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Set default template
  const ta = document.getElementById('inp-template');
  if (ta) ta.value = DEFAULT_TEMPLATE;

  // Load initial data
  loadConfig();
  loadStats();
  loadLeads();
  setStep(1);   // start at step 1
});

// ─────────────────────────────────────────────────────────────────────────────
//  LOAD CONFIG (connection status)
// ─────────────────────────────────────────────────────────────────────────────

async function loadConfig() {
  try {
    const res  = await fetch(`${API}/api/config`);
    const cfg  = await res.json();

    // Search API badge
    const searchBadge = document.getElementById('conn-search-badge');
    const searchName  = document.getElementById('conn-search-name');
    const searchText  = document.getElementById('conn-search-text');

    searchName.textContent = cfg.serpapi.mode;
    searchText.textContent = cfg.serpapi.connected ? 'Connected' : 'Demo Mode';
    searchBadge.className  = `conn-badge ${cfg.serpapi.connected ? 'connected' : 'demo'}`;

    // Mail badge
    const mailBadge = document.getElementById('conn-mail-badge');
    const mailName  = document.getElementById('conn-mail-name');
    const mailText  = document.getElementById('conn-mail-text');

    mailName.textContent = cfg.mail.email;
    if (cfg.mail.connected && !cfg.mail.simulated) {
      mailText.textContent = 'Connected';
      mailBadge.className  = 'conn-badge connected';
    } else if (cfg.mail.connected && cfg.mail.simulated) {
      mailText.textContent = 'Simulated';
      mailBadge.className  = 'conn-badge demo';
    } else {
      mailText.textContent = 'Not set';
      mailBadge.className  = 'conn-badge disconnected';
    }

  } catch (err) {
    console.warn('Config load failed:', err.message);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  STATS
// ─────────────────────────────────────────────────────────────────────────────

async function loadStats() {
  try {
    const res   = await fetch(`${API}/api/stats`);
    const stats = await res.json();
    updateKPI(stats);
  } catch (err) {
    console.warn('Stats load failed:', err.message);
  }
}

function updateKPI(stats) {
  setKPI('kpi-total',     stats.total_leads);
  setKPI('kpi-contacted', stats.contacted);
  setKPI('kpi-sent',      stats.emails_sent);
  setKPI('kpi-failed',    stats.failed);
}

function setKPI(id, newVal) {
  const el = document.getElementById(id);
  if (!el) return;
  if (el.textContent !== String(newVal)) {
    el.textContent = newVal;
    el.classList.remove('kpi-pop');
    void el.offsetWidth;   // reflow
    el.classList.add('kpi-pop');
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  LEADS TABLE
// ─────────────────────────────────────────────────────────────────────────────

async function loadLeads() {
  try {
    const res   = await fetch(`${API}/api/leads`);
    const leads = await res.json();
    state.leads = leads;
    renderLeads(leads);
    document.getElementById('leads-count').textContent = leads.length;
  } catch (err) {
    console.warn('Leads load failed:', err.message);
  }
}

function renderLeads(leads) {
  const tbody = document.getElementById('leads-tbody');
  tbody.innerHTML = '';

  if (!leads || leads.length === 0) {
    tbody.innerHTML = `
      <tr class="empty-state">
        <td colspan="10">No leads yet. Use Search Leads to import data.</td>
      </tr>`;
    document.getElementById('leads-count').textContent = '0';
    return;
  }

  document.getElementById('leads-count').textContent = leads.length;

  leads.forEach(lead => {
    const score      = lead.score || 0;
    const contacted  = lead.contacted;
    const hasEmail   = !!lead.email;
    const domain     = lead.source || 'unknown';

    const tr = document.createElement('tr');
    tr.id = `lead-row-${lead.id}`;

    tr.innerHTML = `
      <td>
        <a class="business-link"
           href="${esc(lead.website || '#')}"
           target="_blank"
           title="Visit website">${esc(lead.business_name)}</a>
      </td>
      <td>${esc(lead.owner || '—')}</td>
      <td class="td-wrap">${esc(lead.email || '—')}</td>
      <td>${esc(lead.phone || '—')}</td>
      <td>${esc(lead.country)}</td>
      <td>${esc(domain)}</td>
      <td>
        <div class="score-bar-wrap">
          <div class="score-bar">
            <div class="score-bar-fill" style="width:${score}%"></div>
          </div>
          <span class="score-val">${score}</span>
        </div>
      </td>
      <td>
        <span class="pill ${contacted ? 'pill-yes' : 'pill-no'}" id="contacted-${lead.id}">
          ${contacted ? 'Yes' : 'No'}
        </span>
      </td>
      <td>
        <button
          class="btn btn-green btn-sm"
          id="send-btn-${lead.id}"
          onclick="sendSingleEmail(${lead.id})"
          ${!hasEmail ? 'disabled title="No email address"' : ''}
        >Send</button>
      </td>
      <td>
        <button class="btn btn-red btn-sm" onclick="deleteLead(${lead.id})">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M9 6V4h6v2"/>
          </svg>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  SEARCH LEADS
// ─────────────────────────────────────────────────────────────────────────────

async function searchLeads() {
  const btn      = document.getElementById('search-btn');
  const alertDiv = document.getElementById('search-alert-area');

  const keywords  = document.getElementById('inp-keywords').value.trim();
  const countries = document.getElementById('inp-countries').value.trim();
  const limit     = parseInt(document.getElementById('inp-limit').value) || 5;
  const seedUrls  = document.getElementById('inp-seed').value.trim();

  if (!keywords) {
    showAlert(alertDiv, 'Please enter search keywords.', 'error');
    return;
  }

  setLoading(btn, true, 'Working…');
  alertDiv.innerHTML = '';

  try {
    const res  = await fetch(`${API}/api/search`, {
      method:  'POST',
      headers: {'Content-Type': 'application/json'},
      body:    JSON.stringify({ keywords, countries, limit, seed_urls: seedUrls }),
    });

    const data = await res.json();

    if (!res.ok || data.error) {
      showAlert(alertDiv, data.error || 'Search failed.', 'error');
      return;
    }

    const type = data.demo_mode ? 'warning' : 'success';
    showAlert(alertDiv, data.message, type);

    // Refresh table and stats
    await loadLeads();
    await loadStats();
    setStep(2);   // leads imported → move to step 2 (upload PDF)

  } catch (err) {
    showAlert(alertDiv, `Network error: ${err.message}`, 'error');
  } finally {
    setLoading(btn, false, 'Search Leads');
    btn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      Search Leads`;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  PDF UPLOAD
// ─────────────────────────────────────────────────────────────────────────────

async function uploadPDF(input) {
  if (!input.files.length) return;

  const file      = input.files[0];
  const alertDiv  = document.getElementById('email-alert-area');

  showAlert(alertDiv, 'Uploading PDF…', 'info');

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res  = await fetch(`${API}/api/upload`, { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok || data.error) {
      showAlert(alertDiv, data.error || 'Upload failed.', 'error');
      return;
    }

    // Update UI
    state.pdfPath = data.path;
    state.pdfUrl  = data.url;

    document.getElementById('pdf-name-display').innerHTML =
      `<strong>${esc(data.filename)}</strong>`;

    const urlEl = document.getElementById('pdf-url-link');
    urlEl.href        = data.url;
    urlEl.textContent = data.url;
    urlEl.style.display = 'block';

    showAlert(alertDiv, `${data.filename} uploaded successfully.`, 'success');
    setStep(3);   // PDF uploaded → move to step 3 (send bulk email)

  } catch (err) {
    showAlert(alertDiv, `Upload error: ${err.message}`, 'error');
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  SEND SINGLE EMAIL
// ─────────────────────────────────────────────────────────────────────────────

async function sendSingleEmail(leadId) {
  const btn      = document.getElementById(`send-btn-${leadId}`);
  const alertDiv = document.getElementById('email-alert-area');

  const subject  = document.getElementById('inp-subject').value.trim();
  const template = document.getElementById('inp-template').value;

  if (!subject) {
    showAlert(alertDiv, 'Please enter an email subject.', 'error');
    return;
  }

  btn.disabled    = true;
  btn.textContent = '…';

  // Find lead email for progress display
  const lead = state.leads.find(l => l.id === leadId);
  showAlert(alertDiv, `Sending email to ${lead?.email || 'lead #' + leadId}…`, 'info');

  try {
    const res = await fetch(`${API}/api/send-email/${leadId}`, {
      method:  'POST',
      headers: {'Content-Type': 'application/json'},
      body:    JSON.stringify({
        subject,
        template,
        pdf_path: state.pdfPath,
      }),
    });

    const data = await res.json();

    if (!res.ok || data.error) {
      showAlert(alertDiv, data.error || 'Send failed.', 'error');
      btn.disabled    = false;
      btn.textContent = 'Send';
      return;
    }

    const simNote = data.simulated ? ' (simulated – no SMTP credentials)' : '';
    showAlert(alertDiv, `✅ Email Sent Successfully${simNote}`, 'success');

    // Update contacted pill in-place (no full reload)
    const pill = document.getElementById(`contacted-${leadId}`);
    if (pill) {
      pill.textContent = 'Yes';
      pill.className   = 'pill pill-yes';
    }
    btn.textContent = '✓ Sent';

    // Update state cache
    if (lead) lead.contacted = true;

    // Update KPIs
    if (data.stats) updateKPI(data.stats);

  } catch (err) {
    showAlert(alertDiv, `Network error: ${err.message}`, 'error');
    btn.disabled    = false;
    btn.textContent = 'Send';
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  SEND BULK EMAIL
// ─────────────────────────────────────────────────────────────────────────────

async function sendBulkEmail() {
  const btn      = document.getElementById('bulk-btn');
  const alertDiv = document.getElementById('email-alert-area');
  const logEl    = document.getElementById('progress-log');

  const subject  = document.getElementById('inp-subject').value.trim();
  const template = document.getElementById('inp-template').value;

  if (!subject) {
    showAlert(alertDiv, 'Please enter an email subject first.', 'error');
    return;
  }

  setLoading(btn, true, 'Sending…');
  alertDiv.innerHTML = '';
  logEl.innerHTML    = '';
  logEl.style.display = 'block';

  appendLog(logEl, '⏳ Starting bulk email send…', '');

  try {
    const res  = await fetch(`${API}/api/send-bulk-email`, {
      method:  'POST',
      headers: {'Content-Type': 'application/json'},
      body:    JSON.stringify({
        subject,
        template,
        pdf_path: state.pdfPath,
      }),
    });

    const data = await res.json();

    if (!res.ok || data.error) {
      showAlert(alertDiv, data.error || 'Bulk send failed.', 'error');
      return;
    }

    // Animate through each result
    for (const p of (data.progress || [])) {
      const cls = p.status === 'sent' ? 'log-sent' : 'log-error';
      const ico = p.status === 'sent' ? '✅' : '❌';
      const sim = p.simulated ? ' (simulated)' : '';
      appendLog(logEl, `${ico} ${p.email}${sim}`, cls);
      await sleep(300);
    }

    appendLog(logEl, `─── Done: ${data.sent} sent, ${data.failed} failed ───`, '');

    const simNote = data.progress?.some(p => p.simulated)
      ? ' (simulated – no SMTP credentials)'
      : '';
    showAlert(alertDiv,
      `✅ Bulk send complete: ${data.sent} sent, ${data.failed} failed${simNote}`,
      'success',
    );

    // Full re-render to update all rows
    if (data.leads) {
      state.leads = data.leads;
      renderLeads(data.leads);
    }
    if (data.stats) updateKPI(data.stats);

  } catch (err) {
    showAlert(alertDiv, `Network error: ${err.message}`, 'error');
  } finally {
    btn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
      </svg>
      Send Bulk Email`;
    btn.disabled = false;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  DELETE LEAD
// ─────────────────────────────────────────────────────────────────────────────

async function deleteLead(leadId) {
  if (!confirm('Delete this lead? This cannot be undone.')) return;

  try {
    const res = await fetch(`${API}/api/leads/${leadId}`, { method: 'DELETE' });
    if (res.ok) {
      // Animate row removal
      const row = document.getElementById(`lead-row-${leadId}`);
      if (row) {
        row.style.transition = 'opacity .3s, transform .3s';
        row.style.opacity    = '0';
        row.style.transform  = 'translateX(20px)';
        setTimeout(() => row.remove(), 300);
      }
      state.leads = state.leads.filter(l => l.id !== leadId);
      document.getElementById('leads-count').textContent = state.leads.length;
      await loadStats();
    }
  } catch (err) {
    alert('Delete failed: ' + err.message);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  EXPORT CSV
// ─────────────────────────────────────────────────────────────────────────────

function exportCSV() {
  window.location.href = `${API}/api/export`;
}

// ─────────────────────────────────────────────────────────────────────────────
//  RESET DATABASE
// ─────────────────────────────────────────────────────────────────────────────

async function resetDatabase() {
  if (!confirm('Reset all leads and statistics? This cannot be undone.')) return;

  try {
    const res = await fetch(`${API}/api/reset`, { method: 'POST' });
    if (res.ok) {
      state.leads   = [];
      state.pdfPath = null;
      state.pdfUrl  = null;

      renderLeads([]);
      updateKPI({ total_leads: 0, contacted: 0, emails_sent: 0, failed: 0 });

      document.getElementById('pdf-name-display').innerHTML =
        '<span class="pdf-placeholder">No catalog uploaded</span>';
      document.getElementById('pdf-url-link').style.display = 'none';
      document.getElementById('progress-log').style.display  = 'none';
      document.getElementById('search-alert-area').innerHTML = '';
      document.getElementById('email-alert-area').innerHTML  = '';
    }
  } catch (err) {
    alert('Reset failed: ' + err.message);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  HELPERS
// ─────────────────────────────────────────────────────────────────────────────

function showAlert(container, message, type = 'info') {
  const icons = {
    success: '✅',
    error:   '⚠️',
    info:    '💬',
    warning: '⚡',
  };
  container.innerHTML = `
    <div class="alert alert-${type}">
      <span>${icons[type] || ''}</span>
      <span>${esc(message)}</span>
    </div>`;
}

function appendLog(container, text, cls) {
  const div = document.createElement('div');
  div.className  = `log-line ${cls}`;
  div.textContent = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function setLoading(btn, loading, text) {
  btn.disabled = loading;
  if (loading) {
    btn.innerHTML = `<span class="spinner"></span> ${esc(text)}`;
  } else {
    btn.textContent = text;
  }
}

function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}
