const API_BASE = window.SETU_API_BASE_URL || "";
requireAuth();

// 🔓 Logout
function logout() {
    localStorage.clear();
    window.location.href = "index.html";
}



// 📌 Volunteer ID
const volunteerId = localStorage.getItem("volunteer_id");

// 👤 Load Profile + Assignment
async function loadProfile() {

    if (!volunteerId) {
        document.getElementById("assignment").innerText =
            "No volunteer ID found. Please login again.";
        return;
    }

    // 👤 Basic info (fallback safe)
    const name = localStorage.getItem("name") || "Volunteer";
    document.getElementById("name").innerText = name;
    document.getElementById("skills").innerText = "Skills: Assigned dynamically";
    document.getElementById("ngo").innerText = "NGO: Connected";
    document.getElementById("status").innerText = "Status: Checking...";

    // The assignment loading is now handled by initDashboard()
}

// ─── Dynamic Dashboard Population ─────────────────────────────────────────────
function getSeverityClass(severity) {
    if (!severity) return "severity-low";
    const s = severity.toLowerCase();
    if (s === "critical" || s === "very high" || s === "high") return "severity-high";
    if (s === "medium") return "severity-medium";
    return "severity-low";
}

async function initDashboard() {
    const container = document.getElementById("volunteerDashboardBody");
    if (!container) return;
    container.innerHTML = "<tr><td colspan='6' style='padding: 12px; text-align: center;'>Loading...</td></tr>";

    const response = await ApiService.getDashboard();
    const data = response && response.ok ? response.data : null;

    if (!data) {
        container.innerHTML = "<tr><td colspan='6' style='padding: 12px; text-align: center;'>⚠️ Could not load dashboard data.</td></tr>";
        return;
    }

    const reports = data.reports || [];
    container.innerHTML = "";

    if (!reports.length) {
        container.innerHTML = "<tr><td colspan='6' style='padding: 12px; text-align: center;'>No active assignments.</td></tr>";
        return;
    }

    reports.forEach(r => {
        const severity = (r.severity || "low").toLowerCase();
        const severityClass = getSeverityClass(severity);
        const tr = document.createElement("tr");
        tr.dataset.needId = r.id;
        tr.style.borderBottom = "1px solid #2a2a3c";
        const rName = r.reporter_name || "Unknown";
        const isAssigned = r.status === "assigned";
        const isResolved = r.status === "resolved";

        // Actions column: show Resolve if assigned, Accept if open
        let actionBtn = "—";
        if (isAssigned && r.assignment_id) {
            actionBtn = `<button
                onclick="resolveAssignment('${r.id}','${r.assignment_id}',this)"
                style="padding:5px 12px;background:#e74c3c;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:0.78rem;font-weight:600;">
                ✔ Resolve
            </button>`;
        } else if (!isResolved) {
            actionBtn = `<button
                onclick="acceptNeed('${r.id}',this)"
                style="padding:5px 12px;background:#3b82f6;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:0.78rem;font-weight:600;">
                ⚡ Accept
            </button>`;
        }

        tr.innerHTML = `
            <td style="padding: 12px;">${rName}</td>
            <td style="padding: 12px;">${r.location || "N/A"}</td>
            <td style="padding: 12px;">${r.disaster_type || "Emergency"}</td>
            <td style="padding: 12px;">${r.summary_en || r.description || ""}</td>
            <td class="${severityClass}" style="padding: 12px;">${r.status || "pending"}</td>
            <td style="padding: 12px;">${actionBtn}</td>
        `;
        container.appendChild(tr);
    });
}

// ─── Accept Need (Volunteer) ───────────────────────────────────────────────────
async function acceptNeed(needId, btn) {
    if (btn) { btn.disabled = true; btn.textContent = "Accepting…"; }

    const response = await ApiService.acceptNeed(needId);

    if (response && response.ok) {
        showToast("Need accepted — you are now assigned!", "success");
        // Update status cell and swap button to Resolve in the same row
        const row = btn ? btn.closest("tr") : null;
        if (row) {
            const statusCell = row.querySelector("td:nth-child(5)");
            if (statusCell) {
                statusCell.textContent = "assigned";
                statusCell.className = "severity-high"; // high urgency once accepted
            }
            const assignmentId = response.data?.assignment_id || "";
            btn.closest("td").innerHTML = `<button
                onclick="resolveAssignment('${needId}','${assignmentId}',this)"
                style="padding:5px 12px;background:#e74c3c;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:0.78rem;font-weight:600;">
                ✔ Resolve
            </button>`;
        }
    } else {
        showToast(response?.error || "Could not accept need — please try again.", "error");
        if (btn) { btn.disabled = false; btn.textContent = "⚡ Accept"; }
    }
}

// ─── Resolve Assignment (Volunteer) ───────────────────────────────────────────
async function resolveAssignment(needId, assignmentId, btn) {
    if (!confirm("Are you sure you want to mark this assignment as resolved?"))
        return;

    if (btn) { btn.disabled = true; btn.textContent = "Resolving…"; }

    const response = await ApiService.resolveAssignment(assignmentId, {
        need_id: needId,
        volunteer_id: volunteerId
    });

    if (response && response.ok) {
        showToast("Assignment resolved — great work! 🎉", "success");
        const row = btn ? btn.closest("tr") : null;
        if (row) {
            row.style.transition = "opacity 0.4s ease";
            row.style.opacity = "0";
            row.addEventListener("transitionend", () => row.remove(), { once: true });
        }
        // Also update the profile status chip
        const statusEl = document.getElementById("status");
        if (statusEl) statusEl.innerText = "Status: Available";
    } else {
        showToast(response?.error || "Failed to resolve assignment.", "error");
        if (btn) { btn.disabled = false; btn.textContent = "✔ Resolve"; }
    }
}

// 🚀 INIT
loadProfile();
initDashboard();