const API_BASE = window.SETU_API_BASE_URL || "";
let allReports = [];

function openNeedForm() {
    window.open("https://forms.gle/YOUR_NEED_FORM", "_blank");
}

async function loadReports() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/reports`);

        const data = await res.json();
        allReports = data.reports || data;

        renderReports(allReports);

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

        card.innerHTML = `
            <div class="report-header">
                <h3>${r.disaster_type || "Emergency"}</h3>
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