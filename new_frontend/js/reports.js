// new_frontend/js/reports.js

document.addEventListener('DOMContentLoaded', async () => {
    const loader = document.getElementById('loader');
    const reportsList = document.getElementById('reportsList');
    const emptyState = document.getElementById('emptyState');

    const result = await ApiService.getReports(); 

    if (loader) loader.classList.add('hidden'); 

    // Extract the actual array regardless of backend format
    let reports = [];
    if (result.ok) {
        // Handle both raw list and {"reports": [...]} formats
        reports = Array.isArray(result.data) ? result.data : (result.data.reports || []);
    }

    if (result.ok && reports.length > 0) {
        reportsList.classList.remove('hidden');

        // 🔥 SORT BY CRITICALITY: Critical > High > Medium > Low
        const priorityOrder = { "critical": 1, "high": 2, "medium": 3, "low": 4 };
        const sortedData = reports.sort((a, b) => {
            const pA = priorityOrder[(a.severity || 'low').toLowerCase()] || 5;
            const pB = priorityOrder[(b.severity || 'low').toLowerCase()] || 5;
            return pA - pB;
        });

        sortedData.forEach((report, index) => {
            const severity = (report.severity || "LOW").toLowerCase();
            let badgeStyle = "bg-muted text-ink-700";
            let iconName = "activity";

            // Dynamic Styling based on severity
            if (severity === "critical" || severity === "high") {
                badgeStyle = "bg-rose-50 text-rose-700 border-rose-200";
                iconName = "alert-circle";
            } else if (severity === "medium") {
                badgeStyle = "bg-orange-50 text-orange-700 border-orange-200";
                iconName = "alert-triangle";
            }

            const el = document.createElement('div');
            el.className = `bg-surface p-6 rounded-[1.5rem] shadow-soft border border-muted/50 hover:shadow-float transition-all flex flex-col md:flex-row justify-between gap-6 fade-in-up`;
            el.style.animationDelay = `${(index * 0.05)}s`;

            el.innerHTML = `
                <div class="flex flex-col gap-2 flex-1">
                    <span class="px-2.5 py-1 w-max rounded-full text-[10px] font-bold uppercase tracking-widest flex items-center gap-1 ${badgeStyle}">
                        <i data-feather="${iconName}" class="w-3 h-3"></i>
                        ${severity.toUpperCase()}
                    </span>
                    <h3 class="text-lg font-medium text-ink-900">${report.disaster_type || "Emergency Signal"}</h3>
                    <p class="text-sm text-ink-500 truncate max-w-2xl">${report.description || "N/A"}</p>
                </div>
                <div class="flex flex-col md:items-end gap-1">
                    <span class="text-[10px] font-semibold text-ink-500 uppercase">Location</span>
                    <span class="text-sm font-medium text-ink-900">${report.location_text || "Unknown"}</span>
                    <span class="text-xs text-ink-500 mt-2">Trust Score: <b>${report.trust_score || 0}%</b></span>
                </div>
            `;
            reportsList.appendChild(el);

            // 🔥 Add Marker to the Integrated Map
            if (window.reportsMap && report.lat && report.lng) {
                new google.maps.Marker({
                    position: { lat: parseFloat(report.lat), lng: parseFloat(report.lng) },
                    map: window.reportsMap,
                    icon: {
                        path: google.maps.SymbolPath.CIRCLE,
                        scale: severity === 'critical' ? 10 : 7,
                        fillColor: severity === 'critical' ? 'red' : 'orange',
                        fillOpacity: 1,
                        strokeWeight: 1
                    }
                });
            }
        });

        if (typeof feather !== 'undefined') feather.replace();
    } else {
        if (emptyState) emptyState.classList.remove('hidden');
    }
});