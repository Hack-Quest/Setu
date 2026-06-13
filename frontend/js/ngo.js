// ============================================================
// frontend/js/ngo.js  — SETU NGO Dashboard Logic
// ============================================================
// Powers ngo.html:
//   • Loads NGO-specific dashboard: stats, assignments, team
//   • Run matching engine
//   • Resolve assignments
//   • Bulk volunteer upload (Excel via SheetJS)
// ============================================================

requireAuth('login.html');

const ngoId = localStorage.getItem('ngo_id');

// ── Init on load ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    updateUserGreeting();
    loadNGODashboard();
    checkHealth();
    setupEventListeners();
});

function updateUserGreeting() {
    const name = localStorage.getItem('name') || 'NGO Admin';
    const greetEl = document.getElementById('ngo-name-display');
    if (greetEl) greetEl.textContent = name;
}

function setupEventListeners() {
    const runBtn = document.getElementById('runMatchBtn');
    if (runBtn) runBtn.addEventListener('click', runMatchingEngine);

    const excelInput = document.getElementById('excelInput');
    if (excelInput) excelInput.addEventListener('change', handleExcelUpload);

    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) logoutBtn.addEventListener('click', () => logout('landing.html'));
}

// ── Health Check ─────────────────────────────────────────
async function checkHealth() {
    const el = document.getElementById('healthStatus');
    if (!el) return;
    const response = await ApiService.getHealth();
    if (response.ok && response.data?.status === 'ok') {
        el.textContent = '● Backend Online';
        el.style.color = '#22c55e';
    } else {
        el.textContent = '● Backend Offline';
        el.style.color = '#ef4444';
    }
}

// ── Load NGO Dashboard ─────────────────────────────────────
async function loadNGODashboard() {
    if (!ngoId) {
        showToast('NGO ID not found. Please login again.', 'error');
        return;
    }

    try {
        const response = await ApiService.getNGODashboard(ngoId);
        if (!response || !response.ok) throw new Error(response?.error || 'No data returned');

        // ApiService.request wraps the payload in { ok, data } — unwrap here
        const payload = response.data || {};
        const { ngo, stats, active_assignments, managed_volunteers } = payload;

        // Update stats cards
        updateStatCards(stats, active_assignments?.length || 0);

        // Render assignments table
        renderAssignments(active_assignments || []);

        // Render team list
        renderTeamMembers(managed_volunteers || []);

        // Update NGO name in sidebar
        if (ngo) {
            const nameEl = document.getElementById('ngo-org-name');
            if (nameEl) nameEl.textContent = ngo.ngo_name || ngo.organization_name || 'Your NGO';
        }

    } catch (err) {
        console.error('loadNGODashboard error:', err);
        showToast('Failed to load dashboard. Retrying in 10s…', 'error');
        setTimeout(loadNGODashboard, 10000);
    }
}

// ── Update Stat Cards ─────────────────────────────────────
function updateStatCards(stats, reportCount) {
    const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val ?? '—';
    };
    set('stat-verified-volunteers', stats?.managed_volunteers ?? '—');
    set('stat-active-missions',     stats?.active_assignments ?? '—');
    set('stat-verified-professionals', stats?.verified_professionals ?? '—');
    set('stat-open-reports',        reportCount);
}

// ── Render Assignments Table ──────────────────────────────
const SEVERITY_ORDER = { critical: 0, 'very high': 1, high: 2, medium: 3, low: 4 };

