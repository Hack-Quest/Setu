const API_BASE = "http://127.0.0.1:8000";

function logout() {
    localStorage.removeItem("token");
    window.location.href = "index.html";
}

// 🔄 Load reports
async function loadReports() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/reports`, {
            headers: {
                Authorization: "Bearer hackathon-secret"
            }
        });

        const data = await res.json();
        const reports = data.reports || data;

        renderReports(reports);

    } catch (err) {
        console.error(err);
    }
}

// 🎨 Render reports
function renderReports(reports) {
    const container = document.getElementById("reportsList");
    container.innerHTML = "";

    reports.forEach(r => {

        const card = document.createElement("div");
        card.className = "report-card";

        card.innerHTML = `
            <h3>${r.disaster_type || "Emergency"}</h3>
            <p>${r.description || ""}</p>

            <p>Status: ${r.status || "Pending"}</p>

            <button onclick="assign('${r.id}')">Assign</button>
            <button onclick="resolve('${r.id}')">Resolve</button>
        `;

        container.appendChild(card);
    });
}

// 🤝 Assign volunteer
async function assign(id) {
    alert("Assign logic next step 🔥");
}

// ✅ Resolve
async function resolve(id) {
    alert("Resolve logic next step 🔥");
}

// 🚀 INIT
loadReports();