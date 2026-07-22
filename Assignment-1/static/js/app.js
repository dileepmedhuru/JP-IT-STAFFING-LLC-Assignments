/* Front-End Interactive Scripting for EXPORT Automation System */

document.addEventListener('DOMContentLoaded', () => {
    // Search table filter
    const searchInput = document.getElementById('tableSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().strip();
            const rows = document.querySelectorAll('.custom-table tbody tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        });
    }

    // Auto-dismiss flashes after 5 seconds
    setTimeout(() => {
        const flashes = document.querySelectorAll('.flash-alert');
        flashes.forEach(f => {
            f.style.opacity = '0';
            f.style.transition = 'opacity 0.5s ease';
            setTimeout(() => f.remove(), 500);
        });
    }, 5000);
});

// Render Dashboard Delivery & Source Distribution Charts
function renderDashboardCharts(deliveryStats, sourceBreakdown) {
    // Delivery Donut Chart
    const ctxDelivery = document.getElementById('deliveryChart');
    if (ctxDelivery && window.Chart) {
        new Chart(ctxDelivery, {
            type: 'doughnut',
            data: {
                labels: ['Successful Sends', 'Failed / Bounced', 'Unsent / Queued'],
                datasets: [{
                    data: [
                        deliveryStats.sent_success || 0,
                        deliveryStats.sent_failed || 0,
                        Math.max(0, (deliveryStats.total_buyers || 0) - (deliveryStats.total_sent_attempts || 0))
                    ],
                    backgroundColor: ['#10b981', '#f43f5e', '#6366f1'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#9ca3af', font: { family: 'Inter' } }
                    }
                },
                cutout: '70%'
            }
        });
    }

    // Source Platform Bar Chart
    const ctxSource = document.getElementById('sourceChart');
    if (ctxSource && window.Chart) {
        const labels = Object.keys(sourceBreakdown || {});
        const counts = Object.values(sourceBreakdown || {});

        new Chart(ctxSource, {
            type: 'bar',
            data: {
                labels: labels.length ? labels : ['Google', 'LinkedIn', 'Facebook', 'Directories', 'Websites'],
                datasets: [{
                    label: 'Discovered Leads',
                    data: counts.length ? counts : [8, 5, 5, 5, 4],
                    backgroundColor: 'rgba(99, 102, 241, 0.7)',
                    borderColor: '#6366f1',
                    borderWidth: 1,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                scales: {
                    x: { ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}
