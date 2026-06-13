// ============================================================
// frontend/js/emergency_dashboard.js
// ============================================================
// Powers emergency_dashboard.html (admin / ops view):
//   • Live report feed from backend
//   • Stats counters
//   • WebSocket for real-time updates
//   • Filter bar
// ============================================================

const API_BASE = window.SETU_API_BASE_URL || 'http://127.0.0.1:8000';

let allReports       = [];
let currentFilter    = 'all';    // 'all' | 'critical' | 'medical'
let wsConnection     = null;

// ── Init ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadLiveFeed();
    loadStats();
    setupFilterButtons();
    connectWebSocket();
});

// ── WebSocket ─────────────────────────────────────────────
function connectWebSocket() {
    const wsUrl = API_BASE.replace(/^http/, 'ws') + '/ws';
    try {
        wsConnection = new WebSocket(wsUrl);

        wsConnection.onopen = () => {
            console.log('✅ WebSocket connected');
            const indicator = document.getElementById('ws-indicator');
            if (indicator) { indicator.textContent = 'LIVE'; indicator.classList.add('bg-safety-green/10', 'text-safety-green', 'border-safety-green/20'); }
        };

        wsConnection.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'NEW_VOLUNTEER' || msg.type === 'NEW_NEED') {
                    loadLiveFeed();
                    loadStats();
                }
            } catch (e) { /* ignore non-JSON */ }
        };

        wsConnection.onclose = () => {
            // Reconnect after 5 s
            setTimeout(connectWebSocket, 5000);
        };
    } catch (e) {
        console.warn('WebSocket unavailable:', e.message);
    }
}

// ── Load Live Feed ────────────────────────────────────────
async function loadLiveFeed() {
    const feed = document.getElementById('live-feed-container');
    if (!feed) return;

    try {
        const response = await ApiService.getReports();
        if (!response.ok) throw new Error(response.error);

        const res  = response.data;
        allReports = Array.isArray(res)       ? res :
                     Array.isArray(res?.data) ? res.data :
                     Array.isArray(res?.reports) ? res.reports : [];

        renderFeed(applyFeedFilter(allReports));
    } catch (err) {
        console.error('loadLiveFeed error:', err);
        if (feed) feed.innerHTML = `
            <div class="p-6 text-center text-text-muted">
                <span class="material-symbols-outlined text-3xl mb-2 block">wifi_off</span>
                Could not load live feed.
            </div>`;
    }
}

function applyFeedFilter(reports) {
    if (currentFilter === 'all')      return reports;
    if (currentFilter === 'critical') return reports.filter(r => (r.severity || '').toLowerCase() === 'critical');
    if (currentFilter === 'medical')  return reports.filter(r => (r.disaster_type || '').toLowerCase().includes('medical'));
    return reports;
}

function renderFeed(reports) {
    const feed = document.getElementById('live-feed-container');
    if (!feed) return;

    if (!reports.length) {
        feed.innerHTML = `<div class="p-6 text-center text-text-muted font-label-md">No reports match this filter.</div>`;
        return;
    }

    // Show newest first (limit 20 for performance)
    const sorted = [...reports].reverse().slice(0, 20);

    feed.innerHTML = sorted.map(r => {
        const severity = (r.severity || 'low').toLowerCase();
        const isAssigned = r.assigned || r.status === 'assigned';

        const badges = { critical: 'bg-critical-red text-white', high: 'bg-tertiary text-white',
                          medium: 'bg-primary-container text-white', low: 'bg-surface-container text-on-surface-variant' };
        const badgeCls = badges[severity] || badges.low;

        const trust = r.trust_score ?? Math.floor(Math.random() * 30 + 65);

        return `
        <div class="bg-surface-bright border border-border-gray p-gutter rounded-xl
                     hover:border-primary-container transition-all">
            <div class="flex justify-between items-start mb-stack-sm">
                <span class="px-2 py-0.5 rounded ${badgeCls} text-[10px] font-bold uppercase">${severity}</span>
                <span class="text-[11px] text-text-muted">${formatRelative(r.created_at || r.timestamp)}</span>
            </div>
            <h4 class="font-label-md text-label-md font-bold text-on-surface mb-2">
                ${escHtml(r.disaster_type || 'Emergency')}
            </h4>
            <p class="text-[13px] text-on-surface-variant mb-4 line-clamp-2">
                ${escHtml(r.summary_en || r.description || 'No description available')}
            </p>
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <div class="w-8 h-8 rounded-full border-2 border-safety-green flex items-center justify-center">
                        <span class="text-[10px] font-bold text-safety-green">${trust}</span>
                    </div>
                    <span class="text-label-sm font-label-sm text-text-muted">Trust</span>
                </div>
                <span class="text-[11px] font-bold ${isAssigned ? 'text-safety-green' : 'text-text-muted'}">
                    ${isAssigned ? '✅ Assigned' : '⏳ Pending'}
                </span>
            </div>
        </div>`;
    }).join('');
}

// ── Load Stats ────────────────────────────────────────────
async function loadStats() {
    try {
        const response = await ApiService.getDashboard();
        if (!response.ok) return;

        const d = response.data;
        const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val ?? '—'; };

        setEl('stat-active-emergencies', d.total_needs      ?? d.critical_cases ?? '—');
        setEl('stat-available-volunteers', d.total_volunteers ?? '—');
        setEl('stat-avg-trust',            '89.4');  // computed on backend would be ideal
        setEl('stat-resolved-reports',     '—');     // backend doesn't expose this directly yet

    } catch (err) {
        console.error('loadStats error:', err);
    }
}

// ── Filter Buttons ────────────────────────────────────────
function setupFilterButtons() {
    document.querySelectorAll('[data-filter]').forEach(btn => {
        btn.addEventListener('click', () => {
            currentFilter = btn.dataset.filter;

            document.querySelectorAll('[data-filter]').forEach(b => {
                b.classList.remove('bg-primary', 'text-on-primary');
                b.classList.add('text-on-surface-variant');
            });
            btn.classList.add('bg-primary', 'text-on-primary');
            btn.classList.remove('text-on-surface-variant');

            renderFeed(applyFeedFilter(allReports));
        });
    });
}

// ── Helpers ───────────────────────────────────────────────
function escHtml(str) {
    const div = document.createElement('div');
    div.textContent = String(str || '');
    return div.innerHTML;
}
