/* frontend/js/volunteers.js */
let allVolunteers = [];
let currentMainFilter = "all"; // "all" | "available" | "busy"

// ── Data loading ───────────────────────────────────────────────
async function loadVolunteers() {
    const loadingEl = document.getElementById("reports-loading");
    if (loadingEl) loadingEl.style.display = "flex";

    try {
        const response = await ApiService.getVolunteers();

        // /volunteers returns a plain array; ApiService wraps it as { ok, data }
        // Handle both shapes defensively
        let data = null;
        if (response && response.ok && response.data !== undefined) {
            data = response.data;
        } else if (Array.isArray(response)) {
            data = response;
        } else {
            console.error("NO DATA FROM API");
            allVolunteers = [];
            renderVolunteers([]);
            return;
        }

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
        if (loadingEl) loadingEl.style.display = "none";
    }
}

// ── Stats panel ──────────────────────────────────────────────────────
function updateStats() {
    const total = allVolunteers.length;
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
        if (card) {
            if (t === matchType) {
                card.classList.add("bg-surface-container-low", "shadow-sm");
            } else {
                card.classList.remove("bg-surface-container-low", "shadow-sm");
            }
        }
    });
    
    // Update filter buttons
    document.querySelectorAll(".filter-btn").forEach(btn => {
        btn.classList.remove("bg-primary", "text-on-primary");
        btn.classList.add("hover:bg-surface-container-low", "text-on-surface-variant");
    });
    
    const activeBtn = document.getElementById("filter-" + type);
    if (activeBtn) {
        activeBtn.classList.add("bg-primary", "text-on-primary");
        activeBtn.classList.remove("hover:bg-surface-container-low", "text-on-surface-variant");
    }

    renderVolunteers(getFilteredSet());
}

// ── Secondary filter buttons ───────────────────────────
function filterVolunteers(type) {
    applyMainFilter(type);
}

// ── Render — Tailwind-based grid cards ─────────────────────────────────────────
function renderVolunteers(volunteers) {
    const container = document.getElementById("reportsList");
    if (!container) return;
    container.innerHTML = "";

    if (allVolunteers.length === 0) {
        container.innerHTML = `<div class="col-span-full text-center text-text-muted py-12">📭 No volunteers available.</div>`;
        return;
    }

    if (volunteers.length === 0) {
        container.innerHTML = `<div class="col-span-full text-center text-text-muted py-12">✅ No volunteers match the current filter.</div>`;
        return;
    }

    volunteers.forEach(v => {
        const name = v.name || v.volunteer_name || v.full_name || "Unknown Volunteer";
        const skill = (Array.isArray(v.skills) ? v.skills.join(" • ") : v.skills) || v.role || "General Responder";
        const location = v.location || v.area || v.city || "";
        const phone = v.phone || v.contact || "";
        const isAvailable = v.available === true || String(v.available).toLowerCase() === "true";
        const isTier1 = (v.ngo_verified === true || String(v.ngo_verified).toLowerCase() === "true") || 
                        (Array.isArray(v.credential_tags) && v.credential_tags.length > 0) || 
                        !!v.ngo_id;
                        
        const tierText = isTier1 ? "Tier 1 - NGO Verified" : "Tier 2 - Community Volunteer";
        const badgeClass = isTier1 ? "bg-primary-container/10 text-primary" : "bg-surface-container text-on-surface-variant";
        const tierBadgeHTML = `<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase shrink-0 ${badgeClass}">${tierText}</span>`;

        const card = document.createElement("div");
        card.className = "glass-card p-6 rounded-xl shadow-sm hover:shadow-md transition-all flex flex-col justify-between gap-4";

        card.innerHTML = `
            <div>
                <div class="flex justify-between items-start mb-2 gap-2 flex-wrap">
                    <h3 class="font-headline-md text-base text-text-main font-bold leading-snug">${escHtml(name)}</h3>
                    <div class="flex gap-1 items-center shrink-0">
                        ${tierBadgeHTML}
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold text-white uppercase shrink-0 ${isAvailable ? 'bg-safety-green' : 'bg-critical-red'}">
                            ${isAvailable ? "Available" : "Busy"}
                        </span>
                    </div>
                </div>
                <p class="text-body-md text-sm text-text-muted mt-1 leading-relaxed">${escHtml(skill)}</p>
            </div>
            <div class="flex flex-col gap-2 pt-4 border-t border-border-gray text-label-sm text-text-muted">
                ${location ? `
                <div class="flex items-center gap-1.5">
                    <span class="material-symbols-outlined text-[16px] text-primary">location_on</span>
                    <span>${escHtml(location)}</span>
                </div>` : ""}
                ${phone ? `
                <div class="flex items-center gap-1.5">
                    <span class="material-symbols-outlined text-[16px] text-primary">phone</span>
                    <span>${escHtml(phone)}</span>
                </div>` : ""}
            </div>
        `;

        container.appendChild(card);
    });
}

function escHtml(str) {
    const div = document.createElement('div');
    div.textContent = String(str || '');
    return div.innerHTML;
}

// Expose filter functions globally for layout onclick buttons
window.filterVolunteers = filterVolunteers;
window.applyMainFilter = applyMainFilter;

document.addEventListener("DOMContentLoaded", loadVolunteers);