function renderAssignments(assignments) {
    const container = document.getElementById('assignments-list');
    if (!container) return;

    if (!assignments.length) {
        container.innerHTML = `
            <div class="flex items-center justify-center py-12 text-on-surface-variant">
                <span class="material-symbols-outlined mr-3">check_circle</span>
                No active assignments right now.
            </div>`;
        return;
    }

    // Sort by priority
    assignments.sort((a, b) =>
        (SEVERITY_ORDER[(a.priority || 'low').toLowerCase()] ?? 5) -
        (SEVERITY_ORDER[(b.priority || 'low').toLowerCase()] ?? 5)
    );

    container.innerHTML = assignments.map(a => {
        const priority = (a.priority || 'low').toLowerCase();
        const priorityColors = {
            critical: 'bg-critical-red text-white',
            high:     'bg-tertiary text-white',
            medium:   'bg-primary-container text-white',
            low:      'bg-surface-container text-on-surface-variant',
        };
        const badgeCls = priorityColors[priority] || priorityColors.low;
        const isAssigned = a.status && a.status.toLowerCase() !== 'open';

        return `
        <div class="p-6 hover:bg-surface-container-low transition-colors" data-assignment-id="${a.id}">
            <div class="flex items-start gap-4">
                <div class="flex-shrink-0 mt-1">
                    <span class="material-symbols-outlined text-primary p-2 bg-surface-container rounded-full">
                        ${priority === 'critical' ? 'warning' : 'assignment'}
                    </span>
                </div>
                <div class="flex-grow">
                    <div class="flex justify-between items-start mb-2 flex-wrap gap-2">
                        <div>
                            <h4 class="font-body-lg font-bold text-text-main">${escHtml(a.title || 'Emergency Report')}</h4>
                            <p class="text-label-sm text-text-muted">${escHtml(a.location || 'Location pending')} • Lead: ${escHtml(a.lead || 'Unassigned')}</p>
                        </div>
                        <span class="px-3 py-1 ${badgeCls} font-label-sm text-label-sm rounded-lg">${priority}</span>
                    </div>
                    <div class="flex items-center justify-between mt-4 flex-wrap gap-3">
                        <span class="text-label-sm ${isAssigned ? 'text-safety-green' : 'text-text-muted'}">
                            ${isAssigned ? '✅ Assigned' : '⏳ Pending'}
                        </span>
                        <div class="flex gap-3">
                            ${!isAssigned && a.id ? `
                            <button
                                onclick="resolveAssignment('${escHtml(a.id)}')"
                                class="bg-primary text-on-primary px-4 py-1.5 rounded-lg font-label-md text-label-md hover:opacity-90 transition-all">
                                Mark Resolved
                            </button>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
    }).join('<div class="border-t border-border-gray"></div>');
}

// ── Render Team Members ───────────────────────────────────
function renderTeamMembers(volunteers) {
    const container = document.getElementById('team-list');
    if (!container) return;

    if (!volunteers.length) {
        container.innerHTML = `<p class="text-center text-text-muted py-6">No team members found.</p>`;
        return;
    }

    container.innerHTML = volunteers.map(v => {
        const isAvailable = v.status === 'On Call' || v.available === true;
        const statusCls   = isAvailable ? 'text-safety-green bg-green-50' : 'text-primary bg-blue-50';
        const statusDot   = isAvailable ? 'bg-safety-green' : 'bg-primary';
        const statusText  = isAvailable ? 'Available' : 'Engaged';
        const skills      = Array.isArray(v.skills) ? v.skills.slice(0, 2).join(' • ') : v.role || 'Volunteer';
        const initials    = (v.name || 'V').charAt(0).toUpperCase();

        return `
        <div class="flex items-center justify-between p-3 rounded-lg hover:bg-surface-container-low
                    border border-transparent hover:border-border-gray transition-all">
            <div class="flex items-center gap-3">
                <div class="relative">
                    <div class="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center
                                text-primary font-bold text-sm">
                        ${initials}
                    </div>
                    <div class="absolute -bottom-0.5 -right-0.5 w-3 h-3 ${statusDot}
                                border-2 border-surface-container-lowest rounded-full"></div>
                </div>
                <div>
                    <p class="font-label-md text-label-md text-text-main font-bold">${escHtml(v.name || 'Volunteer')}</p>
                    <p class="text-[12px] text-text-muted">${escHtml(skills)}${v.zone ? ` • ${escHtml(v.zone)}` : ''}</p>
                </div>
            </div>
            <span class="font-label-sm text-label-sm ${statusCls} px-2 py-0.5 rounded">${statusText}</span>
        </div>`;
    }).join('');
}

