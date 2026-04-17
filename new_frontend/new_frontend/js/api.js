/**
 * Centralized API client for the new frontend.
 *
 * Existing volunteer/report helpers still use the live backend when needed,
 * while NGO registration and dashboard data are mocked in localStorage so the
 * new UI can be exercised without backend changes.
 */

const API_BASE_URL = 'http://localhost:8000';
const FIXED_TOKEN = 'hackathon-secret';
const NGO_STORE_KEY = 'setu_mock_ngo_store';
const ACTIVE_NGO_KEY = 'setu_active_ngo_id';

const DEFAULT_NGO_STORE = {
    'ngo-hope-horizon': {
        ngo: {
            id: 'ngo-hope-horizon',
            name: 'Hope Horizon Trust',
            reg_number: 'NGO-2026-001',
            coverage_area: 'North river corridor and adjacent shelter clusters',
            radius: 24,
            verified: true,
            registered_at: '2026-04-12T08:30:00.000Z'
        },
        active_assignments: [
            {
                id: 'asg-2041',
                title: 'Flood shelter intake support',
                location: 'Riverside Ward 12',
                priority: 'High',
                status: 'In progress',
                eta: '45 min',
                lead: 'Dr. Maya Rao'
            },
            {
                id: 'asg-2042',
                title: 'Medical triage checkpoint',
                location: 'Central Relief Camp',
                priority: 'Critical',
                status: 'Dispatch queued',
                eta: '18 min',
                lead: 'Aman Verma'
            }
        ],
        managed_volunteers: [
            {
                id: 'vol-301',
                name: 'Dr. Maya Rao',
                role: 'Medical Coordinator',
                zone: 'Ward 12',
                status: 'Available',
                skills: ['Medical', 'Triage', 'Assessment'],
                ngo_id: 'ngo-hope-horizon'
            },
            {
                id: 'vol-302',
                name: 'Kabir Singh',
                role: 'Logistics Lead',
                zone: 'Depot B',
                status: 'On Call',
                skills: ['Logistics', 'Supply'],
                ngo_id: 'ngo-hope-horizon'
            },
            {
                id: 'vol-303',
                name: 'Asha Nair',
                role: 'Community Volunteer',
                zone: 'Sector 3',
                status: 'Available',
                skills: ['Communications', 'Coordination']
            }
        ]
    },
    'ngo-safeline-response': {
        ngo: {
            id: 'ngo-safeline-response',
            name: 'SafeLine Response Network',
            reg_number: 'NGO-2026-014',
            coverage_area: 'South district shelters and transit hubs',
            radius: 18,
            verified: false,
            registered_at: '2026-04-14T11:15:00.000Z'
        },
        active_assignments: [
            {
                id: 'asg-2111',
                title: 'Food parcel distribution',
                location: 'Transit Hub Alpha',
                priority: 'Medium',
                status: 'Assigned',
                eta: '22 min',
                lead: 'Neha Kapoor'
            }
        ],
        managed_volunteers: [
            {
                id: 'vol-401',
                name: 'Neha Kapoor',
                role: 'Operations Lead',
                zone: 'Transit Hub Alpha',
                status: 'Available',
                skills: ['Operations', 'Dispatch'],
                ngo_id: 'ngo-safeline-response'
            },
            {
                id: 'vol-402',
                name: 'Rohan Das',
                role: 'Field Volunteer',
                zone: 'Transit Hub Bravo',
                status: 'Available',
                skills: ['Shelter Support', 'Intake']
            }
        ]
    }
};

class APIClient {
    constructor() {
        this.token = FIXED_TOKEN;
        this.baseURL = API_BASE_URL;
    }

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

