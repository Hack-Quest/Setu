const API_BASE = window.SETU_API_BASE_URL || "";

// 📩 Open Google Form (unchanged)
function openNeedForm() {
    window.open(
        "https://docs.google.com/forms/d/e/1FAIpQLSfpOTtIUbv4g216ME419DG_BqF_PCS1chJ0es47HRbkznNA1g/viewform",
        "_blank"
    );
}

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

        // Reveal OTP section
        document.getElementById("otp-section").style.display = "block";
        
        // Disable email input
        document.getElementById("email").disabled = true;
        
        // Disable role selection
        document.getElementById("role").disabled = true;

        // Change button text
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

        // ✅ STORE AUTH DATA
        localStorage.setItem("auth_token", data.token);
        localStorage.setItem("role", role);

        if (data.id) {
            localStorage.setItem("volunteer_id", data.id);
            localStorage.setItem("ngo_id", data.id);
        }

        if (data.name) {
            localStorage.setItem("name", data.name);
        }

        console.log("Login success:", data);

        // 🔀 REDIRECT
        if (role === "ngo") {
            window.location.href = "ngo-dashboard.html";
        } else {
            window.location.href = "volunteer-dashboard.html";
        }

    } catch (err) {
        console.error(err);
        showToast("Server error while verifying OTP", "error");
    }
}