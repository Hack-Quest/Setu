/* frontend/js/ngos.js */
let allNGOs = [];
let currentMainFilter = "all"; // "all" | "verified" | "unverified"

// ── Data loading ───────────────────────────────────────────────
async function loadNGOs() {
    const loadingEl = document.getElementById("reports-loading");
    if (loadingEl) loadingEl.style.display = "flex";

    try {
        const response = await ApiService.getNGOs();
        console.log("📥 GET NGOs API Response:", response);

        if (!response || (!response.data && !Array.isArray(response))) {
            console.error("NO DATA FROM API");
            allNGOs = [];
            renderNGOs([]);
            return;
        }

        const data = response.data || response;
        console.log("🎯 Processed NGO Data:", data);

        // Normalize Data
        if (Array.isArray(data)) {
            allNGOs = data;
        } else if (data && Array.isArray(data.ngos)) {
            allNGOs = data.ngos;
        } else if (data && Array.isArray(data.data)) {
            allNGOs = data.data;
        } else {
            console.error("UNKNOWN DATA FORMAT:", data);
            allNGOs = [];
        }

        filterNGOs("all");

    } catch (err) {
        console.error("LOAD ERROR:", err);
        allNGOs = [];
        renderNGOs([]);
    } finally {
        if (loadingEl) loadingEl.style.display = "none";
    }
}

// ── Filter logic ───────────────────────────────────────────────
function filterNGOs(type) {
    currentMainFilter = type;

    // Update active state on buttons
    document.querySelectorAll(".filter-btn").forEach(btn => {
        btn.classList.remove("bg-primary", "text-on-primary");
        btn.classList.add("hover:bg-surface-container-low", "text-on-surface-variant");
    });
    
    const activeBtn = document.getElementById("filter-" + type);
    if (activeBtn) {
        activeBtn.classList.add("bg-primary", "text-on-primary");
        activeBtn.classList.remove("hover:bg-surface-container-low", "text-on-surface-variant");
    }

    if (type === "all") {
        renderNGOs(allNGOs);
    } else if (type === "verified") {
        renderNGOs(allNGOs.filter(n => n.verified === true || String(n.verified).toLowerCase() === "true"));
    } else {
        renderNGOs(allNGOs.filter(n => !(n.verified === true || String(n.verified).toLowerCase() === "true")));
    }
}

// ── Render — Tailwind-based grid cards ─────────────────────────────────────────
function renderNGOs(ngos) {
    const container = document.getElementById("reportsList");
    if (!container) return;
    container.innerHTML = "";

    if (allNGOs.length === 0) {
        container.innerHTML = `<div class="col-span-full text-center text-text-muted py-12">📭 No NGOs available.</div>`;
        return;
    }

    if (ngos.length === 0) {
        container.innerHTML = `<div class="col-span-full text-center text-text-muted py-12">✅ No NGOs match the current filter.</div>`;
        return;
    }

    ngos.forEach(ngo => {
        const ngoName = ngo.ngo_name || ngo.organization_name || "Unnamed NGO";
        const description = ngo.description || ngo.type || ngo.category || ngo.ngo_type
            || (ngo.owner_name ? `Owner: ${ngo.owner_name}` : "")
            || "Humanitarian aid response partner.";
        const region = ngo.region || ngo.area || ngo.city || ngo.location || "";
        const contact = ngo.contact || ngo.email || ngo.phone || "";
        const isVerified = ngo.verified === true || String(ngo.verified).toLowerCase() === "true";

        const card = document.createElement("div");
        card.className = "glass-card p-6 rounded-xl shadow-sm hover:shadow-md transition-all flex flex-col justify-between gap-4";

        card.innerHTML = `
            <div>
                <div class="flex justify-between items-start mb-2 gap-2">
                    <h3 class="font-headline-md text-base text-text-main font-bold leading-snug">${escHtml(ngoName)}</h3>
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold text-white uppercase shrink-0 ${isVerified ? 'bg-safety-green' : 'bg-tertiary'}">
                        ${isVerified ? "Verified" : "Pending"}
                    </span>
                </div>
                <p class="text-body-md text-sm text-text-muted mt-1 leading-relaxed">${escHtml(description)}</p>
            </div>
            <div class="flex flex-col gap-2 pt-4 border-t border-border-gray text-label-sm text-text-muted">
                ${region ? `
                <div class="flex items-center gap-1.5">
                    <span class="material-symbols-outlined text-[16px] text-primary">location_on</span>
                    <span>${escHtml(region)}</span>
                </div>` : ""}
                ${contact ? `
                <div class="flex items-center gap-1.5">
                    <span class="material-symbols-outlined text-[16px] text-primary">mail</span>
                    <span>${escHtml(contact)}</span>
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

// Expose functions globally for layout onclick buttons
window.filterNGOs = filterNGOs;

document.addEventListener("DOMContentLoaded", loadNGOs);