// ── Resolve Assignment ────────────────────────────────────
async function resolveAssignment(assignmentId) {
    if (!confirm('Mark this assignment as resolved?')) return;

    const response = await ApiService.resolveAssignment(assignmentId, {});
    if (response.ok) {
        showToast('Assignment resolved. Volunteer is now available.', 'success');
        loadNGODashboard(); // refresh
    } else {
        showToast(response.error || 'Could not resolve assignment.', 'error');
    }
}

// ── Run Matching Engine ────────────────────────────────────
async function runMatchingEngine() {
    const btn = document.getElementById('runMatchBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Running…'; }

    const response = await ApiService.runMatch();
    if (btn) { btn.disabled = false; btn.textContent = 'Run Matching Engine'; }

    if (!response.ok) {
        showToast(response.error || 'Matching engine failed.', 'error');
        return;
    }

    const matches   = response.data?.matches || [];
    const assigned  = matches.filter(m => m.status === 'assigned').length;
    const unmatched = matches.length - assigned;
    showToast(`Matching complete! ✅ Assigned: ${assigned} | Unmatched: ${unmatched}`, 'success');
    loadNGODashboard();
}

// ── Bulk Excel Upload ─────────────────────────────────────
async function handleExcelUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (typeof XLSX === 'undefined') {
        showToast('SheetJS not loaded. Reload the page.', 'error');
        return;
    }

    const statusEl = document.getElementById('uploadStatus');
    if (statusEl) { statusEl.textContent = 'Parsing file…'; statusEl.style.color = '#ca8a04'; }

    try {
        const buf      = await file.arrayBuffer();
        const wb       = XLSX.read(buf, { type: 'array' });
        const ws       = wb.Sheets[wb.SheetNames[0]];
        const rows     = XLSX.utils.sheet_to_json(ws, { defval: '' });

        if (!rows.length) {
            if (statusEl) { statusEl.textContent = '⚠️ No rows found.'; statusEl.style.color = '#ef4444'; }
            return;
        }

        if (statusEl) statusEl.textContent = `Found ${rows.length} volunteers. Uploading…`;

        let ok = 0, fail = 0;
        for (const row of rows) {
            const rawSkills = row['skills'] || row['Skills'] || '';
            const skills    = Array.isArray(rawSkills)
                ? rawSkills
                : String(rawSkills).split(',').map(s => s.trim()).filter(Boolean);

            const payload = {
                name:     row['name']     || row['Name']     || 'Unknown',
                phone:    String(row['phone'] || row['Phone'] || '0000000000'),
                location: row['location'] || row['Location'] || '',
                lat:      parseFloat(row['lat']  || row['Latitude']  || 0),
                lng:      parseFloat(row['lng']  || row['Longitude'] || 0),
                skills,
                email:    row['email'] || row['Email'] || `bulk-${Date.now()}@ngo.internal`,
                password: 'BulkUpload!1',
                ngo_id:   row['ngo_id'] || row['NGO ID'] || ngoId || null,
            };

            try {
                const res = await ApiService.postVolunteer(payload);
                res.ok ? ok++ : fail++;
            } catch { fail++; }
        }

        const msg = `✅ Uploaded: ${ok} | Failed: ${fail}`;
        if (statusEl) { statusEl.textContent = msg; statusEl.style.color = ok > 0 ? '#16a34a' : '#ef4444'; }
        showToast(msg, ok > 0 ? 'success' : 'error');
        loadNGODashboard();

    } catch (err) {
        console.error('Excel upload error:', err);
        if (statusEl) { statusEl.textContent = '❌ Failed to parse file.'; statusEl.style.color = '#ef4444'; }
        showToast('Failed to parse Excel file.', 'error');
    }

    event.target.value = '';
}

// ── Helpers ───────────────────────────────────────────────
function escHtml(str) {
    const div = document.createElement('div');
    div.textContent = String(str || '');
    return div.innerHTML;
}

// Expose for inline onclick=""
window.resolveAssignment  = resolveAssignment;
window.runMatchingEngine  = runMatchingEngine;
window.handleExcelUpload  = handleExcelUpload;
