// Modal and Forms Logic
const formModal = document.getElementById('formModal');
const modalBackdrop = document.getElementById('modalBackdrop');
const modalContent = document.getElementById('modalContent');
const modalTitle = document.getElementById('modalTitle');

const needForm = document.getElementById('needForm');
const volunteerForm = document.getElementById('volunteerForm');
const needResult = document.getElementById('needResult');

const statNeeds = document.getElementById('statNeeds');
const statUnits = document.getElementById('statUnits');

// Dashboard Initialization
async function loadDashboard() {
    const { ok, data } = await ApiService.getDashboard();
    if (ok) {
        if (statNeeds) statNeeds.textContent = data.total_needs || 0;
        if (statUnits) statUnits.textContent = data.total_volunteers || 0;
    }
}

document.addEventListener('DOMContentLoaded', loadDashboard);


// Modal Open/Close Logic
window.openFormModal = function (type) {
    // Set title and active form
    if (type === 'need') {
        modalTitle.textContent = "Process New Need";
        needForm.classList.remove('hidden');
        volunteerForm.classList.add('hidden');
        needResult.classList.add('hidden');
        needForm.reset();
    } else if (type === 'volunteer') {
        modalTitle.textContent = "Register Unit";
        volunteerForm.classList.remove('hidden');
        needForm.classList.add('hidden');
        volunteerForm.reset();
    }

    // Show modal container
    formModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    // Animate in
    setTimeout(() => {
        modalBackdrop.classList.remove('opacity-0');
        modalBackdrop.classList.add('opacity-100');

        modalContent.classList.remove('translate-y-[100%]');
        modalContent.classList.add('translate-y-0');
    }, 10);
}

window.closeFormModal = function () {
    // Animate out
    modalBackdrop.classList.remove('opacity-100');
    modalBackdrop.classList.add('opacity-0');

    modalContent.classList.remove('translate-y-0');
    modalContent.classList.add('translate-y-[100%]');

    setTimeout(() => {
        formModal.classList.add('hidden');
        document.body.style.overflow = '';
    }, 500); // Wait for transition
}


// Form Submission Handling
needForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(needForm);
    const data = Object.fromEntries(formData.entries());

    const submitBtn = needForm.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';

    const response = await ApiService.postNeed(data);

    if (response.ok) {
        showToast('Need successfully processed.');
        // Show AI Output Feedback
        const score = response.data.trust_score || 0;
        const action = response.data.dispatch_action || 'N/A';
        const mode = response.data.verification_mode || 'common_only';
        const priorityLevelRaw = response.data.priority_level || response.data.priority || 'low';
        const priorityLevel = String(priorityLevelRaw).toUpperCase();
        const showTrustScore = response.data.trust_score_visible === true || mode === 'full_trust';
        const commonVerification = response.data.common_verification || {};
        const commonPassed = commonVerification.passed === true;
        const isHighTrust = score > 60;

        needResult.classList.remove('hidden');
        needResult.classList.remove('bg-rose-50', 'text-rose-700', 'border-rose-200');
        needResult.classList.remove('bg-emerald-50', 'text-emerald-900', 'border-emerald-200');

        if (!showTrustScore) {
            if (commonPassed) {
                needResult.classList.add('bg-emerald-50', 'text-emerald-900', 'border-emerald-200');
                needResult.innerHTML = `
                    <div class="flex items-center gap-2"><i data-feather="check-circle" class="w-4 h-4"></i> Report verified with common checks</div>
                    <div class="flex items-center gap-2"><i data-feather="shield" class="w-4 h-4"></i> Status: success</div>
                    <div class="flex items-center gap-2"><i data-feather="flag" class="w-4 h-4"></i> Priority: ${priorityLevel}</div>
                `;
            } else {
                const issues = [];
                if (commonVerification.phone_valid === false) {
                    issues.push('Invalid phone number');
                }
                if (commonVerification.location_valid === false) {
                    issues.push('Location could not be geocoded');
                }

                needResult.classList.add('bg-rose-50', 'text-rose-700', 'border-rose-200');
                needResult.innerHTML = `
                    <div class="flex items-center gap-2 font-semibold"><i data-feather="alert-triangle" class="w-4 h-4 text-orange-500"></i> Common verification failed</div>
                    <div class="flex items-center gap-2"><i data-feather="shield-off" class="w-4 h-4"></i> ${issues.join(' | ') || 'Please check phone number and location.'}</div>
                    <div class="flex items-center gap-2"><i data-feather="clock" class="w-4 h-4"></i> Action: pending_verification</div>
                    <div class="flex items-center gap-2"><i data-feather="flag" class="w-4 h-4"></i> Priority: ${priorityLevel}</div>
                `;
            }
        } else if (isHighTrust) {
            needResult.classList.add('bg-emerald-50', 'text-emerald-900', 'border-emerald-200');
            needResult.innerHTML = `
                <div class="flex items-center gap-2"><i data-feather="check-circle" class="w-4 h-4"></i> Trust Score: ${score}/100 | Priority: ${priorityLevel}</div>
                <div class="flex items-center gap-2"><i data-feather="zap" class="w-4 h-4"></i> Action: ${action}</div>
            `;
        } else {
            needResult.classList.add('bg-rose-50', 'text-rose-700', 'border-rose-200');
            needResult.innerHTML = `
                <div class="flex items-center gap-2 font-semibold"><i data-feather="alert-triangle" class="w-4 h-4 text-orange-500"></i> Trust Score: ${score}/100 (Unverified) | Priority: ${priorityLevel}</div>
                <div class="flex items-center gap-2"><i data-feather="shield" class="w-4 h-4"></i> Action: ${action}</div>
            `;
        }
        feather.replace();
        loadDashboard(); // Refresh stats
    } else {
        showToast('Error processing need.');
    }

    submitBtn.disabled = false;
    submitBtn.textContent = 'Submit Need';
});

volunteerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(volunteerForm);
    const data = Object.fromEntries(formData.entries());

    const selectedSkills = formData.getAll('skills').filter(Boolean);
    if (selectedSkills.length > 0) {
        data.skills = selectedSkills;
    } else if (typeof data.skills === 'string' && data.skills.trim()) {
        data.skills = data.skills.split(',').map((skill) => skill.trim()).filter(Boolean);
    } else {
        data.skills = [];
    }

    if (typeof data.email !== 'string' || typeof data.password !== 'string') {
        showToast('Email and password are required for volunteer registration.');
        return;
    }

    const submitBtn = volunteerForm.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Registering...';

    const response = await ApiService.postVolunteer(data);

    if (response.ok) {
        showToast('Volunteer unit registered.');
        loadDashboard(); // Refresh stats
        setTimeout(() => closeFormModal(), 1000);
    } else {
        showToast('Error registering volunteer.');
    }

    submitBtn.disabled = false;
    submitBtn.textContent = 'Register Unit';
});


// System Match API Logic
const runMatchBtn = document.getElementById('runMatchBtn');
const btnText = document.getElementById('btnText');
const toast = document.getElementById('toast');
const toastMsg = document.getElementById('toastMsg');
const assignmentsSection = document.getElementById('assignmentsSection');
const assignmentsList = document.getElementById('assignmentsList');
const matchStats = document.getElementById('matchStats');

function showToast(message) {
    toastMsg.textContent = message;

    // Translate up and fade in
    toast.classList.remove('translate-y-8', 'opacity-0');
    toast.classList.add('translate-y-0', 'opacity-100');

    setTimeout(() => {
        toast.classList.remove('translate-y-0', 'opacity-100');
        toast.classList.add('translate-y-8', 'opacity-0');
    }, 3000);
}

runMatchBtn.addEventListener('click', async () => {
    runMatchBtn.disabled = true;
    const originalText = btnText.textContent;
    btnText.textContent = 'Processing Match...';

    // Simulate slight loading delay for realism
    setTimeout(async () => {
        try {
            const { ok, data } = await ApiService.runMatch();

            if (ok) {
                showToast(`Match Engine complete. Generated ${data.total_matches_made || 0} assignments.`);
                renderMatches(data.matches || []);
            } else {
                showToast('Engine constraint. Backend unreachable.');
            }
        } catch (err) {
            showToast('Engine error.');
        } finally {
            runMatchBtn.disabled = false;
            btnText.textContent = originalText;
        }
    }, 800);
});

