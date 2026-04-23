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

    if (!email) {
        alert("Please enter email");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/auth/send-otp`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email })
        });

        const data = await res.json();

        if (!res.ok) {
            alert(data.detail || "Failed to send OTP");
            return;
        }

        alert("✅ OTP sent to your email");

    } catch (err) {
        console.error(err);
        alert("Server error while sending OTP");
    }
}

// 🔐 VERIFY OTP
async function verifyOTP() {
    const email = document.getElementById("email").value;
    const otp = document.getElementById("otp").value;

    if (!email || !otp) {
        alert("Enter email and OTP");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/auth/verify-otp`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email, otp })
        });

        const data = await res.json();

        if (!res.ok) {
            alert(data.detail || "Invalid OTP");
            return;
        }

        // ✅ STORE AUTH DATA
        localStorage.setItem("auth_token", data.token);
        localStorage.setItem("role", data.role);

        if (data.id) {
            localStorage.setItem("volunteer_id", data.id);
            localStorage.setItem("ngo_id", data.id);
        }

        if (data.name) {
            localStorage.setItem("name", data.name);
        }

        console.log("Login success:", data);

        // 🔀 REDIRECT
        if (data.role === "ngo") {
            window.location.href = "ngo-dashboard.html";
        } else {
            window.location.href = "volunteer-dashboard.html";
        }

    } catch (err) {
        console.error(err);
        alert("Server error while verifying OTP");
    }
}