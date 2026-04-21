// new_frontend/js/reports.js

document.addEventListener('DOMContentLoaded', async () => {
    const loader = document.getElementById('loader');
    const reportsList = document.getElementById('reportsList');
    const emptyState = document.getElementById('emptyState');

    if (window.reportsLayer && typeof window.reportsLayer.clearLayers === 'function') {
        window.reportsLayer.clearLayers();
    }

    const markerBounds = [];

    let result;
    try {
        // 1. Fetch
        result = await ApiService.getReports();
    } catch (error) {
        result = { ok: false, error, data: null };
    }

    // 2. IMMEDIATE OVERRIDE: Hide spinner as soon as request resolves/rejects
    if (loader) loader.classList.add('hidden');

    // 3. Handle Data
    if (result.ok && result.data) {
        const reports = Array.isArray(result.data) ? result.data : (result.data.reports || []);

        if (reports.length > 0) {
            if (reportsList) reportsList.classList.remove('hidden');

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

                const showTrustScore = report.trust_score_visible === true || report.verification_mode === 'full_trust';
                const verificationLabel = report.common_verification?.passed === false
                    ? 'Common Verification: Pending'
                    : 'Common Verification: Passed';
                const priorityLevelRaw = report.priority_level || report.priority || 'low';
                const priorityText = String(priorityLevelRaw).toUpperCase();
                const trustOrVerificationHtml = showTrustScore
                    ? `Trust Score: <b>${report.trust_score || 0}/100</b> | Priority: <b>${priorityText}</b>`
                    : `${verificationLabel} | Priority: <b>${priorityText}</b>`;

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
                    <span class="text-xs text-ink-500 mt-2">${trustOrVerificationHtml}</span>
                </div>
            `;

                if (reportsList) reportsList.appendChild(el);

                // 🔥 Add Marker to the Integrated Map
                if (window.reportsMap && window.reportsLayer && report.lat && report.lng) {
                    const lat = parseFloat(report.lat);
                    const lng = parseFloat(report.lng);

                    if (!Number.isNaN(lat) && !Number.isNaN(lng)) {
                        const marker = L.circleMarker([lat, lng], {
                            radius: severity === 'critical' ? 10 : 7,
                            color: severity === 'critical' ? 'red' : 'orange',
                            fillColor: severity === 'critical' ? 'red' : 'orange',
                            fillOpacity: 1,
                            weight: 1
                        });

                        marker.bindPopup(`
                        <div style="font-family:sans-serif;line-height:1.4;">
                            <b>${report.disaster_type || "Emergency Signal"}</b><br>
                            ${report.description || "N/A"}<br>
                            <b>Severity:</b> ${severity.toUpperCase()}<br>
                            <b>Location:</b> ${report.location_text || "Unknown"}
                        </div>
                    `);

                        marker.addTo(window.reportsLayer);
                        markerBounds.push([lat, lng]);
                    }
                }
            });

            if (markerBounds.length > 0 && window.reportsMap) {
                window.reportsMap.fitBounds(markerBounds, { padding: [28, 28] });
            }

            if (typeof feather !== 'undefined') feather.replace();
        } else {
            if (emptyState) emptyState.classList.remove('hidden');
        }
    } else {
        console.error("Fetch failed:", result.error);
        if (emptyState) emptyState.classList.remove('hidden');
    }
});