function renderMatches(matches) {
    assignmentsSection.classList.remove('hidden');
    assignmentsList.innerHTML = '';

    matchStats.textContent = matches.length + ' Result(s)';

    if (matches.length === 0) {
        assignmentsList.innerHTML = `<div class="p-6 bg-surface border border-muted rounded-xl text-ink-500 text-sm italic">No matching constraints found.</div>`;
        return;
    }

    matches.forEach((match, idx) => {
        const isAssigned = match.status === 'assigned';
        const statusColor = isAssigned ? 'text-emerald-600 bg-emerald-50' : 'text-orange-600 bg-orange-50'; // Safety orange for alert states
        const statusIcon = isAssigned ? 'check-circle' : 'activity';

        let distHtml = '';
        if (isAssigned && match.distance_km) {
            distHtml = `<div class="text-[10px] text-ink-500 uppercase tracking-widest mt-1">Distance</div>
                        <div class="text-sm font-semibold text-ink-900">${match.distance_km} KM</div>`;
        }

        const el = document.createElement('div');
        // using deep navy (bg-ink-900 text-white vs bg-surface)
        // using slate gray variations text-ink-700 / border-muted
        el.className = `flex flex-col sm:flex-row justify-between sm:items-center bg-surface border border-muted/50 p-5 rounded-[1.5rem] shadow-soft hover:shadow-float transition-shadow gap-4 fade-in-up`;
        el.style.animationDelay = `${(idx * 0.05)}s`;

        el.innerHTML = `
            <div class="flex items-start gap-4">
               <div class="mt-1 w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${isAssigned ? 'bg-ink-900 text-white' : 'bg-muted text-ink-500'}">
                   <i data-feather="${statusIcon}" class="w-4 h-4"></i>
               </div>
               <div>
                   <div class="text-xs font-semibold text-ink-300 tracking-wide mb-1">NEED ID #${match.need_id}</div>
                   <div class="text-base font-medium text-ink-900">${isAssigned ? match.assigned_volunteer : 'Unit Unallocated'}</div>
               </div>
            </div>
            
            <div class="flex flex-row sm:flex-col items-center sm:items-end justify-between sm:justify-center w-full sm:w-auto mt-2 sm:mt-0 gap-2">
                <span class="px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest flex items-center gap-1 ${statusColor}">
                    ${match.status}
                </span>
                <div class="text-right">
                    ${distHtml}
                </div>
            </div>
        `;

        assignmentsList.appendChild(el);
    });

    feather.replace();
}

// 🌐 Real-Time WebSocket Updates & Multilingual Push
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsHost = window.SETU_WS_HOST || window.location.host;
const ws = wsHost ? new WebSocket(`${wsProtocol}//${wsHost}/ws`) : null;
let currentLang = 'en';

const uiLang = document.getElementById('uiLang');
if (uiLang) {
    uiLang.addEventListener('change', (e) => {
        currentLang = e.target.value;
    });
}

if (ws) {
ws.onmessage = function (event) {
    let data;
    try {
        data = JSON.parse(event.data);
    } catch (err) {
        return;
    }

    if (data.type === "NEW_VOLUNTEER") {
        showGlobalToast(`👋 New Unit: ${data.data.name} mapped.`, 'info');
    } else if (data.priority === "HIGH" || (data.trust_score && data.trust_score > 70)) {
        const summary = currentLang === 'en' ? (data.summary_en || `🚨 HIGH TRUST: ${data.category}`) : (data.summary_local || `🚨 HIGH TRUST: ${data.category}`);
        showGlobalToast(summary, 'alert');

        if ('speechSynthesis' in window) {
            const msg = new SpeechSynthesisUtterance(summary);
            msg.lang = currentLang === 'en' ? 'en-US' : 'hi-IN';
            window.speechSynthesis.speak(msg);
        }

        loadDashboard(); // Refresh stats
    }
};
}

function showGlobalToast(message, type) {
    let toastContainer = document.getElementById('global-toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'global-toast-container';
        toastContainer.className = 'fixed top-4 right-4 z-[99] flex flex-col gap-2 pointer-events-none';
        document.body.appendChild(toastContainer);
    }

    const el = document.createElement('div');
    const isAlert = type === 'alert';
    el.className = `p-4 rounded-xl shadow-float text-sm font-medium text-white transition-all transform translate-x-10 opacity-0 ${isAlert ? 'bg-orange-600' : 'bg-ink-900'} flex items-center gap-2 pointer-events-auto max-w-xs`;
    el.innerHTML = `<i data-feather="${isAlert ? 'alert-circle' : 'activity'}" class="w-4 h-4 shrink-0"></i> <span>${message}</span>`;
    toastContainer.appendChild(el);
    feather.replace();

    setTimeout(() => {
        el.classList.remove('translate-x-10', 'opacity-0');
    }, 10);

    setTimeout(() => {
        el.classList.add('translate-x-10', 'opacity-0');
        setTimeout(() => el.remove(), 300);
    }, 6000);
}

