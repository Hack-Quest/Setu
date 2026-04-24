const API_BASE = window.SETU_API_BASE_URL || "";
requireAuth();

// ─── Auth ───────────────────────────────────────────────────────────────────
function logout() {
    localStorage.clear();
    window.location.href = "index.html";
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
    const response = await ApiService.getHealth();
    const data = response && response.ok ? response.data : null;
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

    const response = await ApiService.runMatch();
    const data = response && response.ok ? response.data : null;

    if (btn) { btn.disabled = false; btn.textContent = "⚡ Run Matching Engine"; }

    if (!data) {
        alert("Matching engine failed — check console.");
        return;
    }

    const matches = data.matches || [];
    let assigned = 0, unmatched = 0;
    matches.forEach(m => m.status === "assigned" ? assigned++ : unmatched++);

    alert(`✅ Matching complete!\n\nAssigned: ${assigned}\nUnmatched / Escalated: ${unmatched}`);
    initDashboard(); // refresh the list
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
    const container = document.getElementById("ngoDashboardBody");
    if (!container) return;
    container.innerHTML = "<tr><td colspan='5' style='padding: 12px; text-align: center;'>Loading...</td></tr>";

    const response = await ApiService.getDashboard();
    const data = response && response.ok ? response.data : null;

    if (!data) {
        container.innerHTML = "<tr><td colspan='5' style='padding: 12px; text-align: center;'>⚠️ Could not load reports.</td></tr>";
        return;
    }

    const reports = data.reports || [];
    reports.sort((a, b) =>
        (SEVERITY_ORDER[(a.severity || "low").toLowerCase()] ?? 5) -
        (SEVERITY_ORDER[(b.severity || "low").toLowerCase()] ?? 5)
    );

    container.innerHTML = "";

    if (!reports.length) {
        container.innerHTML = "<tr><td colspan='5' style='padding: 12px; text-align: center;'>No active reports.</td></tr>";
        return;
    }

    reports.forEach(r => {
        const severity = (r.severity || "low").toLowerCase();
        const severityClass = getSeverityClass(severity);
        const rName = r.reporter_name || r.volunteer_name || r.assigned_volunteer || "Auto-assigned";
        
        let resolveBtn = "";
        const isAssigned = r.status === "assigned";
        if (isAssigned && r.assignment_id && r.volunteer_id) {
            resolveBtn = `<br><button onclick="resolve('${r.id}','${r.volunteer_id}','${r.assignment_id}',this)"
                style="margin-top:5px;padding:4px 10px;background:#e74c3c;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:0.75rem;">
                Mark Resolved</button>`;
        }

        const tr = document.createElement("tr");
        tr.style.borderBottom = "1px solid #2a2a3c";
        tr.innerHTML = `
            <td style="padding: 12px;">${rName}</td>
            <td style="padding: 12px;">${r.location || "N/A"}</td>
            <td style="padding: 12px;">${r.disaster_type || "Emergency"} ${severityBadge(severity)}</td>
            <td style="padding: 12px;">${r.summary_en || r.description || ""}</td>
            <td class="${severityClass}" style="padding: 12px;">${r.status || "pending"} ${resolveBtn}</td>
        `;
        container.appendChild(tr);
    });
}

// ─── Resolve Assignment (NGO) ─────────────────────────────────────────────────
async function resolve(needId, volunteerId, assignmentId, btn) {
    if (!confirm("Mark this assignment as resolved?")) return;

    // Optimistic UX — disable button while the call is in flight
    if (btn) { btn.disabled = true; btn.textContent = "Resolving…"; }

    const response = await ApiService.resolveAssignment(assignmentId, {
        need_id: needId,
        volunteer_id: volunteerId
    });
    const res = response && response.ok ? response.data : null;

    if (res) {
        showToast("Assignment resolved — volunteer is now available.", "success");
        // Remove the row from the DOM locally without a full refresh
        const row = btn ? btn.closest("tr") : null;
        if (row) {
            row.style.transition = "opacity 0.4s ease";
            row.style.opacity = "0";
            row.addEventListener("transitionend", () => row.remove(), { once: true });
        } else {
            initDashboard();
        }
    } else {
        showToast(response?.error || "Resolve failed — please try again.", "error");
        if (btn) { btn.disabled = false; btn.textContent = "Mark Resolved"; }
    }
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
            // Skills may be a comma-separated string in Excel — normalise to array
            const rawSkills = row["skills"] || row["Skills"] || "";
            const skillsArray = Array.isArray(rawSkills)
                ? rawSkills
                : String(rawSkills).split(",").map(s => s.trim()).filter(Boolean);

            const payload = {
                name: row["name"] || row["Name"] || row["volunteer_name"] || "Unknown",
                phone: String(row["phone"] || row["Phone"] || "0000000000"),
                location: row["location"] || row["Location"] || "",
                skills: skillsArray,
                // NGO bulk-add doesn't require volunteer email/password — use placeholder;
                // the backend /volunteer route strips privileged fields anyway.
                email: row["email"] || row["Email"] || `${Date.now()}@ngo-upload.internal`,
                password: "BulkUpload!1",
                ngo_id: row["ngo_id"] || row["NGO ID"] || null
            };

            try {
                const res = await ApiService.postVolunteer(payload);
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
initDashboard();