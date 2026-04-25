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

async function runMatching() {
    showToast("Running matching engine...", "info");
    try {
        const res = await ApiService.runMatch();
        if (res.ok) {
            showToast("Matching completed successfully ✅", "success");
        } else {
            showToast("Error running matching: " + (res.error || "Unknown error"), "error");
        }
    } catch (err) {
        showToast("Error running matching", "error");
        console.error("runMatching error:", err);
    }
}
window.runMatching = runMatching;
