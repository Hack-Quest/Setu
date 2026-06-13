// ============================================================
// frontend/js/utils.js  — SETU Shared UI Utilities
// ============================================================

// ── Toast Notification ─────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed; top: 80px; right: 20px; z-index: 9999;
            display: flex; flex-direction: column; gap: 8px;
        `;
        document.body.appendChild(container);
    }

    const colors = {
        success: { bg: '#dcfce7', border: '#22c55e', text: '#15803d', icon: '✅' },
        error:   { bg: '#fee2e2', border: '#ef4444', text: '#b91c1c', icon: '❌' },
        warning: { bg: '#fef9c3', border: '#eab308', text: '#854d0e', icon: '⚠️' },
        info:    { bg: '#dbeafe', border: '#3b82f6', text: '#1e40af', icon: 'ℹ️' },
    };
    const c = colors[type] || colors.info;

    const toast = document.createElement('div');
    toast.style.cssText = `
        min-width: 280px; max-width: 380px;
        padding: 12px 16px; border-radius: 12px;
        background: ${c.bg}; border: 1px solid ${c.border};
        color: ${c.text}; font-size: 14px; font-weight: 500;
        font-family: 'Inter', sans-serif;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        display: flex; align-items: flex-start; gap: 10px;
        transition: opacity 0.3s ease, transform 0.3s ease;
        transform: translateX(0); opacity: 1;
    `;
    toast.innerHTML = `<span>${c.icon}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 350);
    }, duration);
}

// ── Auth Guards ────────────────────────────────────────────
function requireAuth(redirectTo = 'login.html') {
    if (!localStorage.getItem('auth_token')) {
        window.location.href = redirectTo;
        return false;
    }
    return true;
}

function logout(redirectTo = 'landing.html') {
    localStorage.clear();
    window.location.href = redirectTo;
}

// ── Google Forms ───────────────────────────────────────────
function openNeedForm()      { window.open(window.SETU_NEED_FORM_URL,      '_blank'); }
function openNGOForm()       { window.open(window.SETU_NGO_FORM_URL,       '_blank'); }
function openVolunteerForm() { window.open(window.SETU_VOLUNTEER_FORM_URL, '_blank'); }

// ── Severity Helpers ───────────────────────────────────────
const SEVERITY_COLORS = {
    critical: { bg: '#fee2e2', text: '#ef4444', border: '#fca5a5' },
    high:     { bg: '#ffedd5', text: '#f97316', border: '#fdba74' },
    medium:   { bg: '#fef9c3', text: '#ca8a04', border: '#fde047' },
    low:      { bg: '#dcfce7', text: '#16a34a', border: '#86efac' },
};

function severityBadgeHTML(severity) {
    const s = (severity || 'low').toLowerCase();
    const c = SEVERITY_COLORS[s] || SEVERITY_COLORS.low;
    return `<span style="
        background:${c.bg}; color:${c.text}; border:1px solid ${c.border};
        padding:2px 10px; border-radius:999px; font-size:11px; font-weight:700;
        text-transform:uppercase; letter-spacing:0.5px; white-space:nowrap;
    ">${s}</span>`;
}

// ── Loading Overlay ────────────────────────────────────────
function showLoading(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.style.display = 'flex';
}
function hideLoading(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.style.display = 'none';
}

// ── Format Date ────────────────────────────────────────────
function formatRelative(isoString) {
    if (!isoString) return 'Unknown time';
    try {
        const date = new Date(isoString);
        const diff = Math.floor((Date.now() - date) / 1000);
        if (diff < 60)   return `${diff}s ago`;
        if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
        return date.toLocaleDateString();
    } catch { return 'Unknown time'; }
}

// Expose all helpers globally
window.showToast       = showToast;
window.requireAuth     = requireAuth;
window.logout          = logout;
window.openNeedForm    = openNeedForm;
window.openNGOForm     = openNGOForm;
window.openVolunteerForm = openVolunteerForm;
window.severityBadgeHTML = severityBadgeHTML;
window.showLoading     = showLoading;
window.hideLoading     = hideLoading;
window.formatRelative  = formatRelative;
