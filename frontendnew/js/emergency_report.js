// ============================================================
// frontend/js/emergency_report.js  — SETU Emergency Need Flow
// ============================================================
// Powers emergency_report.html:
//   1. Enforces authentication (redirects to login if missing)
//   2. Captures GPS location with comprehensive error handling
//   3. Validates inputs matching backend constraints
//   4. Calls ApiService.postNeed(payload) -> POST /need
//   5. Handles 400, 401, 403, 404, 422, 500 & 200 {error} responses
//   6. Renders live processed triage result & database entry details
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    initAuthGuard();
    setupCharCounter();
    prefillUserData();
});

// ── Auth Guard ──────────────────────────────────────────────
function initAuthGuard() {
    const token = localStorage.getItem('auth_token');
    if (!token) {
        // Redirect unauthenticated user to login, preserving destination
        window.location.href = 'login.html?redirect=emergency_report.html';
        return;
    }

    // Display user identity in navbar if available
    const userBadge = document.getElementById('user-badge');
    const userIdentifier = document.getElementById('user-identifier');
    const name = localStorage.getItem('name');
    const email = localStorage.getItem('user_email');
    const role = localStorage.getItem('role');

    if (userBadge && userIdentifier) {
        userIdentifier.textContent = name || email || (role ? `${role.toUpperCase()} User` : 'Verified Responder');
        userBadge.classList.remove('hidden');
        userBadge.classList.add('flex');
    }
}

function prefillUserData() {
    const nameInput = document.getElementById('reporter_name');
    const savedName = localStorage.getItem('name');
    if (nameInput && savedName && !nameInput.value) {
        nameInput.value = savedName;
    }
}

// ── Character Counter for Description ───────────────────────
function setupCharCounter() {
    const desc = document.getElementById('description');
    const counter = document.getElementById('charCount');
    if (!desc || !counter) return;

    desc.addEventListener('input', () => {
        const len = desc.value.trim().length;
        counter.textContent = `${len} / 10 min chars`;
        if (len < 10) {
            counter.className = 'text-[12px] text-critical-red font-medium';
        } else {
            counter.className = 'text-[12px] text-safety-green font-medium';
        }
    });
}

// ── Geolocation Handling ─────────────────────────────────────
function captureUserLocation() {
    const gpsBtn = document.getElementById('getGpsBtn');
    const gpsBtnText = document.getElementById('gpsBtnText');
    const statusText = document.getElementById('gps-status-text');
    const coordsDisplay = document.getElementById('gps-coords-display');
    const clearBtn = document.getElementById('clearGpsBtn');
    const latInput = document.getElementById('lat');
    const lngInput = document.getElementById('lng');
    const locTextInput = document.getElementById('location_text');

    if (!navigator.geolocation) {
        const msg = 'Geolocation is not supported by your browser. Please type your location manually.';
        if (statusText) statusText.innerHTML = `<span class="text-critical-red font-medium">⚠️ ${msg}</span>`;
        if (typeof showToast === 'function') showToast(msg, 'warning');
        return;
    }

    if (gpsBtn) gpsBtn.disabled = true;
    if (gpsBtnText) gpsBtnText.textContent = 'Acquiring GPS…';
    if (statusText) statusText.textContent = 'Requesting device GPS position…';

    const geoOptions = {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
    };

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const rawLat = position.coords.latitude;
            const rawLng = position.coords.longitude;

            // Validate coordinate numbers
            if (typeof rawLat !== 'number' || typeof rawLng !== 'number' || isNaN(rawLat) || isNaN(rawLng)) {
                handleLocationError({ code: 0, message: 'Received invalid coordinate values from device.' });
                return;
            }

            const lat = Number(rawLat.toFixed(6));
            const lng = Number(rawLng.toFixed(6));

            if (latInput) latInput.value = lat;
            if (lngInput) lngInput.value = lng;

            if (statusText) {
                statusText.innerHTML = '<span class="text-safety-green font-semibold">✓ Live GPS coordinates locked.</span>';
            }
            if (coordsDisplay) {
                coordsDisplay.textContent = `Latitude: ${lat}, Longitude: ${lng} (±${Math.round(position.coords.accuracy || 0)}m accuracy)`;
                coordsDisplay.classList.remove('hidden');
            }
            if (clearBtn) clearBtn.style.display = 'inline-flex';
            if (gpsBtnText) gpsBtnText.textContent = 'GPS Locked';
            if (gpsBtn) gpsBtn.disabled = false;

            // Populate location_text if empty so backend has a human-readable fallback
            if (locTextInput && !locTextInput.value.trim()) {
                locTextInput.value = `GPS: ${lat}, ${lng}`;
            }

            // Hide any previous location error
            const errLoc = document.getElementById('err-location_text');
            if (errLoc) errLoc.classList.add('hidden');

            if (typeof showToast === 'function') {
                showToast('GPS position successfully acquired', 'success');
            }
        },
        (error) => {
            handleLocationError(error);
        },
        geoOptions
    );
}

