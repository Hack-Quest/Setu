const API_BASE = window.SETU_API_BASE_URL || "";

// 🔐 Get token (STANDARDIZED)
function getToken() {
    const token = localStorage.getItem("auth_token");
    if (!token) {
        alert("Please login again");
        window.location.href = "login.html";
        throw new Error("No token");
    }
    return token;
}

// 🔓 Logout
function logout() {
    localStorage.clear();
    window.location.href = "index.html";
}

// 🌐 API helper
async function api(endpoint, options = {}) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                "Authorization": `Bearer ${getToken()}`,
                "Content-Type": "application/json"
            },
            ...options
        });

        if (!res.ok) throw new Error("API error");

        return await res.json();
    } catch (err) {
        console.error("API error:", err);
        return null;
    }
}

// 📌 Volunteer ID
const volunteerId = localStorage.getItem("volunteer_id");

// 👤 Load Profile + Assignment
async function loadProfile() {

    if (!volunteerId) {
        document.getElementById("assignment").innerText =
            "No volunteer ID found. Please login again.";
        return;
    }

    // 👤 Basic info (fallback safe)
    const name = localStorage.getItem("name") || "Volunteer";
    document.getElementById("name").innerText = name;
    document.getElementById("skills").innerText = "Skills: Assigned dynamically";
    document.getElementById("ngo").innerText = "NGO: Connected";
    document.getElementById("status").innerText = "Status: Checking...";

    // 📡 Fetch assignments
    const assignments = await api(`/assignment/volunteer/${volunteerId}`);
    const container = document.getElementById("assignment");

    if (!assignments || assignments.length === 0) {
        container.innerHTML = "No active assignment";
        document.getElementById("status").innerText = "Status: Available";
        return;
    }

    // 🔍 Filter active
    const activeAssignments = assignments.filter(a => !a.resolved_at);

    if (activeAssignments.length === 0) {
        container.innerHTML = "No active assignment";
        document.getElementById("status").innerText = "Status: Available";
        return;
    }

    const a = activeAssignments[0];

    document.getElementById("status").innerText = "Status: Assigned";

    const severity = (a.severity || "low").toLowerCase();

    container.innerHTML = `
        <div style="margin-bottom: 10px;">
            <b>${a.disaster_type || "Emergency"}</b>
            <span class="badge ${severity}" style="float: right;">
                ${severity.toUpperCase()}
            </span>
        </div>

        <p>${a.description || "No description provided."}</p>

        <p style="margin-top: 10px;">
            Status: <b>${a.status || "assigned"}</b>
        </p>

        <button onclick="resolveAssignment('${a.need_id}', '${a.assignment_id}')"
            style="margin-top: 15px; padding: 10px 20px; background-color: #f44336; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; width: 100%;">
            Mark as Resolved
        </button>
    `;
}

// ✅ Resolve assignment (FIXED)
async function resolveAssignment(needId, assignmentId) {

    if (!confirm("Are you sure you want to mark this assignment as resolved?"))
        return;

    const res = await api(`/assignment/${assignmentId}/resolve`, {
        method: "PATCH",
        body: JSON.stringify({
            need_id: needId,
            volunteer_id: volunteerId
        })
    });

    if (res) {
        alert("Assignment resolved successfully!");
        loadProfile();
    } else {
        alert("Failed to resolve assignment");
    }
}

// 🚀 INIT
loadProfile();