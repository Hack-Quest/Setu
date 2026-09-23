// ============================================================
// frontend/js/login.js  — SETU Portal Login Flow
// ============================================================
// Drives the login.html page:
//   1. OTP Verification Flow (Default):
//      - User enters email + selects role → Send OTP
//      - User enters OTP → Verify → redirect based on role
//   2. Direct Password Flow:
//      - Registered volunteers enter email + password → redirect to volunteer dashboard
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    // OTP flow elements
    const sendBtn    = document.getElementById('sendBtn');
    const verifyBtn  = document.getElementById('verifyBtn');
    const emailInput = document.getElementById('email');
    const otpInput   = document.getElementById('otp');

    if (sendBtn)   sendBtn.addEventListener('click',   sendOTP);
    if (verifyBtn) verifyBtn.addEventListener('click', verifyOTP);

    if (otpInput) {
        otpInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') verifyOTP();
        });
    }
    if (emailInput) {
        emailInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') sendOTP();
        });
    }

    // Password flow elements
    const loginPassBtn  = document.getElementById('loginPassBtn');
    const passEmail     = document.getElementById('passEmail');
    const passPassword  = document.getElementById('passPassword');

    if (loginPassBtn) loginPassBtn.addEventListener('click', loginWithPassword);

    if (passPassword) {
        passPassword.addEventListener('keydown', e => {
            if (e.key === 'Enter') loginWithPassword();
        });
    }
    if (passEmail) {
        passEmail.addEventListener('keydown', e => {
            if (e.key === 'Enter') loginWithPassword();
        });
    }

    // Tab switcher
    const tabOtp      = document.getElementById('tabOtp');
    const tabPassword = document.getElementById('tabPassword');
    const otpFlow     = document.getElementById('otp-flow');
    const passFlow    = document.getElementById('password-flow');

    if (tabOtp && tabPassword && otpFlow && passFlow) {
        tabOtp.addEventListener('click', () => {
            tabOtp.className = 'flex-1 pb-2.5 text-label-sm font-bold border-b-2 border-primary text-primary transition-all';
            tabPassword.className = 'flex-1 pb-2.5 text-label-sm font-bold border-b-2 border-transparent text-text-muted hover:text-text-main transition-all';
            otpFlow.style.display = 'flex';
            passFlow.style.display = 'none';
        });

        tabPassword.addEventListener('click', () => {
            tabPassword.className = 'flex-1 pb-2.5 text-label-sm font-bold border-b-2 border-primary text-primary transition-all';
            tabOtp.className = 'flex-1 pb-2.5 text-label-sm font-bold border-b-2 border-transparent text-text-muted hover:text-text-main transition-all';
            passFlow.style.display = 'flex';
            otpFlow.style.display = 'none';
        });
    }
});

// ── Step 1: Send OTP ──────────────────────────────────────
async function sendOTP() {
    const email = document.getElementById('email')?.value?.trim();
    const role  = document.getElementById('role')?.value;

    if (!email) { showToast('Please enter your email address', 'warning'); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showToast('Please enter a valid email address', 'warning');
        return;
    }

    const btn = document.getElementById('sendBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Sending…'; }

    try {
        const response = await ApiService.sendOtp({ email, role });

        if (!response.ok) {
            showToast(response.error || 'Failed to send OTP', 'error');
            return;
        }

        showToast('OTP sent to your email ✉️', 'success');
        const otpSection = document.getElementById('otp-section');
        if (otpSection) otpSection.style.display = 'block';

        // Lock email + role fields after OTP sent
        const emailInput = document.getElementById('email');
        const roleSelect = document.getElementById('role');
        if (emailInput) emailInput.disabled = true;
        if (roleSelect) roleSelect.disabled = true;

        if (btn) btn.textContent = 'Resend OTP';

        // Focus OTP input
        setTimeout(() => document.getElementById('otp')?.focus(), 200);

    } catch (err) {
        console.error('sendOTP error:', err);
        showToast('Server error. Please try again.', 'error');
    } finally {
        if (btn) btn.disabled = false;
    }
}

