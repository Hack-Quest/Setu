const API_BASE = window.SETU_API_BASE_URL || "";
requireAuth();

// 🔓 Logout
function logout() {
    localStorage.clear();
    window.location.href = "index.html";
}

// 📌 Volunteer ID
const volunteerId = localStorage.getItem("volunteer_id");

// 🔥 CRITICAL FIX (invalid ID check — graceful, no redirect loop)
if (!volunteerId || volunteerId === "null" || volunteerId === "undefined") {
    console.error("Invalid volunteer ID");

    document.body.innerHTML = `
        <div style="text-align:center;padding:40px;font-family:sans-serif;">
            <h2>Session Error</h2>
            <p>Could not retrieve your volunteer ID.</p>
            <p>Please <a href="login.html">log in again</a>.</p>
            <p style="color:#888;font-size:0.9em;">Redirecting in 3 seconds...</p>
        </div>
    `;

    // Delayed redirect — prevents infinite loop
    setTimeout(() => {
        window.location.href = "login.html";
    }, 3000);

    throw new Error("Stopping dashboard execution due to invalid volunteer ID");
}

// 👤 Load Profile
async function loadProfile() {
    const name = localStorage.getItem("name") || "Volunteer";
    document.getElementById("name").innerText = name;
    document.getElementById("skills").innerText = "Skills: Assigned dynamically";
    document.getElementById("ngo").innerText = "NGO: Connected";
    document.getElementById("status").innerText = "Status: Checking...";
}

// ─── Dashboard
async function initDashboard() {
    const container = document.getElementById("volunteerDashboardBody");
    if (!container) return;

    container.innerHTML = "<tr><td colspan='6'>Loading...</td></tr>";

    const response = await ApiService.getVolunteerAssignments(volunteerId);
    const data = response && response.ok ? response.data : null;

    if (!data) {
        container.innerHTML = "<tr><td colspan='6'>⚠️ Could not load data</td></tr>";
        return;
    }

    const reports = data.reports || [];
    container.innerHTML = "";

    if (!reports.length) {
        container.innerHTML = "<tr><td colspan='6'>No active assignments.</td></tr>";
        return;
    }

    reports.forEach(r => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${r.reporter_name || "Unknown"}</td>
            <td>${r.location || "N/A"}</td>
            <td>${r.disaster_type || "Emergency"}</td>
            <td>${r.description || ""}</td>
            <td>${r.status || "pending"}</td>
            <td>—</td>
        `;

        container.appendChild(tr);
    });
}

// 🚀 INIT
loadProfile();
initDashboard();