// Reports Page Logic using Shared ApiService

async function fetchReports() {
    const { ok, data } = await ApiService.getReports();
    if (ok) {
        // Backend returns a raw array — normalise into { reports: [...] }
        const reports = Array.isArray(data) ? data : (data.reports || []);
        return { reports };
    } else {
        console.error('API Error fetching reports:', ok);
        return { reports: [] }; // Fallback to empty list
    }
}

// Logic to render UI smoothly
document.addEventListener('DOMContentLoaded', async () => {
    const loader = document.getElementById('loader');
    const emptyState = document.getElementById('emptyState');
    const reportsList = document.getElementById('reportsList');

    const data = await fetchReports();
    const reports = data.reports || [];

    // Fade out loader
    loader.classList.add('hidden');

    if (reports.length === 0) {
        emptyState.classList.remove('hidden');
    } else {
        reportsList.classList.remove('hidden');

        reports.forEach((report, index) => {
            // Priority Styling Maps
            const safePriority = (report.priority || "LOW").toUpperCase();
            let priorityBadgeStyle = "bg-muted text-ink-700";
            let priorityIcon = "activity";

            if (safePriority === "HIGH") {
                priorityBadgeStyle = "bg-rose-50 text-rose-700 border border-rose-200/50";
                priorityIcon = "alert-circle";
            } else if (safePriority === "MEDIUM") {
                // Safety Orange for critical alerts instead of light amber
                priorityBadgeStyle = "bg-orange-50 text-orange-700 border border-orange-200/50";
                priorityIcon = "alert-triangle";
            } else {
                priorityBadgeStyle = "bg-emerald-50 text-emerald-700 border border-emerald-200/50";
                priorityIcon = "shield";
            }

            const element = document.createElement('div');
            // Theme alignment: surface bg, deep navy accents available via typography
            element.className = `bg-surface p-6 rounded-[1.5rem] shadow-soft border border-muted/50 hover:shadow-float transition-shadow flex flex-col md:flex-row md:items-center justify-between gap-6 fade-in-up`;
            element.style.animationDelay = `${(index * 0.05) + 0.1}s`; // Stagger animation

            element.innerHTML = `
                <div class="flex flex-col gap-2 flex-1">
                    <div class="flex items-center gap-3 mb-1">
                        <span class="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest flex items-center gap-1 ${priorityBadgeStyle}">
                            <i data-feather="${priorityIcon}" class="w-3 h-3"></i>
                            ${safePriority}
                        </span>
                        <span class="text-xs font-semibold text-ink-300 tracking-wide">ID: ${report.id || report.phone || "Unknown"}</span>
                    </div>
                    <h3 class="text-lg font-medium text-ink-900 leading-snug">${report.disaster_type || "Uncategorized Distress Signal"}</h3>
                    <p class="text-sm text-ink-500 font-light truncate max-w-2xl">${report.description || "No description provided."}</p>
                </div>
                
                <div class="flex flex-col md:items-end gap-1 min-w-[200px]">
                    <span class="text-[10px] font-semibold text-ink-500 uppercase tracking-widest">Location</span>
                    <span class="text-sm font-medium text-ink-900">${report.location_text || (report.lat ? `${report.lat.toFixed(4)}, ${report.lng.toFixed(4)}` : "Location Unknown")}</span>
                    <div class="flex items-center gap-2 mt-2">
                         <span class="text-[10px] text-ink-500">Trust Score:</span>
                         <span class="text-sm font-semibold text-ink-900">${report.trust_score !== undefined ? report.trust_score + '%' : "N/A"}</span>
                    </div>
                </div>
                
                <div class="mt-2 md:mt-0">
                    <button class="px-4 py-2 bg-ink-900 text-white rounded-xl text-xs font-semibold hover:bg-ink-700 transition-colors shadow-soft">
                        View Details
                    </button>
                </div>
            `;
            reportsList.appendChild(element);
        });

        // Re-init feather icons for the new injected elements
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
});
