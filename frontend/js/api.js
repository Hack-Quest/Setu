// --- Global API Service ---
const API_BASE_URL = 'http://localhost:8000'; // Make sure uvicorn is running on port 8000

// Utility function to handle fetched responses
async function fetchWithConfig(endpoint, options = {}) {
    try {
        const token = localStorage.getItem('auth_token');
        const headers = {
            'Content-Type': 'application/json',
        };
        // Add Bearer token if it exists
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers,
            ...options
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP Error: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

const api = {
    // Auth endpoints
    login: async (userId, password) => {
        // Simply storing the password as the token since backend compares Bearer == SECRET_TOKEN
        localStorage.setItem('auth_user_id', userId);
        localStorage.setItem('auth_token', password);
        return { success: true };
    },
    
    logout: () => {
        localStorage.removeItem('auth_user_id');
        localStorage.removeItem('auth_token');
        window.location.href = "index.html";
    },

    // Webhook - Unauthenticated endpoint for SOS form
    submitSOS: async (formData) => {
        return fetchWithConfig('/webhook', {
            method: 'POST',
            body: JSON.stringify(formData)
        });
    },

    // Dashboard - Fetch telemetry
    getDashboardStats: async () => {
        return fetchWithConfig('/dashboard');
    },

    // Volunteer endpoints (authenticated)
    registerVolunteer: async (data) => {
        return fetchWithConfig('/volunteer', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    runMatchEngine: async () => {
        return fetchWithConfig('/match');
    },

    // Future placeholders
    assignUnits: async (incidentId) => {
        console.log(`Mock Assigning Units to: ${incidentId}`);
        return { success: true };
    }
};