function handleLocationError(error) {
    const gpsBtn = document.getElementById('getGpsBtn');
    const gpsBtnText = document.getElementById('gpsBtnText');
    const statusText = document.getElementById('gps-status-text');
    const coordsDisplay = document.getElementById('gps-coords-display');
    const clearBtn = document.getElementById('clearGpsBtn');
    const latInput = document.getElementById('lat');
    const lngInput = document.getElementById('lng');

    // Reset coordinates to 0.0 to prevent submitting bad data
    if (latInput) latInput.value = '0.0';
    if (lngInput) lngInput.value = '0.0';
    if (coordsDisplay) coordsDisplay.classList.add('hidden');
    if (clearBtn) clearBtn.style.display = 'none';
    if (gpsBtn) gpsBtn.disabled = false;
    if (gpsBtnText) gpsBtnText.textContent = 'Capture GPS';

    let userMsg = 'Could not acquire GPS position. Please enter your address or landmark manually.';

    switch (error.code) {
        case 1: // PERMISSION_DENIED
            userMsg = 'Location permission was denied. Please allow location access in your browser or type your location manually.';
            break;
        case 2: // POSITION_UNAVAILABLE
            userMsg = 'GPS position is currently unavailable on this device. Please type your location address manually.';
            break;
        case 3: // TIMEOUT
            userMsg = 'GPS location request timed out. Please try again or type your location manually.';
            break;
        default:
            if (error.message) userMsg = `GPS error: ${error.message}`;
            break;
    }

    if (statusText) {
        statusText.innerHTML = `<span class="text-critical-red font-medium">⚠️ ${userMsg}</span>`;
    }
    if (typeof showToast === 'function') {
        showToast(userMsg, 'warning', 5000);
    }
}

function clearGpsLocation() {
    const gpsBtnText = document.getElementById('gpsBtnText');
    const statusText = document.getElementById('gps-status-text');
    const coordsDisplay = document.getElementById('gps-coords-display');
    const clearBtn = document.getElementById('clearGpsBtn');
    const latInput = document.getElementById('lat');
    const lngInput = document.getElementById('lng');

    if (latInput) latInput.value = '0.0';
    if (lngInput) lngInput.value = '0.0';
    if (gpsBtnText) gpsBtnText.textContent = 'Capture GPS';
    if (statusText) statusText.textContent = 'Optional: Automatically attach your live device coordinates to bypass address geocoding.';
    if (coordsDisplay) {
        coordsDisplay.textContent = '';
        coordsDisplay.classList.add('hidden');
    }
    if (clearBtn) clearBtn.style.display = 'none';
}

// ── Validation Helper ────────────────────────────────────────
function validateEmergencyForm(payload) {
    let isValid = true;
    const errors = {};

    // Clear previous inline errors
    ['reporter_name', 'reporter_phone', 'location_text', 'description'].forEach(field => {
        const el = document.getElementById(`err-${field}`);
        if (el) el.classList.add('hidden');
        const input = document.getElementById(field);
        if (input) input.classList.remove('border-critical-red');
    });

    // 1. Reporter Name
    if (!payload.reporter_name || payload.reporter_name.trim().length === 0) {
        errors.reporter_name = 'Please provide your full name.';
        isValid = false;
    }

    // 2. Reporter Phone
    const phoneClean = (payload.reporter_phone || '').trim().replace(/[\s-]/g, '');
    if (!/^\d{10}$/.test(phoneClean)) {
        errors.reporter_phone = 'Please enter a valid 10-digit mobile phone number.';
        isValid = false;
    }

    // 3. Location Check
    const hasValidCoords = (payload.lat !== 0.0 || payload.lng !== 0.0);
    const hasLocationText = Boolean(payload.location_text && payload.location_text.trim().length > 0);
    if (!hasValidCoords && !hasLocationText) {
        errors.location_text = 'Please enter an incident address/landmark or capture your GPS location.';
        isValid = false;
    }

    // 4. Description length check (Backend requires >= 10 chars)
    if (!payload.description || payload.description.trim().length < 10) {
        errors.description = 'Please describe the emergency in detail (at least 10 characters required for AI triage).';
        isValid = false;
    }

    // Render field errors
    for (const [field, msg] of Object.entries(errors)) {
        const el = document.getElementById(`err-${field}`);
        if (el) {
            el.textContent = msg;
            el.classList.remove('hidden');
        }
        const input = document.getElementById(field);
        if (input) input.classList.add('border-critical-red');
    }

    return { isValid, errors };
}

