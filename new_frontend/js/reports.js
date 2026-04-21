// new_frontend/js/reports.js

document.addEventListener('DOMContentLoaded', async () => {
    const loader = document.getElementById('loader');
    const reportsList = document.getElementById('reportsList');
    const emptyState = document.getElementById('emptyState');
    let markerBounds = [];

    /**
     * 1. THE SAFETY SHIELD
     * Force-hides the loader after 5 seconds to prevent hanging on missing assets.
     */
    const safetyTimeout = setTimeout(() => {
        if (loader && !loader.classList.contains('hidden')) {
            console.warn("Safety Shield: Hiding loader due to potential asset hang.");
            loader.classList.add('hidden');
        }
    }, 5000);

    try {
        // 2. FETCH DATA
        const result = await ApiService.getReports();

        // Kill safety timeout and hide loader immediately upon response
        clearTimeout(safetyTimeout);
        if (loader) loader.classList.add('hidden');

        // 3. DATA EXTRACTION
        let reports = [];
        if (result.ok) {
            reports = Array.isArray(result.data) ? result.data : (result.data.reports || []);
        }

        if (result.ok && reports.length > 0) {
            if (reportsList) {
                reportsList.classList.remove('hidden');
                reportsList.innerHTML = ''; // Clear previous "Syncing..." text
            }

            // 4. CRITICALITY SORTING (Critical > High > Medium > Low)
            const priorityOrder = { "critical": 1, "high": 2, "medium": 3, "low": 4 };
            const sortedData = reports.sort((a, b) => {
                const pA = priorityOrder[(a.severity || 'low').toLowerCase()] || 5;
                const pB = priorityOrder[(b.severity || 'low').toLowerCase()] || 5;
                return pA - pB;
            });

            sortedData.forEach((report, index) => {
                const severity = (report.severity || "LOW").toLowerCase();
                const category = (report.category || "OTHER").toUpperCase();

                // Dynamic Styling Logic
                let badgeStyle = "bg-muted text-ink-700";
                let iconName = "activity";

                if (severity === "critical" || severity === "high") {
                    badgeStyle = "bg-rose-50 text-rose-700 border border-rose-200/50";
                    iconName = "alert-circle";
                } else if (severity === "medium") {
                    badgeStyle = "bg-orange-50 text-orange-700 border border-orange-200/50";
                    iconName = "alert-triangle";
                }

                // 5. MERGED TRUST & PRIORITY LOGIC
                // Combine the "Updated Upstream" detail with the "Stashed" status fallback
                const showTrustScore = report.trust_score_visible === true || report.trust_score !== undefined;

                const verificationLabel = report.common_verification?.passed === false
                    ? 'Common Verification: Pending'
                    : 'Common Verification: Passed';

                const priorityLevelRaw = report.priority_level || report.priority || 'low';
                const priorityText = String(priorityLevelRaw).toUpperCase();

                const trustOrVerificationHtml = showTrustScore
                    ? `Trust Score: <b>${report.trust_score || 0}%</b> | Priority: <b>${priorityText}</b>`
                    : `${verificationLabel} | Priority: <b>${priorityText}</b>`;

                // Create Card element
                const card = document.createElement('div');
                card.className = `bg-surface p-6 rounded-[1.5rem] shadow-soft border border-muted/50 hover:shadow-float transition-all flex flex-col md:flex-row justify-between gap-6 fade-in-up`;
                card.style.animationDelay = `${(index * 0.05)}s`;

                card.innerHTML = `
                    <div class="flex flex-col gap-2 flex-1">
                        <div class="flex items-center gap-2">
                            <span class="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest flex items-center gap-1 ${badgeStyle}">
                                <i data-feather="${iconName}" class="w-3 h-3"></i>
                                ${severity}
                            </span>
                            <span class="text-[10px] font-bold text-ink-300 uppercase tracking-widest">
                                • ${category}
                            </span>
                        </div>
                        <h3 class="text-lg font-medium text-ink-900">${report.disaster_type || "Relief Request"}</h3>
                        <p class="text-sm text-ink-500 truncate max-w-2xl">${report.description || "No description provided."}</p>
                    </div>
                    <div class="flex flex-col md:items-end gap-1">
                        <span class="text-[10px] font-semibold text-ink-500 uppercase tracking-tight">Location</span>
                        <span class="text-sm font-medium text-ink-900">${report.location_text || "Unknown"}</span>
                        <span class="text-xs text-ink-500 mt-2">${trustOrVerificationHtml}</span>
                    </div>
                `;

                if (reportsList) reportsList.appendChild(card);

                // 6. MAP INTEGRATION (Leaflet / OSM Version)
                if (window.reportsMap && window.reportsLayer && report.lat && report.lng) {
                    const lat = parseFloat(report.lat);
                    const lng = parseFloat(report.lng);

                    if (!isNaN(lat) && !isNaN(lng)) {
                        const marker = L.circleMarker([lat, lng], {
                            radius: severity === 'critical' ? 10 : 7,
                            color: severity === 'critical' ? '#E11D48' : '#F97316',
                            fillColor: severity === 'critical' ? '#E11D48' : '#F97316',
                            fillOpacity: 0.8,
                            weight: 2
                        });

                        marker.bindPopup(`
                            <div style="font-family:sans-serif;">
                                <b>${report.disaster_type || "Need"}</b><br>
                                Severity: ${severity.toUpperCase()}<br>
                                Priority: ${priorityText}<br>
                                <small>${report.location_text || ""}</small>
                            </div>
                        `);

                        marker.addTo(window.reportsLayer);
                        markerBounds.push([lat, lng]);
                    }
                }
            });

            // Auto-zoom map to show all pins
            if (markerBounds.length > 0 && window.reportsMap) {
                window.reportsMap.fitBounds(markerBounds, { padding: [30, 30] });
            }

            if (typeof feather !== 'undefined') feather.replace();
        } else {
            if (emptyState) emptyState.classList.remove('hidden');
        }

    } catch (err) {
        console.error("Setu Critical Frontend Error:", err);
        if (loader) loader.classList.add('hidden');
        if (emptyState) emptyState.classList.remove('hidden');
    }
});