/**
 * Watchdog - Environmental Case Monitor
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
    const categoryFilter = document.getElementById('filter-category');
    const confidenceFilter = document.getElementById('filter-confidence');
    const statusFilter = document.getElementById('filter-status');
    const searchInput = document.getElementById('search');
    const casesGrid = document.getElementById('cases-grid');

    if (!casesGrid) return;

    function filterCases() {
        const category = categoryFilter?.value || '';
        const confidence = confidenceFilter?.value || '';
        const status = statusFilter?.value || '';
        const search = searchInput?.value.toLowerCase().trim() || '';

        const cards = casesGrid.querySelectorAll('.case-card');
        let visibleCount = 0;

        cards.forEach(card => {
            const cardCategory = card.dataset.category || '';
            const cardConfidence = card.dataset.confidence || '';
            const cardStatus = card.dataset.status || '';
            const cardText = card.textContent.toLowerCase();

            let visible = true;

            // Category filter
            if (category && cardCategory !== category) {
                // Also match legacy categories
                const legacyMatch = (category === 'extraction' && cardCategory === 'permits') ||
                                   (category === 'energy' && cardCategory === 'industry');
                if (!legacyMatch) {
                    visible = false;
                }
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

            // Status filter
            if (status && cardStatus !== status) {
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
            if (category || confidence || status || search) {
                subtitle.textContent = `Showing ${visibleCount} of ${total} cases`;
            } else {
                subtitle.textContent = `Monitoring ${total} active cases across Lapland`;
            }
        }
    }

    // Attach listeners
    categoryFilter?.addEventListener('change', filterCases);
    confidenceFilter?.addEventListener('change', filterCases);
    statusFilter?.addEventListener('change', filterCases);

    // Debounce search input
    let searchTimeout;
    searchInput?.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(filterCases, 200);
    });
}

/**
 * Card action buttons (star, dismiss)
 */
function initCardActions() {
    // Star/save buttons
    document.querySelectorAll('.btn-star').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const isActive = btn.classList.toggle('active');
            btn.textContent = isActive ? '★' : '☆';
            btn.title = isActive ? 'Remove from watchlist' : 'Save to watchlist';

            // Visual feedback
            btn.style.transform = 'scale(1.2)';
            setTimeout(() => {
                btn.style.transform = '';
            }, 150);

            // TODO: API call to save action
            // const caseId = btn.closest('.case-card').dataset.caseId;
            // saveCaseAction(caseId, 'star', isActive);
        });
    });

    // Dismiss buttons
    document.querySelectorAll('.btn-dismiss').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const card = btn.closest('.case-card');

            // Smooth fade out
            card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            card.style.opacity = '0.3';
            card.style.transform = 'scale(0.98)';

            // Show undo option (simple version)
            btn.textContent = '↩';
            btn.title = 'Undo dismiss';

            const handleUndo = (e) => {
                e.preventDefault();
                e.stopPropagation();
                card.style.opacity = '';
                card.style.transform = '';
                btn.textContent = '×';
                btn.title = 'Dismiss';
                btn.removeEventListener('click', handleUndo);
                btn.addEventListener('click', arguments.callee);
            };

            btn.removeEventListener('click', arguments.callee);
            btn.addEventListener('click', handleUndo);

            // TODO: API call to dismiss
            // const caseId = card.dataset.caseId;
            // saveCaseAction(caseId, 'dismiss', true);
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
        submitBtn.textContent = 'Saving...';
        submitBtn.disabled = true;

        // TODO: Replace with actual API call
        setTimeout(() => {
            submitBtn.textContent = 'Saved!';

            setTimeout(() => {
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
                textarea.value = '';
            }, 1500);
        }, 500);
    });

    // Auto-resize textarea
    const noteTextarea = document.getElementById('note-input');
    noteTextarea?.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 300) + 'px';
    });
}

/**
 * Smooth scroll to element
 */
function scrollToElement(element, offset = 100) {
    const top = element.getBoundingClientRect().top + window.pageYOffset - offset;
    window.scrollTo({
        top: top,
        behavior: 'smooth'
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
