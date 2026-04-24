async function loadStats() {
    try {
        const response = await ApiService.getStats();

        if (!response.ok) {
            console.error("Stats error:", response.error);
            return;
        }

        const data = response.data;
        // /stats returns: total_reports, total_volunteers, total_ngos, verified_ngos
        document.getElementById("totalReports").innerText = data.total_reports ?? 0;
        document.getElementById("volunteer-count").innerText = data.total_volunteers ?? 0;
        document.getElementById("ngo-count").innerText = data.total_ngos ?? 0;

    } catch (err) {
        console.error("Failed to load stats:", err);
    }
}

window.addEventListener("DOMContentLoaded", loadStats);
