window.SETU_API_BASE_URL = "https://setu-api-949977701091.asia-south1.run.app";

function openNeedForm() {
    window.open("https://docs.google.com/forms/d/e/1FAIpQLSfpOTtIUbv4g216ME419DG_BqF_PCS1chJ0es47HRbkznNA1g/viewform", "_blank");
}

function openNGOForm() {
    window.open("https://docs.google.com/forms/d/e/1FAIpQLSeGRTbtKLqkpfPfiOwpugNvznyA8wNA6Hpkey8RxSYy9PKclA/viewform", "_blank");
}

function openVolunteerForm() {
    window.open("https://docs.google.com/forms/d/e/1FAIpQLSclY6jrgE1n3PmEiBQuTwO8o5Ew9QuOrN3_zyTnDLEUbpladw/viewform", "_blank");
}

function requireAuth() {
    if (!localStorage.getItem("auth_token")) {
        window.location.href = "login.html";
    }
}

// ─── Toast Notifications ──────────────────────────────────────────────────────
(function injectToastStyles() {
    if (document.getElementById("setu-toast-styles")) return;
    const style = document.createElement("style");
    style.id = "setu-toast-styles";
    style.textContent = `
        #setu-toast-container {
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            pointer-events: none;
        }
        .setu-toast {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 14px 20px;
            border-radius: 10px;
            font-size: 0.875rem;
            font-weight: 600;
            color: #fff;
            min-width: 260px;
            max-width: 380px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
            pointer-events: all;
            animation: toastIn 0.3s ease forwards;
            backdrop-filter: blur(6px);
        }
        .setu-toast.hiding {
            animation: toastOut 0.3s ease forwards;
        }
        .setu-toast.success { background: rgba(39,174,96,0.92); }
        .setu-toast.error   { background: rgba(231,76,60,0.92); }
        .setu-toast.info    { background: rgba(52,152,219,0.92); }
        @keyframes toastIn  { from { opacity:0; transform: translateY(16px); } to { opacity:1; transform: translateY(0); } }
        @keyframes toastOut { from { opacity:1; transform: translateY(0); } to { opacity:0; transform: translateY(16px); } }
    `;
    document.head.appendChild(style);
})();

/**
 * showToast(message, type, duration)
 * @param {string} message  - Text to display
 * @param {'success'|'error'|'info'} type - Visual style
 * @param {number} duration - Auto-dismiss ms (default 3500)
 */
function showToast(message, type = "info", duration = 3500) {
    let container = document.getElementById("setu-toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "setu-toast-container";
        document.body.appendChild(container);
    }

    const icons = { success: "✅", error: "❌", info: "ℹ️" };
    const toast = document.createElement("div");
    toast.className = `setu-toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || "•"}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add("hiding");
        toast.addEventListener("animationend", () => toast.remove(), { once: true });
    }, duration);
}