/* js/volunteers.js */
const API_BASE = window.SETU_API_BASE_URL || "";
let allVolunteers = [];
let currentMainFilter = "all"; // "all" | "available" | "busy"

// ── Data loading ───────────────────────────────────────────────
async function loadVolunteers() {
    document.getElementById("reports-loading").style.display = "flex";

    try {
        const response = await ApiService.getVolunteers();

        if (!response || (!response.data && !Array.isArray(response))) {
            console.error("NO DATA FROM API");
            allVolunteers = [];
            renderVolunteers([]);
            return;
        }

        const data = response.data || response;

        // Normalize Data
        if (Array.isArray(data)) {
            allVolunteers = data;
        } else if (data && Array.isArray(data.volunteers)) {
            allVolunteers = data.volunteers;
        } else if (data && Array.isArray(data.data)) {
            allVolunteers = data.data;
        } else {
            console.error("UNKNOWN DATA FORMAT:", data);
            allVolunteers = [];
        }

        updateStats();
        applyMainFilter("all");

    } catch (err) {
        console.error("LOAD ERROR:", err);
        allVolunteers = [];
        renderVolunteers([]);
    } finally {
        document.getElementById("reports-loading").style.display = "none";
    }
}

// ── Stats panel ──────────────────────────────────────────────────────
function updateStats() {
    const total = allVolunteers.length;
    // Default available to true if not explicitly false to be safe, or check truthy
    const available = allVolunteers.filter(v => v.available === true || String(v.available).toLowerCase() === "true").length;
    const busy = total - available;

    const el = id => document.getElementById(id);
    if (el("totalVolunteers")) el("totalVolunteers").textContent = total;
    if (el("availableCount"))  el("availableCount").textContent  = available;
    if (el("busyCount"))       el("busyCount").textContent       = busy;
}

// ── Compute the set to show based on active filter ─────────────
function getFilteredSet() {
    let base = allVolunteers;

    if (currentMainFilter === "available") {
        base = base.filter(v => v.available === true || String(v.available).toLowerCase() === "true");
    } else if (currentMainFilter === "busy") {
        base = base.filter(v => !(v.available === true || String(v.available).toLowerCase() === "true"));
    }

    return base;
}

// ── Main filter (stat card clicks) ──────────────────────────────────
function applyMainFilter(type) {
    if (type === "total") type = "all";
    currentMainFilter = type;

    // Update stat card active state
    ["total", "available", "busy"].forEach(t => {
        const card = document.getElementById("stat-" + t);
        const matchType = type === "all" ? "total" : type;
        if (card) card.classList.toggle("rpt-stat-card--active", t === matchType);
    });
    
    // Update filter buttons
    document.querySelectorAll(".filter-btn").forEach(btn => {
        btn.classList.remove("filter-btn--active");
    });
    const activeBtn = document.getElementById("filter-" + type);
    if (activeBtn) activeBtn.classList.add("filter-btn--active");

    renderVolunteers(getFilteredSet());
}

// ── Secondary filter buttons (from HTML) ───────────────────────────
function filterVolunteers(type) {
    applyMainFilter(type);
}

// ── Render — text-based list ─────────────────────────────────────────
function renderVolunteers(volunteers) {
    const container = document.getElementById("reportsList");
    if (!container) return;
    container.innerHTML = "";

    if (allVolunteers.length === 0) {
        container.innerHTML = `<p class="empty-text">📭 No volunteers available</p>`;
        return;
    }

    if (volunteers.length === 0) {
        container.innerHTML = `<p class="empty-text">✅ No volunteers match the current filter.</p>`;
        return;
    }

    volunteers.forEach(v => {
        const name = v.name || v.volunteer_name || v.full_name || "Unknown Volunteer";
        const skill = v.skill || v.skills || v.role || "No skills listed";
        const location = v.location || v.area || v.city || "";
        const phone = v.phone || v.contact || "";
        const isAvailable = v.available === true || String(v.available).toLowerCase() === "true";
        const isTier1 = (v.ngo_verified === true || String(v.ngo_verified).toLowerCase() === "true") || 
                        (Array.isArray(v.credential_tags) && v.credential_tags.length > 0) || 
                        !!v.ngo_id;
                        
        const tierText = isTier1 ? "Tier 1 - Verified Responder" : "Tier 2 - Community Volunteer";
        const badgeClass = isTier1 ? "tier-badge tier-1" : "tier-badge tier-2";
        const tierBadgeHTML = `<span class="${badgeClass}">${tierText}</span>`;

        const item = document.createElement("div");
        item.className = "report-item";

        item.innerHTML = `
            <div class="report-item-header">
                <h3>${name} ${tierBadgeHTML}</h3>
                <span class="severity-pill ${isAvailable ? 'low' : 'critical'}">${isAvailable ? "🟢 AVAILABLE" : "🔴 BUSY"}</span>
            </div>
            <p class="desc">${skill}</p>
            <div class="report-item-meta">
                ${location ? `<span>📍 ${location}</span>` : ""}
                ${phone ? `<span>📞 ${phone}</span>` : ""}
                <span class="status">${isAvailable ? "✅ Ready to Deploy" : "⛔ Currently Unavailable"}</span>
            </div>
        `;

        container.appendChild(item);
    });
}

loadVolunteers();
