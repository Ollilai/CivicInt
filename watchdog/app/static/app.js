/**
 * Vahtikoira - Ympäristöpäätösten seuranta
 * Client-side interactivity
 */

document.addEventListener('DOMContentLoaded', () => {
    initFilters();
    initCardActions();
    initNotesForm();
});

/**
 * Filter functionality for case cards
 */
function initFilters() {
    const actionableFilter = document.getElementById('filter-actionable');
    const municipalityFilter = document.getElementById('filter-municipality');
    const categoryFilter = document.getElementById('filter-category');
    const searchInput = document.getElementById('search');
    const casesGrid = document.getElementById('cases-grid');

    if (!casesGrid) return;

    function filterCases() {
        const onlyActionable = actionableFilter?.checked ?? true;
        const municipality = municipalityFilter?.value || '';
        const category = categoryFilter?.value || '';
        const search = searchInput?.value.toLowerCase().trim() || '';

        const cards = casesGrid.querySelectorAll('.case-card');
        let visibleCount = 0;

        cards.forEach(card => {
            const cardCategory = card.dataset.category || '';
            const cardStatus = card.dataset.status || '';
            const cardMunicipality = card.dataset.municipality || '';
            const cardText = card.textContent.toLowerCase();

            let visible = true;

            // Actionable filter - show only cases with status 'proposed' (open for input)
            if (onlyActionable && cardStatus !== 'proposed') {
                visible = false;
            }

            // Municipality filter
            if (municipality && !cardMunicipality.includes(municipality)) {
                visible = false;
            }

            // Category filter
            if (category && cardCategory !== category) {
                visible = false;
            }

            // Search filter
            if (search && !cardText.includes(search)) {
                visible = false;
            }

            card.style.display = visible ? '' : 'none';
            if (visible) visibleCount++;
        });

        // Update subtitle with filtered count
        const subtitle = document.querySelector('.feed-subtitle');
        if (subtitle) {
            const total = cards.length;
            if (visibleCount === 0 && municipality) {
                subtitle.textContent = `Ei tapauksia kunnassa ${municipality}!`;
            } else if (visibleCount === 0) {
                subtitle.textContent = 'Ei hakuehtoja vastaavia tapauksia';
            } else if (municipality || category || search || onlyActionable) {
                const filterNote = onlyActionable ? ' avointa' : '';
                subtitle.textContent = `Näytetään ${visibleCount}${filterNote} tapausta`;
            } else {
                subtitle.textContent = `Seurannassa ${total} tapausta Lapin kunnista`;
            }
        }
    }

    // Attach listeners
    actionableFilter?.addEventListener('change', filterCases);
    municipalityFilter?.addEventListener('change', filterCases);
    categoryFilter?.addEventListener('change', filterCases);

    // Debounce search input
    let searchTimeout;
    searchInput?.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(filterCases, 200);
    });

    // Run initial filter
    filterCases();
}

/**
 * Card action buttons (star)
 */
function initCardActions() {
    // Star/save buttons
    document.querySelectorAll('.btn-star').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const isActive = btn.classList.toggle('active');
            btn.textContent = isActive ? '★' : '☆';
            btn.title = isActive ? 'Poista seurannasta' : 'Tallenna seurantaan';

            // Visual feedback
            btn.style.transform = 'scale(1.2)';
            setTimeout(() => {
                btn.style.transform = '';
            }, 150);

            // TODO: API call to save action
        });
    });
}

/**
 * Notes form on dossier page
 */
function initNotesForm() {
    const notesForm = document.querySelector('.notes-form');

    notesForm?.addEventListener('submit', (e) => {
        e.preventDefault();

        const textarea = document.getElementById('note-input');
        const submitBtn = notesForm.querySelector('button[type="submit"]');

        if (!textarea.value.trim()) {
            textarea.focus();
            return;
        }

        // Show saving state
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Tallennetaan...';
        submitBtn.disabled = true;

        // TODO: Replace with actual API call
        setTimeout(() => {
            submitBtn.textContent = 'Tallennettu!';

            setTimeout(() => {
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
                textarea.value = '';
            }, 1500);
        }, 500);
    });

    // Auto-resize textarea
    const noteTextarea = document.getElementById('note-input');
    noteTextarea?.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 300) + 'px';
    });
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fi-FI', {
        day: 'numeric',
        month: 'numeric',
        year: 'numeric'
    });
}
