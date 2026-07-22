/* dashboard.js */
document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss flashes after 4 seconds
    setTimeout(() => {
        const flashes = document.querySelectorAll('.flash-msg');
        flashes.forEach(f => {
            f.style.opacity = '0';
            f.style.transition = 'opacity 0.5s ease';
            setTimeout(() => f.remove(), 500);
        });
    }, 4000);
});
