// Modal and Google forms logic
const formModal = document.getElementById('formModal');
const modalBackdrop = document.getElementById('modalBackdrop');
const modalContent = document.getElementById('modalContent');
const modalTitle = document.getElementById('modalTitle');
const googleFormIframe = document.getElementById('googleFormIframe');
const iframeLoader = document.getElementById('iframeLoader');

// Example real forms (replace these with actual Setu ones)
const FORMS = {
    need: {
        title: "Process New Need",
        url: "https://docs.google.com/forms/d/e/1FAIpQLSc_nE998hE_b-sH-rB3f12444002n/viewform?embedded=true" 
    },
    volunteer: {
        title: "Register Unit",
        url: "https://docs.google.com/forms/d/e/1FAIpQLSf2O_x91U4_p-sH-rB3f12444002z/viewform?embedded=true"
    }
};

window.openFormModal = function(type) {
    if (!FORMS[type]) return;
    
    // Set text and source
    modalTitle.textContent = FORMS[type].title;
    googleFormIframe.src = FORMS[type].url;
    googleFormIframe.classList.remove('opacity-100');
    googleFormIframe.classList.add('opacity-0');
    
    // Show modal container
    formModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    
    // Animate in
    setTimeout(() => {
        modalBackdrop.classList.remove('opacity-0');
        modalBackdrop.classList.add('opacity-100');
        
        modalContent.classList.remove('translate-y-[100%]');
        modalContent.classList.add('translate-y-0');
        
        iframeLoader.classList.remove('opacity-0');
    }, 10);
}

window.iframeLoaded = function() {
    if(googleFormIframe.src && googleFormIframe.src !== window.location.href) {
        iframeLoader.classList.add('opacity-0');
        googleFormIframe.classList.remove('opacity-0');
        googleFormIframe.classList.add('opacity-100');
    }
}

window.closeFormModal = function() {
    // Animate out
    modalBackdrop.classList.remove('opacity-100');
    modalBackdrop.classList.add('opacity-0');
    
    modalContent.classList.remove('translate-y-0');
    modalContent.classList.add('translate-y-[100%]');
    
    setTimeout(() => {
        formModal.classList.add('hidden');
        document.body.style.overflow = '';
        googleFormIframe.src = ''; 
    }, 500); // Wait for transition
}


// System Match API simulation logic
const runMatchBtn = document.getElementById('runMatchBtn');
const btnText = document.getElementById('btnText');
const toast = document.getElementById('toast');
const toastMsg = document.getElementById('toastMsg');

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
    btnText.textContent = 'Processing...';
    
    // Simulate slight loading delay for realism
    setTimeout(async () => {
        try {
            // Attempt to call the genuine backend if active
            const response = await fetch('http://127.0.0.1:8000/api/match_units', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
            
            if(response.ok) {
                const data = await response.json();
                showToast(`AI Match computed. Ground units updated.`);
            } else {
                showToast('Engine processed statically. Backend unreachable.');
            }
        } catch(err) {
            showToast('Engine processed statically. Backend unreachable.');
        } finally {
            runMatchBtn.disabled = false;
            btnText.textContent = originalText;
        }
    }, 800);
});
