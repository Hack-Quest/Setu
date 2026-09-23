// ============================================================
// frontend/js/login.js  — SETU OTP Login Flow
// ============================================================
// Drives the login.html page:
//   1. User enters email + selects role → Send OTP
//   2. User enters OTP → Verify → redirect based on role
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    const sendBtn    = document.getElementById('sendBtn');
    const verifyBtn  = document.getElementById('verifyBtn');
    const otpSection = document.getElementById('otp-section');
    const emailInput = document.getElementById('email');
    const roleSelect = document.getElementById('role');
    const otpInput   = document.getElementById('otp');

    if (sendBtn)   sendBtn.addEventListener('click',   sendOTP);
    if (verifyBtn) verifyBtn.addEventListener('click', verifyOTP);

    // Allow pressing Enter in OTP field to verify
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

        // Redirect based on role
        setTimeout(() => {
            if (resolvedRole === 'ngo') {
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

// Expose for any inline onclick="" usage
window.sendOTP   = sendOTP;
window.verifyOTP = verifyOTP;