// ── Step 2: Verify OTP ────────────────────────────────────
async function verifyOTP() {
    const email = document.getElementById('email')?.value?.trim();
    const otp   = document.getElementById('otp')?.value?.trim();
    const role  = document.getElementById('role')?.value;

    if (!email || !otp) { showToast('Enter both email and OTP', 'warning'); return; }

    const btn = document.getElementById('verifyBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Verifying…'; }

    try {
        const response = await ApiService.verifyOtp({ email, otp });

        if (!response.ok) {
            showToast(response.error || 'Invalid or expired OTP', 'error');
            return;
        }

        const data = response.data;
        console.log('Verify OTP response:', data);

        if (data.ok === false || data.role === 'new_user') {
            showToast(data.message || 'Email not registered. Please sign up as a volunteer first.', 'error');
            return;
        }

        // Store auth info
        if (data.token) localStorage.setItem('auth_token', data.token);
        const resolvedRole = data.role || role;
        localStorage.setItem('role', resolvedRole);

        if (resolvedRole === 'ngo') {
            localStorage.removeItem('volunteer_id');
            const ngoId = data.id || data.ngo_id;
            if (ngoId && ngoId !== 'null' && ngoId !== 'undefined') {
                localStorage.setItem('ngo_id', ngoId);
            }
        } else if (resolvedRole === 'volunteer') {
            localStorage.removeItem('ngo_id');
            const volunteerId = data.volunteer_id || data.id;
            if (volunteerId && volunteerId !== 'null' && volunteerId !== 'undefined') {
                localStorage.setItem('volunteer_id', volunteerId);
            }
        }

        if (data.ngo_name)  localStorage.setItem('name', data.ngo_name);
        else if (data.name) localStorage.setItem('name', data.name);
        if (data.email)     localStorage.setItem('user_email', data.email);

        showToast('Login successful! Redirecting…', 'success');

        // Redirect based on redirect parameter or role
        const urlParams = new URLSearchParams(window.location.search);
        const redirectUrl = urlParams.get('redirect');

        setTimeout(() => {
            if (redirectUrl) {
                window.location.href = redirectUrl;
            } else if (resolvedRole === 'ngo') {
                window.location.href = 'ngo.html';
            } else {
                window.location.href = 'volunteer.html';
            }
        }, 800);

    } catch (err) {
        console.error('verifyOTP error:', err);
        showToast('Server error. Please try again.', 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Verify & Login'; }
    }
}

// ── Step 3: Password Login Flow ───────────────────────────
async function loginWithPassword() {
    const email = document.getElementById('passEmail')?.value?.trim();
    const password = document.getElementById('passPassword')?.value;

    if (!email || !password) {
        showToast('Please enter both email and password', 'warning');
        return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showToast('Please enter a valid email address', 'warning');
        return;
    }

    const btn = document.getElementById('loginPassBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Logging in…'; }

    try {
        const response = await ApiService.login({ email, password });

        if (!response.ok) {
            showToast(response.error || 'Invalid email or password', 'error');
            return;
        }

        const data = response.data;
        if (data.token) localStorage.setItem('auth_token', data.token);
        localStorage.setItem('role', 'volunteer');
        localStorage.removeItem('ngo_id');

        const volunteerId = data.volunteer_id || data.id;
        if (volunteerId && volunteerId !== 'null' && volunteerId !== 'undefined') {
            localStorage.setItem('volunteer_id', volunteerId);
        }

        if (data.name) localStorage.setItem('name', data.name);
        if (data.email) localStorage.setItem('user_email', data.email);

        showToast('Login successful! Redirecting…', 'success');

        setTimeout(() => {
            window.location.href = 'volunteer.html';
        }, 800);

    } catch (err) {
        console.error('loginWithPassword error:', err);
        showToast('Server error. Please try again.', 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Log In'; }
    }
}

// Expose for any inline onclick="" usage
window.sendOTP           = sendOTP;
window.verifyOTP         = verifyOTP;
window.loginWithPassword = loginWithPassword;
