/* js/reports.js */
const API_BASE = window.SETU_API_BASE_URL || "";
let allReports      = [];
let currentMainFilter   = localStorage.getItem("reports_filter") || "total";
localStorage.removeItem("reports_filter"); // clear after use
let currentSeverity     = "all";      // "all" | "critical" | "high" | "medium"

// ── Data loading (API call UNCHANGED) ───────────────────────────────
async function loadReports() {
    document.getElementById("reports-loading").style.display = "flex";

    try {
        const response = await ApiService.getReports();

        console.log("RAW API RESPONSE:", response);
        console.log("RAW DATA:", response ? response.data : undefined);

        if (!response || (!response.data && !Array.isArray(response))) {
            console.error("NO DATA FROM API");
            allReports = [];
            renderReports([]);
            return;
        }

        const res = response.data || response;

        console.log("TYPE:", typeof res);
        console.log("IS ARRAY:", Array.isArray(res));
        console.log("REPORTS FIELD:", res?.reports);
        console.log("DATA FIELD:", res?.data);

        // ✅ Handle all formats safely
        if (Array.isArray(res)) {
            allReports = res;
        } else if (res && Array.isArray(res.data)) {
            allReports = res.data;
        } else if (res && Array.isArray(res.reports)) {
            allReports = res.reports;
        } else {
            console.error("UNKNOWN DATA FORMAT:", res);
            allReports = [];
        }

        console.log("REPORTS RECEIVED:", allReports);
        if (allReports.length > 0) {
            console.log("SAMPLE REPORT:", allReports[0]);
        }

        updateStats();
        applyMainFilter(currentMainFilter);

    } catch (err) {
        console.error("LOAD ERROR:", err);
        allReports = [];
        renderReports([]);
    } finally {
        document.getElementById("reports-loading").style.display = "none";
    }
}


// ── Stats panel ──────────────────────────────────────────────────────
function updateStats() {
    const total = allReports.length;
    const assigned = allReports.filter(r => r.assigned === true).length;
    const unassigned = total - assigned;

    console.log("STATS:", { total, assigned, unassigned });

    const el = id => document.getElementById(id);
    if (el("totalReports"))    el("totalReports").textContent    = total;
    if (el("unassignedCount")) el("unassignedCount").textContent = unassigned;
    if (el("assignedCount"))   el("assignedCount").textContent   = assigned;
}


// ── Compute the set to show based on both active filters ─────────────
function getFilteredSet() {
    let base = allReports;

    // Main filter (total / unassigned / assigned)
    if (currentMainFilter === "unassigned") {
        base = base.filter(r => !r.assigned);
    } else if (currentMainFilter === "assigned") {
        base = base.filter(r => r.assigned === true);
    }

    // Severity sub-filter
    if (currentSeverity !== "all") {
        base = base.filter(r => (r.severity || "").toLowerCase() === currentSeverity);
    }

    return base;
}


// ── Main filter (stat card clicks) ──────────────────────────────────
function applyMainFilter(type) {
    currentMainFilter = type;

    // Update stat card active state
    ["total", "unassigned", "assigned"].forEach(t => {
        const card = document.getElementById("stat-" + t);
        if (card) card.classList.toggle("rpt-stat-card--active", t === type);
    });

    const filtered = getFilteredSet();
    console.log("FILTERED:", type, filtered.length);
    renderReports(filtered);
}


// ── Severity filter (existing onclick buttons, signature UNCHANGED) ──
function filterReports(type) {
    currentSeverity = type;

    document.querySelectorAll(".filter-btn").forEach(btn => {
        btn.classList.remove("filter-btn--active");
    });
    const active = document.getElementById("filter-" + type);
    if (active) active.classList.add("filter-btn--active");

    renderReports(getFilteredSet());
}


// ── Render — text-based list ─────────────────────────────────────────
function renderReports(reports) {
    const container = document.getElementById("reportsList");
    if (!container) return;
    container.innerHTML = "";

    // Empty state: no data at all
    if (allReports.length === 0) {
        container.innerHTML = `<p class="empty-text">📭 No reports available</p>`;
        return;
    }

    // Empty state: filter returns nothing
    if (reports.length === 0) {
        container.innerHTML = `<p class="empty-text">✅ No reports match the current filter.</p>`;
        return;
    }

    reports.forEach(r => {
        const severity = (r.severity || "low").toLowerCase();

        // ── Smart field resolution ──
        const title = (r.description || r.summary || r.disaster_type || "No description").slice(0, 60);
        const location = r.location || r.location_text || r.area || r.address || "";

        // ── Clean Status Logic ──
        const isAssigned = r.assigned === true || (r.status && r.status.toLowerCase() === "assigned");
        const statusText = isAssigned ? "📌 ASSIGNED" : "📍 UNASSIGNED";

        // ── Handle Volunteers Data ──
        let volunteers = [];
        if (Array.isArray(r.assigned_volunteers) && r.assigned_volunteers.length > 0) {
            volunteers = r.assigned_volunteers;
        } else if (Array.isArray(r.assigned_to) && r.assigned_to.length > 0) {
            volunteers = r.assigned_to;
        } else if (isAssigned) {
            // 🔥 FORCE fallback (IMPORTANT)
            volunteers = ["Volunteer"];
        }
        
        const volunteerCount = volunteers.length;
        
        // ── Extract Names (Future Ready) ──
        let volunteerNames = [];
        if (volunteerCount > 0) {
            volunteerNames = volunteers.map(v => {
                if (typeof v === "string") return v === "Volunteer" ? null : v;
                return v.name || v.username || null;
            }).filter(Boolean); // Filter out nulls so we don't show "(Volunteer)"
        }

        // ── Tier badge (preserve existing logic) ──
        const tier = r.volunteer_tier || "";
        let badgeClass = "tier-badge";
        if (tier.includes("Tier 1")) badgeClass += " tier-1";
        else if (tier.includes("Tier 2")) badgeClass += " tier-2";
        const tierBadgeHTML = tier ? `<span class="${badgeClass}">${tier}</span>` : "";

        const item = document.createElement("div");
        item.className = "report-item";
        item.dataset.severity = severity;

        item.innerHTML = `
            <div class="report-item-header">
                <h3>${title}... ${tierBadgeHTML}</h3>
                <span class="severity-pill ${severity}">${severity.toUpperCase()}</span>
            </div>
            <p class="desc">${r.description || ""}</p>
            <div class="report-item-meta">
                ${location ? `<span>📍 ${location}</span>` : ""}
                <span class="status">${statusText}</span>
                ${
                    isAssigned && volunteerCount > 0
                    ? `<span class="volunteers">👥 ${volunteerCount} volunteer${volunteerCount > 1 ? "s" : ""} ${volunteerNames.length > 0 ? `(${volunteerNames.join(", ")})` : ""}</span>`
                    : ""
                }
            </div>
        `;

        container.appendChild(item);
    });
}


loadReports();