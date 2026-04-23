const API_BASE = window.SETU_API_BASE_URL || "";

function getToken() {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "login.html";
        throw new Error("Not authenticated");
    }
    return token;
}

async function api(endpoint, options = {}) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
        headers: { "Authorization": `Bearer ${getToken()}`, "Content-Type": "application/json" },
        ...options
    });
    if (!res.ok) {
        console.error(`API error ${res.status} on ${endpoint}`);
        return null;
    }
    return token;
}

// 🌐 API helper
async function api(endpoint, options = {}) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                "Authorization": `Bearer ${getToken()}`,
                "Content-Type": "application/json"
            },
            ...options
        });

        if (!res.ok) {
            console.error(`API error ${res.status} on ${endpoint}`);
            return null;
        }

        return await res.json();
    } catch (err) {
        console.error("API failed:", err);
        return null;
    }
}

// 🔥 Severity order
const SEVERITY_ORDER = {
    critical: 0,
    "very high": 1,
    high: 2,
    medium: 3,
    low: 4
};

// 📊 Load reports
async function loadReports() {
    const data = await api("/dashboard/reports");

    const container = document.getElementById("reportsList");

    if (!data) {
        container.innerHTML = "<p>⚠️ Could not load reports</p>";
        return;
    }

    const reports = data.reports || data || [];

    reports.sort((a, b) =>
        (SEVERITY_ORDER[(a.severity || "low").toLowerCase()] ?? 5) -
        (SEVERITY_ORDER[(b.severity || "low").toLowerCase()] ?? 5)
    );

    renderReports(reports);
}

// 🎨 Badge
function severityBadge(severity) {
    const colors = {
        critical: "#c0392b",
        "very high": "#e74c3c",
        high: "#e67e22",
        medium: "#f1c40f",
        low: "#27ae60"
    };

    const bg = colors[severity] || "#999";

    return `<span style="
        background:${bg};
        color:#fff;
        padding:2px 8px;
        border-radius:12px;
        font-size:0.75rem;
        font-weight:700;
        text-transform:uppercase;
    ">${severity}</span>`;
}

// 📋 Render
function renderReports(reports) {
    const container = document.getElementById("reportsList");
    container.innerHTML = "";

    if (!reports.length) {
        container.innerHTML = "<p>No active reports</p>";
        return;
    }

    reports.forEach(r => {
        const severity = (r.severity || "low").toLowerCase();

        const volunteerName =
            r.volunteer_name ||
            r.assigned_volunteer ||
            "Auto-assigned";

        const isAssigned = r.status === "assigned";

        let resolveBtn = "";

        if (isAssigned && r.assignment_id && r.volunteer_id) {
            resolveBtn = `
                <button onclick="resolve('${r.id}','${r.volunteer_id}','${r.assignment_id}')"
                    style="margin-top:10px;padding:6px 14px;background:#e74c3c;color:#fff;border:none;border-radius:5px;">
                    Mark Resolved
                </button>`;
        }

        const card = document.createElement("div");
        card.className = "report-card";

        card.innerHTML = `
            <div class="report-header">
                <h3>${r.disaster_type || "Emergency"}</h3>
                ${severityBadge(severity)}
            </div>

            <p class="desc">${r.summary_en || r.description || ""}</p>

            <p class="status">Status: ${r.status || "pending"}</p>

            <p>Assigned: <b>${volunteerName}</b></p>

            ${resolveBtn}
        `;

        container.appendChild(card);
    });
}

// ✅ Resolve
async function resolve(needId, volunteerId, assignmentId) {
    const ok = confirm("Mark this assignment as resolved?");
    if (!ok) return;

    const res = await api(`/assignment/${assignmentId}/resolve`, {
        method: "PATCH",
        body: JSON.stringify({
            need_id: needId,
            volunteer_id: volunteerId
        })
    });

    if (res) loadReports();
    else alert("Resolve failed");
}

// 🔓 Logout
function logout() {
    localStorage.clear();
    window.location.href = "index.html";
}

// 🚀 INIT
loadReports();