const API_BASE = window.SETU_API_BASE_URL || "";

// ─── Auth ───────────────────────────────────────────────────────────────────
function getToken() {
    return localStorage.getItem("auth_token") || localStorage.getItem("token") || null;
}

function logout() {
    localStorage.clear();
    window.location.href = "index.html";
}

// ─── API Helper ──────────────────────────────────────────────────────────────
async function api(endpoint, options = {}) {
    try {
        const token = getToken();
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch(`${API_BASE}${endpoint}`, { headers, ...options });

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

// ─── Severity Badge ──────────────────────────────────────────────────────────
const SEVERITY_ORDER = { critical: 0, "very high": 1, high: 2, medium: 3, low: 4 };

function severityBadge(severity) {
    const colors = {
        critical: "#c0392b", "very high": "#e74c3c",
        high: "#e67e22", medium: "#f1c40f", low: "#27ae60"
    };
    const bg = colors[severity] || "#999";
    return `<span style="background:${bg};color:#fff;padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:700;text-transform:uppercase;">${severity}</span>`;
}

// ─── Health Check ────────────────────────────────────────────────────────────
async function checkHealth() {
    const el = document.getElementById("healthStatus");
    if (!el) return;
    el.textContent = "Checking…";
    el.style.color = "#aaa";
    const data = await api("/health");
    if (data && data.status === "ok") {
        el.textContent = "● Backend Online";
        el.style.color = "#27ae60";
    } else {
        el.textContent = "● Backend Offline";
        el.style.color = "#e74c3c";
    }
}

// ─── Run Matching Engine ─────────────────────────────────────────────────────
async function runMatch() {
    const btn = document.getElementById("runMatchBtn");
    if (btn) { btn.disabled = true; btn.textContent = "Running…"; }

    const data = await api("/match");

    if (btn) { btn.disabled = false; btn.textContent = "⚡ Run Matching Engine"; }

    if (!data) {
        alert("Matching engine failed — check console.");
        return;
    }

    const matches = data.matches || [];
    let assigned = 0, unmatched = 0;
    matches.forEach(m => m.status === "assigned" ? assigned++ : unmatched++);

    alert(`✅ Matching complete!\n\nAssigned: ${assigned}\nUnmatched / Escalated: ${unmatched}`);
    loadReports(); // refresh the list
}

// ─── Load Reports ────────────────────────────────────────────────────────────
async function loadReports() {
    const container = document.getElementById("reportsList");
    container.innerHTML = "<p style='color:#aaa'>Loading…</p>";

    const data = await api("/dashboard/reports");

    if (!data) {
        container.innerHTML = "<p>⚠️ Could not load reports.</p>";
        return;
    }

    const reports = data.reports || data || [];
    reports.sort((a, b) =>
        (SEVERITY_ORDER[(a.severity || "low").toLowerCase()] ?? 5) -
        (SEVERITY_ORDER[(b.severity || "low").toLowerCase()] ?? 5)
    );
    renderReports(reports);
}

function renderReports(reports) {
    const container = document.getElementById("reportsList");
    container.innerHTML = "";

    if (!reports.length) {
        container.innerHTML = "<p>No active reports.</p>";
        return;
    }

    reports.forEach(r => {
        const severity = (r.severity || "low").toLowerCase();
        const volunteerName = r.volunteer_name || r.assigned_volunteer || "Auto-assigned";
        const isAssigned = r.status === "assigned";

        let resolveBtn = "";
        if (isAssigned && r.assignment_id && r.volunteer_id) {
            resolveBtn = `<button onclick="resolve('${r.id}','${r.volunteer_id}','${r.assignment_id}')"
                style="margin-top:10px;padding:6px 14px;background:#e74c3c;color:#fff;border:none;border-radius:5px;cursor:pointer;">
                Mark Resolved</button>`;
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

// ─── Resolve Assignment ───────────────────────────────────────────────────────
async function resolve(needId, volunteerId, assignmentId) {
    if (!confirm("Mark this assignment as resolved?")) return;

    const res = await api(`/assignment/${assignmentId}/resolve`, {
        method: "PATCH",
        body: JSON.stringify({ need_id: needId, volunteer_id: volunteerId })
    });

    if (res) loadReports();
    else alert("Resolve failed.");
}

// ─── Bulk Upload (Excel) ──────────────────────────────────────────────────────
async function handleExcelUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const statusEl = document.getElementById("uploadStatus");
    statusEl.textContent = "Parsing Excel file…";
    statusEl.style.color = "#f1c40f";

    try {
        const arrayBuffer = await file.arrayBuffer();
        const workbook = XLSX.read(arrayBuffer, { type: "array" });

        // Use first sheet
        const sheet = workbook.Sheets[workbook.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json(sheet, { defval: "" });

        if (!rows.length) {
            statusEl.textContent = "⚠️ No rows found in the file.";
            statusEl.style.color = "#e74c3c";
            return;
        }

        statusEl.textContent = `Found ${rows.length} volunteers. Uploading…`;

        let success = 0, failed = 0;

        for (const row of rows) {
            const payload = {
                volunteer_name: row["name"] || row["Name"] || row["volunteer_name"] || "Unknown",
                phone: String(row["phone"] || row["Phone"] || "0000000000"),
                location: row["location"] || row["Location"] || "",
                skills: row["skills"] || row["Skills"] || "",
                ngo_id: row["ngo_id"] || row["NGO ID"] || null
            };

            try {
                const res = await fetch(`${API_BASE}/volunteer_webhook`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                res.ok ? success++ : failed++;
            } catch {
                failed++;
            }
        }

        statusEl.textContent = `✅ Done — Uploaded: ${success} | Failed: ${failed}`;
        statusEl.style.color = success > 0 ? "#27ae60" : "#e74c3c";

    } catch (err) {
        console.error("Excel parse error:", err);
        statusEl.textContent = "❌ Failed to parse file.";
        statusEl.style.color = "#e74c3c";
    }

    // Reset input so same file can be re-uploaded if needed
    event.target.value = "";
}

// ─── Init ─────────────────────────────────────────────────────────────────────
checkHealth();
loadReports();