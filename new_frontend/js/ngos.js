/* js/ngos.js */
(function () {
    let allNGOs = [];

    // ── Render helpers ──────────────────────────────────────────────
    function renderCard(n) {
        const name     = n.name || n.ngo_name || n.organization || "Unknown NGO";
        const type     = n.type || n.category || n.ngo_type || "NGO";
        const region   = n.region || n.area || n.city || n.location || "";
        const contact  = n.contact || n.email || n.phone || "";
        const verified = n.verified || n.is_verified || false;

        const verifiedBadge = verified
            ? `<span class="tier-badge tier-1">✓ Verified</span>`
            : "";

        return `
            <div class="ngo-card">
                <div class="ngo-card__icon">🏢</div>
                <div class="ngo-card__name" title="${name}">${name}</div>
                <div class="ngo-card__type">${type}</div>
                <div class="ngo-card__meta">
                    ${region  ? `<span>📍 ${region}</span>`  : ""}
                    ${contact ? `<span>📬 ${contact}</span>` : ""}
                </div>
                ${verifiedBadge}
            </div>
        `;
    }

    function showGrid(data) {
        document.getElementById("ngo-loading").style.display = "none";
        if (!data || data.length === 0) {
            document.getElementById("ngo-empty").style.display = "flex";
            return;
        }
        const grid = document.getElementById("ngo-grid");
        grid.style.display = "grid";
        grid.innerHTML = data.map(renderCard).join("");
        document.getElementById("ngo-total-badge").textContent =
            `${data.length} NGO${data.length !== 1 ? "s" : ""}`;
    }

    function showError(msg, is404 = false) {
        document.getElementById("ngo-loading").style.display = "none";
        const err = document.getElementById("ngo-error");
        err.style.display = "flex";
        const friendlyMsg = is404
            ? "⚠️ NGO data is not available yet — the backend endpoint is being deployed. Please try again shortly."
            : "⚠️ " + (msg || "Unable to load NGOs.");
        document.getElementById("ngo-error-msg").textContent = friendlyMsg;
        if (!document.getElementById("ngo-retry-btn")) {
            const btn = document.createElement("button");
            btn.id = "ngo-retry-btn";
            btn.textContent = "↻ Retry";
            btn.style.cssText = "margin-top:12px;padding:8px 20px;background:#ff5c00;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600;";
            btn.onclick = () => {
                err.style.display = "none";
                document.getElementById("ngo-loading").style.display = "flex";
                init();
            };
            err.appendChild(btn);
        }
    }

    // ── Search filter ───────────────────────────────────────────────
    function applySearch(query) {
        const q = query.toLowerCase().trim();
        const filtered = q
            ? allNGOs.filter(n =>
                JSON.stringify(n).toLowerCase().includes(q))
            : allNGOs;

        const grid  = document.getElementById("ngo-grid");
        const empty = document.getElementById("ngo-empty");

        if (filtered.length === 0) {
            grid.style.display = "none";
            empty.style.display = "flex";
        } else {
            empty.style.display = "none";
            grid.style.display = "grid";
            grid.innerHTML = filtered.map(renderCard).join("");
        }
        document.getElementById("ngo-total-badge").textContent =
            `${filtered.length} NGO${filtered.length !== 1 ? "s" : ""}`;
    }

    // ── Bootstrap ───────────────────────────────────────────────────
    async function init() {
        try {
            const res = await ApiService.getNGOs();
            if (!res.ok) {
                showError(res.error);
                return;
            }
            allNGOs = Array.isArray(res.data)
                ? res.data
                : (res.data.ngos || res.data.data || []);

            showGrid(allNGOs);
        } catch (err) {
            showError(err.message);
            console.error("ngos.js error:", err);
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        init();
        document.getElementById("ngo-search")
            .addEventListener("input", e => applySearch(e.target.value));
    });
})();
