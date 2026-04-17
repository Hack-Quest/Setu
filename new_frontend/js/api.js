const API_BASE_URL = 'http://127.0.0.1:8000';
const AUTH_TOKEN = 'hackathon-secret';

class ApiService {
    static async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${AUTH_TOKEN}`,
            ...(options.headers || {})
        };

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || data.message || `HTTP error! status: ${response.status}`);
            }
            
            return { ok: true, data };
        } catch (error) {
            console.error(`API Error on ${endpoint}:`, error);
            return { ok: false, error: error.message };
        }
    }

    static async getDashboard() {
        return this.request('/dashboard');
    }

    static async getReports() {
        return this.request('/dashboard/reports');
    }

    static async postNeed(data) {
        return this.request('/need', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async postVolunteer(data) {
        return this.request('/volunteer', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async runMatch() {
        return this.request('/match');
    }
}
window.ApiService = ApiService;
