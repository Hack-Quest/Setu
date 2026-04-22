const API_BASE = "http://127.0.0.1:8000";
const token = localStorage.getItem("auth_token") || localStorage.getItem("token") || "hackathon-secret";

async function api(endpoint, options = {}) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
        headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
        ...options
    });
    return res.json();
}

async function loadReports() {
    const data = await api("/dashboard/reports");
    const reports = data.reports || data;
    // sort by severity for visual priority
    const order = { critical: 0, "very high": 1, high: 2, medium: 3, low: 4 };
    reports.sort((a, b) => (order[a.severity] ?? 5) - (order[b.severity] ?? 5));
    renderReports(reports);
}

async function runMatch() {
    const data = await api("/match");
    alert(`Matched ${data.total_matches_made} assignments`);
    loadReports();
}

async function resolve(needId, volunteerId, assignmentId) {
    await api(`/assignment/${assignmentId}/resolve`, {
        method: "PATCH",
        body: JSON.stringify({ need_id: needId, volunteer_id: volunteerId })
    });
    loadReports();
}

function renderReports(reports) {
    const container = document.getElementById("reportsList");
    container.innerHTML = "";

    reports.forEach(r => {
        const severity = (r.severity || "low").toLowerCase();

        const card = document.createElement("div");
        card.className = "report-card";

        const needId = r.id;
        const volunteerId = r.volunteer_id;
        const assignmentId = r.assignment_id;

        let actionButton = "";
        // Only show resolve button if it's assigned and we have the necessary IDs
        if (r.status === "assigned" && assignmentId && volunteerId) {
            actionButton = `<button onclick="resolve('${needId}', '${volunteerId}', '${assignmentId}')" style="margin-top: 10px; padding: 5px 10px; background-color: #f44336; color: white; border: none; border-radius: 3px; cursor: pointer;">Resolve Assignment</button>`;
        }

        card.innerHTML = `
            <div class="report-header">
                <h3>${r.disaster_type || "Emergency"}</h3>
                <span class="badge ${severity}">
                    ${severity.toUpperCase()}
                </span>
            </div>

            <p class="desc">${r.description || ""}</p>

            <p class="status">
                Status: ${r.status || "Pending"}
            </p>

            <p>
                Assigned: ${r.volunteer_name || "Auto-assigned"}
            </p>
            ${actionButton}
        `;

        container.appendChild(card);
    });
}

function logout() {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("token");
    window.location.href = "index.html";
}

// 🚀 INIT
loadReports();