// Watchdog MVP - JavaScript

document.addEventListener('DOMContentLoaded', () => {
    // Filter functionality
    const categoryFilter = document.getElementById('filter-category');
    const confidenceFilter = document.getElementById('filter-confidence');
    const searchInput = document.getElementById('search');
    const casesGrid = document.getElementById('cases-grid');

    function filterCases() {
        if (!casesGrid) return;

        const category = categoryFilter?.value || '';
        const confidence = confidenceFilter?.value || '';
        const search = searchInput?.value.toLowerCase() || '';

        const cards = casesGrid.querySelectorAll('.case-card');

        cards.forEach(card => {
            const cardCategory = card.dataset.category || '';
            const cardConfidence = card.dataset.confidence || '';
            const cardText = card.textContent.toLowerCase();

            let visible = true;

            // Category filter
            if (category && cardCategory !== category) {
                visible = false;
            }

            // Confidence filter
            if (confidence) {
                if (confidence === 'high' && cardConfidence !== 'high') {
                    visible = false;
                }
                if (confidence === 'medium' && cardConfidence === 'low') {
                    visible = false;
                }
            }

            // Search filter
            if (search && !cardText.includes(search)) {
                visible = false;
            }

            card.style.display = visible ? '' : 'none';
        });
    }

    categoryFilter?.addEventListener('change', filterCases);
    confidenceFilter?.addEventListener('change', filterCases);
    searchInput?.addEventListener('input', filterCases);

    // Star/dismiss buttons
    document.querySelectorAll('.btn-star').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            btn.classList.toggle('active');
            btn.textContent = btn.classList.contains('active') ? '⭐' : '☆';
            // TODO: API call to save action
        });
    });

    document.querySelectorAll('.btn-dismiss').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const card = btn.closest('.case-card');
            card.style.opacity = '0.5';
            // TODO: API call to save action
        });
    });

    // Notes form
    const notesForm = document.querySelector('.notes-form');
    notesForm?.addEventListener('submit', (e) => {
        e.preventDefault();
        const textarea = document.getElementById('note-input');
        if (textarea.value.trim()) {
            // TODO: API call to save note
            alert('Note saved!');
            textarea.value = '';
        }
    });
});
