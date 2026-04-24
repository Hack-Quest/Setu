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

function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");

    if (!container) {
        console.warn("Toast container not found");
        return;
    }

    const toast = document.createElement("div");
    toast.classList.add("toast");

    if (type === "success") toast.classList.add("toast-success");
    else if (type === "error") toast.classList.add("toast-error");
    else if (type === "warning") toast.classList.add("toast-warning");
    else toast.classList.add("toast-info");

    toast.innerText = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(100%)";

        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}