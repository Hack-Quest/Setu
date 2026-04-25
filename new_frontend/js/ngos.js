/* js/ngos.js */
const API_BASE = window.SETU_API_BASE_URL || "";
let allNGOs = [];
let currentMainFilter = "all"; // "all" | "verified" | "unverified"

// ── Data loading ───────────────────────────────────────────────
async function loadNGOs() {
    document.getElementById("reports-loading").style.display = "flex";

    try {
        const response = await ApiService.getNGOs();

        if (!response || (!response.data && !Array.isArray(response))) {
            console.error("NO DATA FROM API");
            allNGOs = [];
            renderNGOs([]);
            return;
        }

        const data = response.data || response;

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
        document.getElementById("reports-loading").style.display = "none";
    }
}

// ── Filter logic ───────────────────────────────────────────────
function filterNGOs(type) {
    currentMainFilter = type;

    // Update active state on buttons
    document.querySelectorAll(".filter-btn").forEach(btn => {
        btn.classList.remove("filter-btn--active");
    });
    const activeBtn = document.getElementById("filter-" + type);
    if (activeBtn) activeBtn.classList.add("filter-btn--active");

    if (type === "all") {
        renderNGOs(allNGOs);
    } else if (type === "verified") {
        renderNGOs(allNGOs.filter(n => n.verified === true || String(n.verified).toLowerCase() === "true"));
    } else {
        renderNGOs(allNGOs.filter(n => !(n.verified === true || String(n.verified).toLowerCase() === "true")));
    }
}

// ── Render — text-based list ─────────────────────────────────────────
function renderNGOs(ngos) {
    const container = document.getElementById("reportsList");
    if (!container) return;
    container.innerHTML = "";

    if (allNGOs.length === 0) {
        container.innerHTML = `<p class="empty-text">📭 No NGOs available</p>`;
        return;
    }

    if (ngos.length === 0) {
        container.innerHTML = `<p class="empty-text">✅ No NGOs match the current filter.</p>`;
        return;
    }

    ngos.forEach(ngo => {
        // ── Prioritize NGO Name over Owner Name ──
        const ngoName = ngo.ngo_name || ngo.organization_name || ngo.organization || ngo.name || "NGO";
        
        const description = ngo.description || ngo.type || ngo.category || ngo.ngo_type || "No description available";
        const region = ngo.region || ngo.area || ngo.city || ngo.location || "";
        const contact = ngo.contact || ngo.email || ngo.phone || "";
        const isVerified = ngo.verified === true || String(ngo.verified).toLowerCase() === "true";

        const item = document.createElement("div");
        item.className = "report-item";

        item.innerHTML = `
            <div class="report-item-header">
                <h3>${ngoName}</h3>
                <span class="severity-pill ${isVerified ? 'low' : 'medium'}">${isVerified ? "🟢 VERIFIED" : "🟡 UNVERIFIED"}</span>
            </div>
            <p class="desc">${description}</p>
            <div class="report-item-meta">
                ${region ? `<span>📍 ${region}</span>` : ""}
                ${contact ? `<span>📬 ${contact}</span>` : ""}
                <span class="status">${isVerified ? "✅ Verified Organization" : "⚠️ Pending Verification"}</span>
            </div>
        `;

        container.appendChild(item);
    });
}

loadNGOs();
