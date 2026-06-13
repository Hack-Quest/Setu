// ============================================================
// frontend/js/api.js  — SETU Centralized API Service
// ============================================================
// All HTTP calls to the FastAPI backend go through this class.
// Reads SETU_API_BASE_URL lazily so config.js can set it first.
// ============================================================

const _getBase = () => window.SETU_API_BASE_URL || 'http://127.0.0.1:8000';

class ApiService {
    /**
     * Core request wrapper.
     * Injects Authorization header from localStorage when present.
     */
    static async request(endpoint, options = {}) {
        const url = `${_getBase()}${endpoint}`;
        const token = localStorage.getItem('auth_token');

        const headers = {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        try {
            const response = await fetch(url, { ...options, headers });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || data.error || data.message || `HTTP ${response.status}`);
            }
            return { ok: true, data };
        } catch (err) {
            console.error(`🚨 API [${endpoint}]:`, err.message);
            return { ok: false, error: err.message };
        }
    }

    // ── Auth ──────────────────────────────────────────────────
    static sendOtp(data)    { return this.request('/auth/send-otp',    { method: 'POST', body: JSON.stringify(data) }); }
    static verifyOtp(data)  { return this.request('/auth/verify-otp',  { method: 'POST', body: JSON.stringify(data) }); }
    static login(data)      { return this.request('/auth/login',        { method: 'POST', body: JSON.stringify(data) }); }
    static register(data)   { return this.request('/auth/register',     { method: 'POST', body: JSON.stringify(data) }); }

    // ── Dashboard / Reports ───────────────────────────────────
    static getDashboard()   { return this.request('/dashboard'); }
    static getReports()     { return this.request('/dashboard/reports'); }
    static getStats()       { return this.request('/stats'); }
    static getHealth()      { return this.request('/health'); }

    // ── NGO ───────────────────────────────────────────────────
    static getNGOs()                { return this.request('/ngo/list'); }
    static getNGODashboard(ngoId)   { return this.request(`/ngo/${ngoId}/dashboard`); }
    static registerNGO(data)        { return this.request('/ngo/register', { method: 'POST', body: JSON.stringify(data) }); }

    // ── Volunteers ────────────────────────────────────────────
    static getVolunteers()          { return this.request('/volunteers'); }
    static postVolunteer(data)      { return this.request('/volunteer',  { method: 'POST', body: JSON.stringify(data) }); }
    static getVolunteerAssignments(id) { return this.request(`/assignment/volunteer/${id}`); }

    // ── Assignments ───────────────────────────────────────────
    static acceptNeed(needId)        { return this.request(`/assignment/volunteer/${needId}`, { method: 'POST' }); }
    static resolveAssignment(id, d)  { return this.request(`/assignment/${id}/resolve`,       { method: 'PATCH', body: JSON.stringify(d) }); }

    // ── Matching Engine ───────────────────────────────────────
    static runMatch()  { return this.request('/match'); }

    // ── Needs / Webhook ───────────────────────────────────────
    static postNeed(data) { return this.request('/need', { method: 'POST', body: JSON.stringify(data) }); }
}

// Expose globally for inline HTML onclick handlers
window.ApiService = ApiService;
window.api        = ApiService;
