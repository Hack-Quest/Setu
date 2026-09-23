// ============================================================
// frontend/js/volunteer-register.js — SETU Native Volunteer Registration
// ============================================================
// Handles native volunteer registration:
//   1. Client-side input validation
//   2. Submits payload to existing POST /auth/register via ApiService
//   3. Handles duplicate email, invalid location, network failures
//   4. Shows clear success state and directs to login
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('volunteerForm');
    const togglePassBtn = document.getElementById('togglePasswordBtn');

    if (form) {
        form.addEventListener('submit', handleRegisterSubmit);
    }

    if (togglePassBtn) {
        togglePassBtn.addEventListener('click', togglePasswordVisibility);
    }
});

function togglePasswordVisibility() {
    const passwordInput = document.getElementById('password');
    const icon = document.getElementById('togglePasswordIcon');
    if (!passwordInput || !icon) return;

    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        icon.textContent = 'visibility_off';
    } else {
        passwordInput.type = 'password';
        icon.textContent = 'visibility';
    }
}

function hideError() {
    const errorBox = document.getElementById('form-error');
    if (errorBox) errorBox.style.display = 'none';
}

function showError(message) {
    const errorBox = document.getElementById('form-error');
    const errorText = document.getElementById('form-error-text');
    if (errorBox && errorText) {
        errorText.textContent = message;
        errorBox.style.display = 'flex';
        errorBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    if (typeof showToast === 'function') {
        showToast(message, 'error');
    }
}

async function handleRegisterSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    hideError();

    const name = document.getElementById('name')?.value?.trim();
    const email = document.getElementById('email')?.value?.trim();
    const password = document.getElementById('password')?.value;
    const phone = document.getElementById('phone')?.value?.trim();
    const location = document.getElementById('location')?.value?.trim();

    // ── 1. Validation ─────────────────────────────────────────
    if (!name) {
        showError('Please enter your full name.');
        document.getElementById('name')?.focus();
        return;
    }

    if (!email) {
        showError('Please enter your email address.');
        document.getElementById('email')?.focus();
        return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showError('Please enter a valid email address.');
        document.getElementById('email')?.focus();
        return;
    }

    if (!phone) {
        showError('Please enter your phone number.');
        document.getElementById('phone')?.focus();
        return;
    }

    const cleanedPhone = phone.replace(/[^\d+]/g, '');
    if (cleanedPhone.length < 7) {
        showError('Please enter a valid phone number (at least 7 digits).');
        document.getElementById('phone')?.focus();
        return;
    }

    if (!password || password.length < 6) {
        showError('Password must be at least 6 characters long.');
        document.getElementById('password')?.focus();
        return;
    }

    if (!location) {
        showError('Please enter your location or city for emergency dispatch.');
        document.getElementById('location')?.focus();
        return;
    }

    // Collect skills
    const checkedBoxes = Array.from(document.querySelectorAll('input[name="skills"]:checked'));
    const checkedSkills = checkedBoxes.map(cb => cb.value.trim().toLowerCase());

    const customInput = document.getElementById('custom_skills')?.value?.trim();
    let customSkills = [];
    if (customInput) {
        customSkills = customInput
            .split(',')
            .map(s => s.trim().toLowerCase())
            .filter(Boolean);
    }

    const combinedSkills = Array.from(new Set([...checkedSkills, ...customSkills]));
    if (combinedSkills.length === 0) {
        showError('Please select or specify at least one skill or emergency response capability.');
        return;
    }

    // ── 2. Loading State & Double-submission Prevention ──────
    const submitBtn = document.getElementById('submitBtn');
    if (!submitBtn) return;

    submitBtn.disabled = true;
    const originalBtnContent = submitBtn.innerHTML;
    submitBtn.innerHTML = `
        <div class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
        <span>Registering Volunteer…</span>
    `;

    // ── 3. Submit to existing FastAPI /auth/register ──────────
    const payload = {
        name,
        email,
        password,
        phone,
        location,
        skills: combinedSkills
    };

    try {
        const response = await ApiService.register(payload);

        if (!response.ok) {
            let errorMsg = response.error || 'Registration failed. Please try again.';
            const lowerErr = errorMsg.toLowerCase();

            if (lowerErr.includes('already registered')) {
                errorMsg = 'This email is already registered. Please log in instead or use a different email.';
            } else if (lowerErr.includes('location') || lowerErr.includes('unresolvable')) {
                errorMsg = 'Could not verify location. Please enter a recognized city or complete address (e.g. "Delhi" or "Mumbai").';
            } else if (lowerErr.includes('failed to fetch') || lowerErr.includes('network') || lowerErr.includes('connection')) {
                errorMsg = 'Could not reach the SETU server. Please check your internet connection or verify the backend is running.';
            }

            showError(errorMsg);
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnContent;
            return;
        }

        // Success!
        showSuccessView(name, email);

    } catch (err) {
        console.error('Registration error:', err);
        const networkError = 'Could not connect to the SETU backend server. Please verify your connection and try again.';
        showError(networkError);
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnContent;
    }
}

function showSuccessView(name, email) {
    const form = document.getElementById('volunteerForm');
    const successCard = document.getElementById('success-card');
    const successMsg = document.getElementById('success-message');
    const countdownEl = document.getElementById('redirect-countdown');

    if (form) form.style.display = 'none';
    hideError();

    if (successMsg) {
        successMsg.textContent = `Welcome, ${name}! Your volunteer account (${email}) has been successfully created. You can now log in to access your volunteer dashboard and receive mission assignments.`;
    }

    if (successCard) {
        successCard.style.display = 'flex';
        successCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    if (typeof showToast === 'function') {
        showToast('Registration successful! Welcome to SETU.', 'success');
    }

    // Auto-redirect countdown
    let secondsLeft = 5;
    const interval = setInterval(() => {
        secondsLeft -= 1;
        if (countdownEl) {
            countdownEl.textContent = `Redirecting to login in ${secondsLeft} seconds...`;
        }
        if (secondsLeft <= 0) {
            clearInterval(interval);
            window.location.href = 'login.html';
        }
    }, 1000);
}

// Expose handlers globally
window.handleRegisterSubmit = handleRegisterSubmit;
window.togglePasswordVisibility = togglePasswordVisibility;
