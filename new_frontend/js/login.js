const API_BASE = window.SETU_API_BASE_URL || "";

// 📩 SEND OTP
async function sendOTP() {
    const email = document.getElementById("email").value;
    const role = document.getElementById("role").value;

    if (!email) {
        showToast("Please enter email", "info");
        return;
    }

    try {
        const response = await ApiService.sendOtp({ email, role });

        if (!response.ok) {
            showToast(response.error || "Failed to send OTP", "error");
            return;
        }

        showToast("✅ OTP sent to your email", "success");

        document.getElementById("otp-section").style.display = "block";
        document.getElementById("email").disabled = true;
        document.getElementById("role").disabled = true;

        document.querySelector(".btn-primary").innerText = "Resend OTP";

    } catch (err) {
        console.error(err);
        showToast("Server error while sending OTP", "error");
    }
}

// 🔐 VERIFY OTP
async function verifyOTP() {
    const email = document.getElementById("email").value;
    const otp = document.getElementById("otp").value;
    const role = document.getElementById("role").value;

    if (!email || !otp) {
        showToast("Enter email and OTP", "info");
        return;
    }

    try {
        const response = await ApiService.verifyOtp({ email, otp });

        if (!response.ok) {
            showToast(response.error || "Invalid OTP", "error");
            return;
        }

        const data = response.data;
        console.log("VERIFY OTP RESPONSE:", data);

        // ✅ STORE TOKEN + ROLE
        localStorage.setItem("auth_token", data.token);
        localStorage.setItem("role", role);

        // 🔥 CRITICAL FIX (NO fallback garbage)
        if (data.volunteer_id && data.volunteer_id !== "null") {
            localStorage.setItem("volunteer_id", data.volunteer_id);
        } else {
            console.warn("No valid volunteer_id received");
        }

        // NGO ID
        if (data.id) {
            localStorage.setItem("ngo_id", data.id);
        }

        // Name
        if (data.name) {
            localStorage.setItem("name", data.name);
        }

        // 🔀 REDIRECT — handle new/unregistered users
        if (role === "ngo") {
            window.location.href = "ngo-dashboard.html";
        } else if (data.volunteer_id && data.volunteer_id !== "null") {
            window.location.href = "volunteer-dashboard.html";
        } else {
            // Volunteer email not registered in system
            showToast("⚠️ Email not found. Please register as a volunteer first.", "error");
            return; // Don't redirect at all
        }

    } catch (err) {
        console.error(err);
        showToast("Server error while verifying OTP", "error");
    }
}