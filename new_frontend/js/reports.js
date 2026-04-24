const API_BASE = window.SETU_API_BASE_URL || "";
let allReports = [];


async function loadReports() {
    try {
        const response = await ApiService.getReports();

        if (response.ok) {
            const data = response.data;
            allReports = data.reports || data;
            renderReports(allReports);
        } else {
            console.error(response.error);
        }

    } catch (err) {
        console.error(err);
    }
}

function renderReports(reports) {
    const container = document.getElementById("reportsList");
    container.innerHTML = "";

    reports.forEach(r => {

        const severity = (r.severity || "low").toLowerCase();

        const card = document.createElement("div");
        card.className = "report-card";

        const tier = r.volunteer_tier || "";
        let badgeClass = "tier-badge";
        if (tier.includes("Tier 1")) badgeClass += " tier-1";
        else if (tier.includes("Tier 2")) badgeClass += " tier-2";
        const tierBadgeHTML = tier ? `<span class="${badgeClass}">${tier}</span>` : "";

        card.innerHTML = `
            <div class="report-header">
                <h3>${r.disaster_type || "Emergency"} ${tierBadgeHTML}</h3>
                <span class="badge ${severity}">
                    ${severity.toUpperCase()}
                </span>
            </div>

            <p class="desc">${r.description || ""}</p>
            <p class="status">Status: ${r.status || ""}</p>
        `;

        container.appendChild(card);
    });
}

function filterReports(type) {
    if (type === "all") {
        renderReports(allReports);
    } else {
        const filtered = allReports.filter(r =>
            (r.severity || "").toLowerCase() === type
        );
        renderReports(filtered);
    }
}

loadReports();