// ── Form Submission ──────────────────────────────────────────
async function handleEmergencySubmit(event) {
    if (event) event.preventDefault();

    const banner = document.getElementById('form-error-banner');
    const bannerMsg = document.getElementById('form-error-message');
    if (banner) banner.style.display = 'none';

    // Collect values matching NeedInput schema
    const rawLat = parseFloat(document.getElementById('lat')?.value || '0.0');
    const rawLng = parseFloat(document.getElementById('lng')?.value || '0.0');

    const payload = {
        reporter_name: document.getElementById('reporter_name')?.value?.trim() || '',
        reporter_phone: document.getElementById('reporter_phone')?.value?.trim() || '',
        location_text: document.getElementById('location_text')?.value?.trim() || '',
        lat: isNaN(rawLat) ? 0.0 : rawLat,
        lng: isNaN(rawLng) ? 0.0 : rawLng,
        disaster_type: document.getElementById('disaster_type')?.value || 'Not Specified',
        help_needed: document.getElementById('help_needed')?.value || 'Not Specified',
        description: document.getElementById('description')?.value?.trim() || ''
    };

    // Client-side validation
    const { isValid, errors } = validateEmergencyForm(payload);
    if (!isValid) {
        const firstErrKey = Object.keys(errors)[0];
        const firstMsg = errors[firstErrKey];
        if (banner && bannerMsg) {
            bannerMsg.textContent = firstMsg;
            banner.style.display = 'flex';
        }
        const firstInput = document.getElementById(firstErrKey);
        if (firstInput) firstInput.focus();
        if (typeof showToast === 'function') showToast(firstMsg, 'warning');
        return;
    }

    // Loading State
    const submitBtn = document.getElementById('submitBtn');
    const submitBtnText = document.getElementById('submitBtnText');
    if (submitBtn) submitBtn.disabled = true;
    if (submitBtnText) submitBtnText.textContent = 'Transmitting to AI Triage…';

    try {
        // Calls POST /need via existing ApiService abstraction
        const response = await ApiService.postNeed(payload);

        if (!response.ok) {
            handleBackendError(response);
            return;
        }

        const data = response.data;

        // Check if backend returned an error in a 200 envelope (e.g. {"error": "..."})
        if (data && data.error) {
            showFormError(data.error);
            return;
        }

        // Render processed result
        displaySubmissionResult(data);

        if (typeof showToast === 'function') {
            showToast('Emergency request submitted and triaged successfully.', 'success');
        }

    } catch (err) {
        console.error('Submission unexpected error:', err);
        showFormError('An unexpected network error occurred. Please check your connection or contact emergency services.');
    } finally {
        if (submitBtn) submitBtn.disabled = false;
        if (submitBtnText) submitBtnText.textContent = 'Submit Emergency Report';
    }
}

// ── Backend Error Handling ───────────────────────────────────
function handleBackendError(response) {
    const status = response.status || 0;
    const errorMsg = response.error || 'Request failed';
    let friendlyMessage = errorMsg;

    switch (status) {
        case 400:
            // Bad request, e.g. location unresolvable or geocoding failed
            friendlyMessage = errorMsg.includes('location') || errorMsg.includes('Geocoding')
                ? `Location Error: ${errorMsg}. Please provide a clearer address or landmark, or use GPS.`
                : `Invalid Request: ${errorMsg}`;
            break;
        case 401:
            friendlyMessage = 'Authentication session expired or missing. Please login to submit emergency reports.';
            setTimeout(() => {
                window.location.href = 'login.html?redirect=emergency_report.html';
            }, 2000);
            break;
        case 403:
            friendlyMessage = 'Access forbidden. You do not have permission to submit this report.';
            break;
        case 404:
            friendlyMessage = 'Emergency submission service is currently unreachable (404). Please contact emergency hotlines directly.';
            break;
        case 422:
            friendlyMessage = `Validation Error: ${errorMsg}. Please verify all fields.`;
            break;
        case 500:
            friendlyMessage = 'The server encountered an error while processing the emergency report. Please try again or reach out to local emergency services.';
            break;
        default:
            friendlyMessage = errorMsg || 'Unable to submit emergency report. Please try again.';
            break;
    }

    showFormError(friendlyMessage);
}

