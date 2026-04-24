const API_BASE = window.SETU_API_BASE_URL || "";
requireAuth();

// 🔓 Logout
function logout() {
    localStorage.clear();
    window.location.href = "index.html";
}

// 📌 Volunteer ID
const volunteerId = localStorage.getItem("volunteer_id");

// 🔥 CRITICAL FIX (invalid ID check)
if (!volunteerId || volunteerId === "null" || volunteerId === "undefined") {
    console.error("Invalid volunteer ID, redirecting...");
    window.location.href = "login.html";
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