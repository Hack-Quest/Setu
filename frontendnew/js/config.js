// ============================================================
// frontend/js/config.js  — SETU Frontend Configuration
// ============================================================
// Single source of truth for the backend URL.
// Change this one value to point at staging / production.
// ============================================================

window.SETU_API_BASE_URL = (function () {
    var origin = window.location.origin;
    if (!origin || origin === "null" || origin === "file://") {
        return "http://127.0.0.1:8000";
    }
    return origin;
})();

// Google Forms deep-links (kept in sync with new_frontend)
window.SETU_NEED_FORM_URL    = "https://docs.google.com/forms/d/e/1FAIpQLSfpOTtIUbv4g216ME419DG_BqF_PCS1chJ0es47HRbkznNA1g/viewform";
window.SETU_NGO_FORM_URL     = "https://docs.google.com/forms/d/e/1FAIpQLSeGRTbtKLqkpfPfiOwpugNvznyA8wNA6Hpkey8RxSYy9PKclA/viewform";
window.SETU_VOLUNTEER_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSclY6jrgE1n3PmEiBQuTwO8o5Ew9QuOrN3_zyTnDLEUbpladw/viewform";