function showFormError(msg) {
    const banner = document.getElementById('form-error-banner');
    const bannerMsg = document.getElementById('form-error-message');
    if (banner && bannerMsg) {
        bannerMsg.textContent = msg;
        banner.style.display = 'flex';
        banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    if (typeof showToast === 'function') {
        showToast(msg, 'error', 6000);
    }
}

// ── Status & Result Rendering ────────────────────────────────
function displaySubmissionResult(data) {
    const formSection = document.getElementById('emergency-form-section');
    const resultSection = document.getElementById('emergency-result-section');

    if (!resultSection) return;

    // Populate actual returned fields from backend
    const docId = data.id || data.need_id || 'N/A';
    const status = data.status || 'open';
    const priority = data.priority || 'MEDIUM';
    const category = data.category || 'other';
    const severity = data.severity || 'medium';
    const trustScore = (data.trust_score !== undefined && data.trust_score !== null) ? data.trust_score : '—';
    const dispatchAction = data.dispatch_action || 'N/A';
    const flag = data.flag || 'N/A';
    const lat = data.lat !== undefined ? data.lat : 0;
    const lng = data.lng !== undefined ? data.lng : 0;
    const reasons = Array.isArray(data.reasons) ? data.reasons : [];

    // Elements
    const idEl = document.getElementById('res-id');
    const statusEl = document.getElementById('res-status');
    const priorityEl = document.getElementById('res-priority');
    const categoryEl = document.getElementById('res-category');
    const severityEl = document.getElementById('res-severity');
    const trustEl = document.getElementById('res-trust-score');
    const dispatchEl = document.getElementById('res-dispatch-action');
    const flagEl = document.getElementById('res-flag');
    const coordsEl = document.getElementById('res-coords');
    const reasonsListEl = document.getElementById('res-reasons-list');

    if (idEl) idEl.textContent = docId;

    if (statusEl) {
        statusEl.textContent = status.replace('_', ' ').toUpperCase();
        statusEl.className = 'inline-block px-3 py-1 rounded-full text-label-sm font-bold tracking-wide uppercase ' +
            (status === 'open' ? 'bg-green-100 text-safety-green border border-green-200' :
             status === 'secondary_review' ? 'bg-amber-100 text-yellow-800 border border-amber-200' :
             'bg-red-100 text-critical-red border border-red-200');
    }

    if (priorityEl) {
        priorityEl.textContent = priority.toUpperCase();
        priorityEl.className = 'inline-block px-3 py-1 rounded-full text-label-sm font-bold tracking-wide uppercase ' +
            (priority === 'HIGH' ? 'bg-red-100 text-critical-red border border-red-200' :
             priority === 'MEDIUM' ? 'bg-amber-100 text-yellow-800 border border-amber-200' :
             'bg-blue-100 text-primary border border-blue-200');
    }

    if (categoryEl) categoryEl.textContent = category;
    if (severityEl) severityEl.textContent = severity;
    if (trustEl) trustEl.textContent = `${trustScore} / 100`;
    if (dispatchEl) dispatchEl.textContent = dispatchAction;

    if (flagEl) {
        flagEl.textContent = flag.toUpperCase();
        flagEl.className = 'font-label-md font-bold uppercase ' +
            (flag === 'verified' ? 'text-safety-green' : 'text-yellow-700');
    }

    if (coordsEl) {
        coordsEl.textContent = (lat !== 0 || lng !== 0) ? `${lat}, ${lng}` : (data.location_text || 'Coordinates not provided');
    }

    if (reasonsListEl) {
        reasonsListEl.innerHTML = '';
        if (reasons.length > 0) {
            reasons.forEach(r => {
                const li = document.createElement('li');
                li.textContent = r;
                reasonsListEl.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.textContent = 'Automated validation checks completed successfully.';
            reasonsListEl.appendChild(li);
        }
    }

    // Toggle view
    if (formSection) formSection.style.display = 'none';
    resultSection.style.display = 'flex';
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function resetEmergencyForm() {
    const form = document.getElementById('emergencyForm');
    if (form) form.reset();

    clearGpsLocation();

    const banner = document.getElementById('form-error-banner');
    if (banner) banner.style.display = 'none';

    const charCount = document.getElementById('charCount');
    if (charCount) {
        charCount.textContent = '0 / 10 min chars';
        charCount.className = 'text-[12px] text-text-muted font-medium';
    }

    prefillUserData();

    const formSection = document.getElementById('emergency-form-section');
    const resultSection = document.getElementById('emergency-result-section');
    if (resultSection) resultSection.style.display = 'none';
    if (formSection) {
        formSection.style.display = 'flex';
        formSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Expose globals for inline HTML event handlers
window.captureUserLocation   = captureUserLocation;
window.clearGpsLocation      = clearGpsLocation;
window.handleEmergencySubmit = handleEmergencySubmit;
window.resetEmergencyForm    = resetEmergencyForm;
