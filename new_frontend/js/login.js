const API_BASE = "http://127.0.0.1:8000";

function openNeedForm() {
    window.open("https://docs.google.com/forms/d/e/1FAIpQLSfpOTtIUbv4g216ME419DG_BqF_PCS1chJ0es47HRbkznNA1g/viewform", "_blank");
}

async function login() {

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const roleEl = document.getElementById("role");
    const selectedRole = roleEl ? roleEl.value : "volunteer";

    if (!email || !password) {
        alert("Please fill all fields");
        return;
    }

    try {

        const res = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email: email,      // ✅ FIXED
                password: password
            })
        });

        const data = await res.json();

        if (!res.ok) {
            alert(data.detail || "Login failed");
            return;
        }

        // ✅ Save token
        localStorage.setItem("auth_token", data.token);

        console.log("Login response:", data);

        // 🔥 ROLE HANDLING
        let role = data.role;

        // ⚠️ fallback (agar backend role nahi bhejta)
        if (!role) {
            role = selectedRole;
        }

        // 🚀 REDIRECT
        if (role === "ngo") {
            window.location.href = "ngo-dashboard.html";
        } else {
            window.location.href = "volunteer-dashboard.html";
        }

    } catch (err) {
        console.error("Login error:", err);
        alert("Server error");
    }
}