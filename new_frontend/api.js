/**
 * Centralized API Client
 * All requests include Authorization: Bearer hackathon-secret globally
 * Handles token storage and error handling
 */

const API_BASE_URL = 'http://localhost:8000';
const FIXED_TOKEN = 'hackathon-secret';

class APIClient {
  constructor() {
    this.token = FIXED_TOKEN;
    this.baseURL = API_BASE_URL;
  }

  /**
   * Generic fetch wrapper with built-in auth header
   */
  async request(endpoint, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.token}`,
      ...options.headers,
    };

    const config = {
      ...options,
      headers,
    };

    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, config);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const error = new Error(errorData.detail || `HTTP ${response.status}`);
        error.statusCode = response.status;
        throw error;
      }

      return await response.json();
    } catch (error) {
      console.error(`API Error (${endpoint}):`, error.message);
      throw error;
    }
  }

  /**
   * POST /need - Submit an emergency need
   */
  async submitNeed(payload) {
    return this.request('/need', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /**
   * POST /volunteer - Register a volunteer
   */
  async registerVolunteer(payload) {
    return this.request('/volunteer', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /**
   * GET /match - Run the match engine
   */
  async runMatchEngine() {
    return this.request('/match', {
      method: 'GET',
    });
  }

  /**
   * GET /dashboard - Get dashboard statistics (no auth required by server, but we include it anyway)
   */
  async getDashboardStats() {
    return this.request('/dashboard', {
      method: 'GET',
    });
  }

  /**
   * Health check (no auth)
   */
  async health() {
    return fetch(`${this.baseURL}/health`)
      .then(r => r.json())
      .catch(() => ({ status: 'offline' }));
  }
}

// Global API instance
const api = new APIClient();
