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
    return res.json();
}

const SEVERITY_ORDER = { critical: 0, "very high": 1, high: 2, medium: 3, low: 4 };

async function loadReports() {
    const data = await api("/dashboard/reports");
    if (!data) {
        document.getElementById("reportsList").innerHTML = "<p>Could not load reports. Is the backend running?</p>";
        return;
    }
    const reports = data.reports || data || [];

    // Sort by severity weight (highest urgency first)
    reports.sort((a, b) =>
        (SEVERITY_ORDER[(a.severity || "low").toLowerCase()] ?? 5) -
        (SEVERITY_ORDER[(b.severity || "low").toLowerCase()] ?? 5)
    );
    renderReports(reports);
}

async function runMatch() {
    const btn = document.getElementById("matchBtn");
    if (btn) { btn.disabled = true; btn.textContent = "Running..."; }

    const data = await api("/match");

    if (btn) { btn.disabled = false; btn.textContent = "Run Match Engine"; }

    if (!data) { alert("Match engine failed. Check backend logs."); return; }
    alert(`Match complete: ${data.total_matches_made} of ${data.total_needs_processed} needs assigned.`);
    loadReports();
}

async function resolve(needId, volunteerId, assignmentId) {
    const ok = confirm("Mark this assignment as resolved?");
    if (!ok) return;

    const res = await api(`/assignment/${assignmentId}/resolve`, {
        method: "PATCH",
        body: JSON.stringify({ need_id: needId, volunteer_id: volunteerId })
    });
    if (res) { loadReports(); }
    else { alert("Could not resolve assignment. Check backend."); }
}

// Returns a color-coded badge element string for a severity label
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
        background:${bg}; color:#fff; padding:2px 8px;
        border-radius:12px; font-size:0.75rem; font-weight:700;
        text-transform:uppercase; letter-spacing:0.5px;
    ">${severity}</span>`;
}

function renderReports(reports) {
    const container = document.getElementById("reportsList");
    if (!container) return;
    container.innerHTML = "";

    if (!reports.length) {
        container.innerHTML = "<p style='color:#888;'>No open reports at this time.</p>";
        return;
    }

    reports.forEach(r => {
        const severity      = (r.severity || "low").toLowerCase();
        const needId        = r.id;
        const volunteerId   = r.volunteer_id;
        const assignmentId  = r.assignment_id;
        const volunteerName = r.volunteer_name || r.assigned_volunteer || "Unassigned";
        const distanceStr   = r.distance_km != null ? `${r.distance_km} km away` : "";
        const scoreStr      = r.score != null ? `Score: ${r.score}` : "";
        const isAssigned    = r.status === "assigned";

        let resolveBtn = "";
        if (isAssigned && assignmentId && volunteerId) {
            resolveBtn = `
                <button
                    onclick="resolve('${needId}', '${volunteerId}', '${assignmentId}')"
                    style="margin-top:10px; padding:6px 14px; background:#e74c3c;
                           color:#fff; border:none; border-radius:5px; cursor:pointer; font-weight:600;">
                    Mark Resolved
                </button>`;
        }

        const card = document.createElement("div");
        card.className = "report-card";
        card.innerHTML = `
            <div class="report-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <h3 style="margin:0;">${r.disaster_type || r.category || "Emergency"}</h3>
                ${severityBadge(severity)}
            </div>

            <p style="margin:4px 0; color:#555; font-size:0.9rem;">${r.summary_en || r.description || ""}</p>
            <p style="margin:4px 0; font-size:0.85rem; color:#777;">
                📍 ${r.location_text || "Unknown location"}
            </p>

            <div style="display:flex; gap:16px; margin-top:8px; font-size:0.85rem;">
                <span>Status: <b>${r.status || "pending"}</b></span>
                <span>Assigned: <b>${volunteerName}</b></span>
                ${distanceStr ? `<span>📏 ${distanceStr}</span>` : ""}
                ${scoreStr    ? `<span>⚡ ${scoreStr}</span>`     : ""}
            </div>

            ${resolveBtn}
        `;
        container.appendChild(card);
    });
}

function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("auth_token");
    localStorage.removeItem("volunteer_id");
    localStorage.removeItem("name");
    window.location.href = "index.html";
}

// Init
loadReports();