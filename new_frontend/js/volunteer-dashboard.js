const API_BASE = window.SETU_API_BASE_URL || "";

// Get auth token — standardized key is 'token'
function getToken() {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "login.html";
        throw new Error("Not authenticated");
    }
    return token;
}

// Logout — clear all auth-related keys
function logout() {
    ["token", "auth_token", "volunteer_id", "name"].forEach(k => localStorage.removeItem(k));
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
        console.error(err);
        return null;
    }
}

const volunteerId = localStorage.getItem("volunteer_id");

// 👤 Load Profile and Assignment
async function loadProfile() {
    if (!volunteerId) {
        document.getElementById("assignment").innerText = "No volunteer ID found. Please login again.";
        return;
    }

    const nameStr = localStorage.getItem("name") || "Volunteer";
    document.getElementById("name").innerText = nameStr;
    document.getElementById("skills").innerText = "Skills: Available in Database";
    document.getElementById("ngo").innerText = "NGO: Registered";
    document.getElementById("status").innerText = "Status: Available";

    const assignments = await api(`/assignment/volunteer/${volunteerId}`);
    const container = document.getElementById("assignment");

    // Filter to active assignments (not resolved)
    const activeAssignments = assignments ? assignments.filter(a => !a.resolved_at) : [];

    if (!activeAssignments || activeAssignments.length === 0) {
        container.innerHTML = "No active assignment";
        document.getElementById("status").innerText = "Status: Available";
        return;
    }

    document.getElementById("status").innerText = "Status: Assigned";

    const a = activeAssignments[0];

    const severity = (a.severity || "low").toLowerCase();

    container.innerHTML = `
        <div style="margin-bottom: 10px;">
            <b>${a.disaster_type || "Emergency"}</b>
            <span class="badge ${severity}" style="float: right;">${severity.toUpperCase()}</span>
        </div>
        <p>${a.description || "No description provided."}</p>
        <p style="margin-top: 10px;">Status: <b>${a.status || "assigned"}</b></p>
        <button onclick="resolveAssignment('${a.assignment_id}')" style="margin-top: 15px; padding: 10px 20px; background-color: #f44336; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; width: 100%;">Mark as Resolved</button>
    `;
}

async function resolveAssignment(assignmentId) {
    if (!confirm("Are you sure you want to mark this assignment as resolved?")) return;
    
    await api(`/assignment/${assignmentId}/resolve`, {
        method: "PATCH"
    });
    
    alert("Assignment resolved successfully!");
    loadProfile();
}

// 🚀 INIT
loadProfile();