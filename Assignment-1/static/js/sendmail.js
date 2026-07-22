/* sendmail.js */
document.addEventListener('DOMContentLoaded', () => {
    const subjectInput = document.getElementById('subjectInput');
    const contentInput = document.getElementById('contentInput');
    const audienceSelect = document.querySelector('select[name="audience"]');

    const subjectPreview = document.getElementById('subjectPreview');
    const bodyPreview = document.getElementById('bodyPreview');
    const audiencePreview = document.getElementById('audiencePreview');

    if (subjectInput && subjectPreview) {
        subjectInput.addEventListener('input', (e) => {
            subjectPreview.textContent = e.target.value || 'Summer Internship Program';
        });
    }

    if (contentInput && bodyPreview) {
        contentInput.addEventListener('input', (e) => {
            bodyPreview.textContent = e.target.value || '';
        });
    }

    if (audienceSelect && audiencePreview) {
        audienceSelect.addEventListener('change', (e) => {
            audiencePreview.textContent = e.target.value + ' Accounts';
        });
    }
});
