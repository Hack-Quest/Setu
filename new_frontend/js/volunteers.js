/* js/volunteers.js */
(function () {
    let allVolunteers = [];

    // ── Render helpers ──────────────────────────────────────────────
    function renderCard(v) {
        // Gracefully handle varying API shapes
        const name     = v.name || v.volunteer_name || v.full_name || "Unknown Volunteer";
        const skill    = v.skill || v.skills || v.role || "Volunteer";
        const location = v.location || v.area || v.city || "";
        const phone    = v.phone || v.contact || "";
        const tier     = v.tier || v.tier_level || null;

        const tierHtml = tier
            ? `<span class="tier-badge tier-${tier}">Tier ${tier}</span>`
            : "";

        return `
            <div class="vol-card">
                <div class="vol-card__avatar">🤝</div>
                <div class="vol-card__name" title="${name}">${name}</div>
                <div class="vol-card__skill">${skill}</div>
                <div class="vol-card__meta">
                    ${location ? `<span>📍 ${location}</span>` : ""}
                    ${phone    ? `<span>📞 ${phone}</span>`    : ""}
                </div>
                ${tierHtml}
            </div>
        `;
    }

    function showGrid(data) {
        document.getElementById("vol-loading").style.display = "none";
        if (!data || data.length === 0) {
            document.getElementById("vol-empty").style.display = "flex";
            return;
        }
        const grid = document.getElementById("vol-grid");
        grid.style.display = "grid";
        grid.innerHTML = data.map(renderCard).join("");
        document.getElementById("vol-total-badge").textContent =
            `${data.length} volunteer${data.length !== 1 ? "s" : ""}`;
    }

    function showError(msg, is404 = false) {
        document.getElementById("vol-loading").style.display = "none";
        const err = document.getElementById("vol-error");
        err.style.display = "flex";
        const friendlyMsg = is404
            ? "⚠️ Volunteer data is not available yet — the backend endpoint is being deployed. Please try again shortly."
            : "⚠️ " + (msg || "Unable to load volunteers.");
        document.getElementById("vol-error-msg").textContent = friendlyMsg;
        // Add retry button if not already present
        if (!document.getElementById("vol-retry-btn")) {
            const btn = document.createElement("button");
            btn.id = "vol-retry-btn";
            btn.textContent = "↻ Retry";
            btn.style.cssText = "margin-top:12px;padding:8px 20px;background:#ff5c00;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600;";
            btn.onclick = () => {
                err.style.display = "none";
                document.getElementById("vol-loading").style.display = "flex";
                init();
            };
            err.appendChild(btn);
        }
    }

    // ── Search filter ───────────────────────────────────────────────
    function applySearch(query) {
        const q = query.toLowerCase().trim();
        const filtered = q
            ? allVolunteers.filter(v =>
                JSON.stringify(v).toLowerCase().includes(q))
            : allVolunteers;

        const grid = document.getElementById("vol-grid");
        const empty = document.getElementById("vol-empty");

        if (filtered.length === 0) {
            grid.style.display = "none";
            empty.style.display = "flex";
        } else {
            empty.style.display = "none";
            grid.style.display = "grid";
            grid.innerHTML = filtered.map(renderCard).join("");
        }
        document.getElementById("vol-total-badge").textContent =
            `${filtered.length} volunteer${filtered.length !== 1 ? "s" : ""}`;
    }

    // ── Bootstrap ───────────────────────────────────────────────────
    async function init() {
        try {
            const res = await ApiService.getVolunteers();
            if (!res.ok) {
                showError(res.error);
                return;
            }
            // API might return array directly or wrapped in a key
            allVolunteers = Array.isArray(res.data)
                ? res.data
                : (res.data.volunteers || res.data.data || []);

            showGrid(allVolunteers);
        } catch (err) {
            showError(err.message);
            console.error("volunteers.js error:", err);
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        init();
        document.getElementById("vol-search")
            .addEventListener("input", e => applySearch(e.target.value));
    });
})();
