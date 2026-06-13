// ============================================================
// frontend/js/volunteer.js  — SETU Volunteer Dashboard Logic
// ============================================================
// Powers volunteer.html:
//   • Loads volunteer profile, current assignment, stats
//   • Mark mission as resolved
//   • On-duty toggle
//   • Live broadcast feed
// ============================================================

requireAuth('login.html');

const volunteerId = localStorage.getItem('volunteer_id');

// Safety check: invalid volunteer ID
if (!volunteerId || volunteerId === 'null' || volunteerId === 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        document.body.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:center;min-height:100vh;
                        font-family:'Inter',sans-serif;background:#faf8ff;flex-direction:column;gap:16px;">
                <h2 style="color:#1e293b;font-size:24px;">Session Error</h2>
                <p style="color:#64748b;">Could not retrieve your volunteer ID.</p>
                <a href="login.html" style="background:#004ac6;color:#fff;padding:12px 24px;
                    border-radius:8px;text-decoration:none;font-weight:600;">Login Again</a>
            </div>`;
    });
    throw new Error('Halting: invalid volunteer ID');
}

// ── Init ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadProfile();
    loadAssignments();
    setupEventListeners();
});

function loadProfile() {
    const name = localStorage.getItem('name') || 'Volunteer';
    const greetEl = document.getElementById('volunteer-greeting');
    const nameEl  = document.getElementById('volunteer-name');
    if (greetEl) greetEl.textContent = `Good day, ${name}`;
    if (nameEl)  nameEl.textContent  = name;
}

function setupEventListeners() {
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) logoutBtn.addEventListener('click', () => logout('landing.html'));

    const dutyToggle = document.getElementById('dutyToggle');
    if (dutyToggle) {
        dutyToggle.addEventListener('change', () => {
            const label = document.getElementById('dutyLabel');
            if (label) label.textContent = dutyToggle.checked ? 'You are On-Duty' : 'You are Off-Duty';
        });
    }

    const resolveBtn = document.getElementById('markResolvedBtn');
    if (resolveBtn) resolveBtn.addEventListener('click', markCurrentResolved);
}

// ── Load Assignments ──────────────────────────────────────
let currentAssignmentId = null;
let currentNeedId       = null;

async function loadAssignments() {
    const spinner = document.getElementById('assignments-loading');
    if (spinner) spinner.style.display = 'flex';

    try {
        const response = await ApiService.getVolunteerAssignments(volunteerId);

        if (!response.ok) throw new Error(response.error);

        // Backend returns array directly (not wrapped in {data:})
        const assignments = Array.isArray(response.data) ? response.data :
                            Array.isArray(response.data?.data) ? response.data.data : [];

        renderActiveMission(assignments);
        updatePersonalStats(assignments);

    } catch (err) {
        console.error('loadAssignments error:', err);
        showToast('Failed to load assignments.', 'error');
        const section = document.getElementById('active-mission-section');
        if (section) section.innerHTML = `
            <div class="p-6 text-center text-text-muted">
                <span class="material-symbols-outlined text-4xl mb-2 block">wifi_off</span>
                Could not connect to backend. Check your connection.
            </div>`;
    } finally {
        if (spinner) spinner.style.display = 'none';
    }
}

// ── Render Active Mission ─────────────────────────────────
function renderActiveMission(assignments) {
    const section = document.getElementById('active-mission-section');
    if (!section) return;

    // Pick the first unresolved assignment
    const active = assignments.find(a =>
        !a.resolved_at && a.status !== 'resolved'
    );

    if (!active) {
        section.innerHTML = `
            <div class="p-6 text-center text-text-muted">
                <span class="material-symbols-outlined text-4xl mb-2 block text-safety-green">task_alt</span>
                <p class="font-label-md text-label-md">No active assignments. You're available!</p>
            </div>`;
        return;
    }

    currentAssignmentId = active.assignment_id || active.id;
    currentNeedId       = active.id;

    const severity      = (active.severity || 'low').toLowerCase();
    const sevColors     = {
        critical: 'bg-critical-red text-white animate-pulse',
        high:     'bg-tertiary text-white',
        medium:   'bg-primary-container text-white',
        low:      'bg-surface-container text-on-surface-variant',
    };
    const sevCls = sevColors[severity] || sevColors.low;

    section.innerHTML = `
        <div class="p-6 border-b border-border-gray flex justify-between items-center flex-wrap gap-3">
            <div class="flex items-center gap-3">
                <span class="p-2 bg-error-container text-error rounded-lg">
                    <span class="material-symbols-outlined" style="font-variation-settings:'FILL' 1">emergency</span>
                </span>
                <div>
                    <h3 class="font-headline-md text-headline-md">Active Mission</h3>
                    <p class="text-on-surface-variant font-label-sm text-label-sm uppercase tracking-wider">
                        ID: ${escHtml(active.id || '—')}
                    </p>
                </div>
            </div>
            <span class="px-3 py-1 ${sevCls} font-label-sm text-label-sm rounded-full">
                ${severity.toUpperCase()} SEVERITY
            </span>
        </div>
        <div class="p-6 grid grid-cols-1 md:grid-cols-2 gap-stack-lg">
            <div class="space-y-4">
                <div>
                    <label class="font-label-sm text-label-sm text-text-muted block mb-1">LOCATION</label>
                    <p class="font-body-lg text-body-lg font-semibold flex items-center gap-2">
                        <span class="material-symbols-outlined text-primary">location_on</span>
                        ${escHtml(active.location_text || active.location || active.area || 'Location pending')}
                    </p>
                </div>
                <div>
                    <label class="font-label-sm text-label-sm text-text-muted block mb-1">TASK DESCRIPTION</label>
                    <p class="font-body-md text-body-md text-on-surface-variant">
                        ${escHtml(active.summary_en || active.description || 'No description available.')}
                    </p>
                </div>
                <div>
                    <label class="font-label-sm text-label-sm text-text-muted block mb-1">DISASTER TYPE</label>
                    <p class="font-label-md text-label-md font-bold">${escHtml(active.disaster_type || 'Emergency')}</p>
                </div>
                <div class="pt-4 flex gap-3 flex-wrap">
                    <button class="flex-1 bg-primary text-white font-label-md text-label-md py-3 rounded-lg
                                   hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                            onclick="window.open('https://maps.google.com/?q=${encodeURIComponent(active.location_text || active.location || '')}','_blank')">
                        <span class="material-symbols-outlined">directions</span>
                        Navigate
                    </button>
                    <button id="markResolvedBtn"
                            class="flex-1 border border-safety-green text-safety-green font-label-md text-label-md
                                   py-3 rounded-lg hover:bg-safety-green hover:text-white transition-all
                                   flex items-center justify-center gap-2"
                            onclick="markCurrentResolved()">
                        <span class="material-symbols-outlined">check_circle</span>
                        Mark as Resolved
                    </button>
                </div>
            </div>
            <div class="relative rounded-xl overflow-hidden border border-border-gray bg-surface-variant
                        h-64 md:h-full min-h-[200px] flex items-center justify-center">
                <div class="text-center text-text-muted p-6">
                    <span class="material-symbols-outlined text-5xl mb-3 block text-primary/30">map</span>
                    <p class="font-label-md text-label-md">
                        ${escHtml(active.location_text || active.location || 'Location data loading')}
                    </p>
                    ${active.lat && active.lng ? `
                    <p class="text-label-sm text-text-muted mt-1">
                        ${parseFloat(active.lat).toFixed(4)}, ${parseFloat(active.lng).toFixed(4)}
                    </p>` : ''}
                </div>
            </div>
        </div>`;
}

// ── Update Personal Stats ─────────────────────────────────
function updatePersonalStats(assignments) {
    const resolved = assignments.filter(a => a.status === 'resolved' || a.resolved_at).length;
    const trust    = 88; // Would come from volunteer profile

    const setEl = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };
    setEl('stat-missions-completed', resolved);
    setEl('stat-trust-score',        trust);

    const trustBar = document.getElementById('trust-score-bar');
    if (trustBar) trustBar.style.width = `${trust}%`;
}

// ── Mark Resolved ─────────────────────────────────────────
async function markCurrentResolved() {
    if (!currentAssignmentId) {
        showToast('No active assignment to resolve.', 'warning');
        return;
    }
    if (!confirm('Mark this mission as resolved?')) return;

    const btn = document.getElementById('markResolvedBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Resolving…'; }

    const response = await ApiService.resolveAssignment(currentAssignmentId, {});
    if (response.ok) {
        showToast('Mission resolved! Thank you for your service. 🙏', 'success');
        currentAssignmentId = null;
        setTimeout(loadAssignments, 1000);
    } else {
        showToast(response.error || 'Failed to resolve assignment.', 'error');
        if (btn) { btn.disabled = false; btn.textContent = 'Mark as Resolved'; }
    }
}

// ── Helpers ───────────────────────────────────────────────
function escHtml(str) {
    const div = document.createElement('div');
    div.textContent = String(str || '');
    return div.innerHTML;
}

// Expose for inline onclick
window.markCurrentResolved = markCurrentResolved;
