// new_frontend/js/api.js
// NOTE: Read lazily inside request() so common.js has time to set the value first.
const getApiBaseUrl = () => window.SETU_API_BASE_URL || '';

class ApiService {
    /**
     * Centralized request handler with dynamic Token injection.
     */
    static async request(endpoint, options = {}) {
        const url = `${getApiBaseUrl()}${endpoint}`;
        const token = localStorage.getItem('auth_token');

        const headers = {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        };

        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }

        const config = { ...options, headers };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || data.message || `HTTP error! status: ${response.status}`);
            }
            return { ok: true, data };
        } catch (error) {
            console.error(`🚨 API Error on ${endpoint}:`, error);
            return { ok: false, error: error.message };
        }
    }

    static async login(data) { return this.request('/auth/login', { method: 'POST', body: JSON.stringify(data) }); }
    static async register(data) { return this.request('/auth/register', { method: 'POST', body: JSON.stringify(data) }); }
    static async getDashboard() { return this.request('/dashboard'); }
    static async getReports() { return this.request('/dashboard/reports'); }
    static async registerNGO(data) { return this.request('/ngo/register', { method: 'POST', body: JSON.stringify(data) }); }
    static async sendOtp(data) {
        return this.request('/auth/send-otp', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async verifyOtp(data) {
        return this.request('/auth/verify-otp', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    static async getStats() { return this.request('/stats'); }
    static async getHealth() { return this.request('/health'); }
    static async getVolunteerAssignments(volunteerId) { return this.request(`/assignment/volunteer/${volunteerId}`); }
    static async acceptNeed(needId) { return this.request(`/assignment/volunteer/${needId}`, { method: 'POST' }); }
    static async resolveAssignment(id, data) { return this.request(`/assignment/${id}/resolve`, { method: 'PATCH', body: JSON.stringify(data) }); }

    /**
     * Parallel fetch for NGO profile + global stats.
     */
    static async getNGODashboard(ngoId) {
        const response = await this.request(`/ngo/${ngoId}/dashboard`);
        if (!response.ok) {
            throw new Error(response.error || 'Unable to load NGO dashboard');
        }
        return response.data;
    }

    static async postNeed(data) {
        return this.request('/need', { method: 'POST', body: JSON.stringify(data) });
    }

    static async postVolunteer(data) {
        return this.request('/volunteer', { method: 'POST', body: JSON.stringify(data) });
    }

    static async runMatch()       { return this.request('/match'); }
    static async getVolunteers()  { return this.request('/volunteers'); }
    static async getNGOs()        { return this.request('/ngo/list'); }
}
window.ApiService = ApiService;
window.api = ApiService;