    async submitNeed(payload) {
        return this.request('/need', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    }

    async registerVolunteer(payload) {
        return this.request('/volunteer', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    }

    async runMatchEngine() {
        return this.request('/match', {
            method: 'GET',
        });
    }

    async getDashboardStats() {
        return this.request('/dashboard', {
            method: 'GET',
        });
    }

    async registerNGO(data) {
        const store = this.readMockStore();
        const normalizedNgo = this.buildNgoRecord(data);
        store[normalizedNgo.id] = this.buildStarterDashboard(normalizedNgo);
        this.writeMockStore(store);
        this.setActiveNgoId(normalizedNgo.id);

        return this.delay({
            message: 'NGO registered successfully',
            ngo: normalizedNgo,
            active_assignments: store[normalizedNgo.id].active_assignments,
            managed_volunteers: store[normalizedNgo.id].managed_volunteers
        });
    }

    async getNGODashboard(ngoId) {
        const store = this.readMockStore();
        const storeKeys = Object.keys(store);
        if (storeKeys.length === 0) {
            const fallbackNgo = this.buildNgoRecord({
                name: 'New NGO',
                reg_number: 'NGO-0000-000',
                coverage_area: 'Unassigned coverage area'
            }, 'ngo-new-ngo');
            const fallbackDashboard = this.buildStarterDashboard(fallbackNgo);
            store[fallbackNgo.id] = fallbackDashboard;
            this.writeMockStore(store);
            return this.delay({
                ngo: fallbackDashboard.ngo,
                stats: {
                    active_assignments: fallbackDashboard.active_assignments.length,
                    managed_volunteers: fallbackDashboard.managed_volunteers.length,
                    verified_professionals: fallbackDashboard.managed_volunteers.filter((volunteer) => Boolean(volunteer.ngo_id)).length
                },
                active_assignments: fallbackDashboard.active_assignments,
                managed_volunteers: fallbackDashboard.managed_volunteers
            });
        }

        const resolvedNgoId = ngoId || this.getActiveNgoId() || storeKeys[0];
        const dashboard = store[resolvedNgoId] || this.buildStarterDashboard(this.buildNgoRecord({
            name: 'New NGO',
            reg_number: 'NGO-0000-000',
            coverage_area: 'Unassigned coverage area'
        }, resolvedNgoId));

        if (!store[resolvedNgoId]) {
            store[resolvedNgoId] = dashboard;
            this.writeMockStore(store);
        }

        const activeAssignments = dashboard.active_assignments || [];
        const managedVolunteers = dashboard.managed_volunteers || [];

        return this.delay({
            ngo: dashboard.ngo,
            stats: {
                active_assignments: activeAssignments.length,
                managed_volunteers: managedVolunteers.length,
                verified_professionals: managedVolunteers.filter((volunteer) => Boolean(volunteer.ngo_id)).length
            },
            active_assignments: activeAssignments,
            managed_volunteers: managedVolunteers
        });
    }

    async health() {
        return fetch(`${this.baseURL}/health`)
            .then((response) => response.json())
            .catch(() => ({ status: 'offline' }));
    }

    readMockStore() {
        try {
            const raw = localStorage.getItem(NGO_STORE_KEY);
            if (raw) {
                return JSON.parse(raw);
            }
        } catch (error) {
            console.warn('Unable to read NGO store:', error);
        }

        return JSON.parse(JSON.stringify(DEFAULT_NGO_STORE));
    }

    writeMockStore(store) {
        try {
            localStorage.setItem(NGO_STORE_KEY, JSON.stringify(store));
        } catch (error) {
            console.warn('Unable to write NGO store:', error);
        }
    }

    getActiveNgoId() {
        try {
            return localStorage.getItem(ACTIVE_NGO_KEY) || '';
        } catch (error) {
            return '';
        }
    }

    setActiveNgoId(ngoId) {
        try {
            localStorage.setItem(ACTIVE_NGO_KEY, ngoId);
        } catch (error) {
            console.warn('Unable to store active NGO:', error);
        }
    }

    buildNgoRecord(data, explicitId) {
        const rawName = (data?.name || 'New NGO').trim();
        const regNumber = (data?.reg_number || 'NGO-0000-000').trim();
        const coverageArea = (data?.coverage_area || 'Unspecified coverage area').trim();
        const generatedId = explicitId || `ngo-${this.slugify(rawName)}-${this.slugify(regNumber).slice(-8)}`;

        return {
            id: generatedId,
            name: rawName,
            reg_number: regNumber,
            coverage_area: coverageArea,
            radius: Number(data?.radius || data?.radius_km || 24),
            verified: Boolean(data?.verified ?? false),
            registered_at: data?.registered_at || new Date().toISOString()
        };
    }

    buildStarterDashboard(ngo) {
        const prefix = ngo.id.replace(/[^a-z0-9]/gi, '').slice(-8) || 'ngo';

        return {
            ngo,
            active_assignments: [
                {
                    id: `${prefix}-as-1`,
                    title: `Field coordination - ${ngo.coverage_area}`,
                    location: ngo.coverage_area,
                    priority: 'High',
                    status: 'Queued',
                    eta: '30 min',
                    lead: 'Assigned coordinator'
                },
                {
                    id: `${prefix}-as-2`,
                    title: 'Supply verification sweep',
                    location: `${ngo.coverage_area} staging point`,
                    priority: 'Medium',
                    status: 'Ready',
                    eta: '55 min',
                    lead: 'Operations desk'
                }
            ],
            managed_volunteers: [
                {
                    id: `${prefix}-vol-1`,
                    name: `${ngo.name.split(' ')[0]} Medical Lead`,
                    role: 'Medical Coordinator',
                    zone: ngo.coverage_area,
                    status: 'Available',
                    skills: ['Medical', 'Assessment'],
                    ngo_id: ngo.id
                },
                {
                    id: `${prefix}-vol-2`,
                    name: `${ngo.name.split(' ')[0]} Logistics Lead`,
                    role: 'Logistics Lead',
                    zone: `${ngo.coverage_area} depot`,
                    status: 'On Call',
                    skills: ['Logistics', 'Supply'],
                    ngo_id: ngo.id
                },
                {
                    id: `${prefix}-vol-3`,
                    name: 'Community Support Volunteer',
                    role: 'Volunteer',
                    zone: ngo.coverage_area,
                    status: 'Available',
                    skills: ['Communications', 'Routing']
                }
            ]
        };
    }

    slugify(value) {
        return String(value)
            .toLowerCase()
            .trim()
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-+|-+$/g, '');
    }

    delay(payload) {
        return new Promise((resolve) => {
            setTimeout(() => resolve(JSON.parse(JSON.stringify(payload))), 220);
        });
    }
}

const api = new APIClient();
window.api = api;
