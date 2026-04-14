// --- Global Theme Logic ---
function initTheme() {
    const html = document.documentElement;
    const icon = document.getElementById('theme-toggle')?.querySelector('span.material-symbols-outlined') || document.getElementById('theme-icon');
    
    // Check local storage or system preference
    if (localStorage.getItem('theme') === 'light' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: light)').matches)) {
        html.classList.remove('dark');
        if (icon) {
            icon.innerText = 'dark_mode'; // If light, show dark mode icon to toggle
        }
        document.querySelectorAll('#theme-toggle span').forEach(el => {
            if (el.dataset && el.dataset.icon === 'dark_mode') el.classList.remove('hidden');
            if (el.dataset && el.dataset.icon === 'light_mode') el.classList.add('hidden');
        });
    } else {
        html.classList.add('dark');
        if (icon) {
            icon.innerText = 'light_mode'; // If dark, show light mode icon to toggle
        }
        document.querySelectorAll('#theme-toggle span').forEach(el => {
            if (el.dataset && el.dataset.icon === 'light_mode') el.classList.remove('hidden');
            if (el.dataset && el.dataset.icon === 'dark_mode') el.classList.add('hidden');
        });
    }
}

function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.classList.contains('dark');
    
    if (isDark) {
        localStorage.setItem('theme', 'light');
    } else {
        localStorage.setItem('theme', 'dark');
    }
    
    initTheme();
}

// Initialize theme on load
document.addEventListener('DOMContentLoaded', () => {
    initTheme();

    // Attach event listeners to any button toggling theme
    const toggleBtns = document.querySelectorAll('#theme-toggle, [onclick="toggleTheme()"]');
    toggleBtns.forEach(btn => {
        // Remove existing onclick to avoid double-firing if we add a listener, but since index.html doesn't use onclick inline we're safe.
        // Wait, some do use onclick inline: we should be careful.
        btn.addEventListener('click', (e) => {
            // Only toggle if they haven't run an inline script toggle already
            if (!btn.hasAttribute('onclick')) {
                toggleTheme();
            }
        });
    });
});
