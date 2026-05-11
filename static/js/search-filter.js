/**
 * Enhanced Search and Filter Utility
 * Provides global search functionality with advanced filtering
 */

(function () {
    'use strict';

    /**
     * Initialize all search and filter functionality
     */
    function init() {
        initGlobalSearch();
        initAdvancedFilters();
        initSearchHistory();
        initQuickFilters();
    }

    /**
     * Global Search - Searches across multiple content types
     */
    function initGlobalSearch() {
        const globalSearchInput = document.getElementById('global-search');
        if (!globalSearchInput) return;

        const searchResults = document.getElementById('global-search-results');
        const searchOverlay = document.getElementById('search-overlay');
        let searchTimeout;

        globalSearchInput.addEventListener('input', function (e) {
            const query = e.target.value.trim();

            clearTimeout(searchTimeout);

            if (query.length < 2) {
                hideSearchResults();
                return;
            }

            searchTimeout = setTimeout(() => {
                performGlobalSearch(query);
            }, 300); // Debounce 300ms
        });

        // Close search on outside click
        document.addEventListener('click', function (e) {
            if (!e.target.closest('.global-search-container')) {
                hideSearchResults();
            }
        });

        // Keyboard navigation
        globalSearchInput.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                hideSearchResults();
                globalSearchInput.blur();
            }
        });

        function hideSearchResults() {
            if (searchResults) searchResults.style.display = 'none';
            if (searchOverlay) searchOverlay.style.display = 'none';
        }
    }

    /**
     * Perform global search across all content
     */
    async function performGlobalSearch(query) {
        const resultsContainer = document.getElementById('global-search-results');
        if (!resultsContainer) return;

        resultsContainer.style.display = 'block';
        resultsContainer.innerHTML = '<div class="search-loading"><i class="fas fa-spinner fa-spin"></i> Searching...</div>';

        try {
            const response = await fetch(`/api/search/?q=${encodeURIComponent(query)}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                displaySearchResults(data.results, query);
                saveSearchHistory(query);
            } else {
                resultsContainer.innerHTML = '<div class="search-error">Failed to search. Please try again.</div>';
            }
        } catch (error) {
            console.error('Search error:', error);
            resultsContainer.innerHTML = '<div class="search-error">An error occurred. Please try again.</div>';
        }
    }

    /**
     * Display search results
     */
    function displaySearchResults(results, query) {
        const resultsContainer = document.getElementById('global-search-results');
        if (!resultsContainer) return;

        if (results.length === 0) {
            resultsContainer.innerHTML = `
                <div class="search-no-results">
                    <i class="fas fa-search"></i>
                    <p>No results found for "${query}"</p>
                </div>
            `;
            return;
        }

        // Group results by type
        const grouped = results.reduce((acc, result) => {
            if (!acc[result.type]) acc[result.type] = [];
            acc[result.type].push(result);
            return acc;
        }, {});

        let html = '';
        const typeLabels = {
            'event': 'Events & Programs',
            'community': 'Communities',
            'volunteer': 'Volunteer Opportunities',
            'announcement': 'Announcements'
        };

        Object.keys(grouped).forEach(type => {
            html += `<div class="search-group">
                <h4 class="search-group-title">${typeLabels[type] || type}</h4>`;

            grouped[type].forEach(result => {
                html += `
                    <a href="${result.url}" class="search-result-item">
                        <div class="search-result-icon">
                            <i class="${result.icon || 'fas fa-file'}"></i>
                        </div>
                        <div class="search-result-content">
                            <div class="search-result-title">${highlightQuery(result.title, query)}</div>
                            ${result.description ? `<div class="search-result-description">${highlightQuery(result.description, query)}</div>` : ''}
                            ${result.date ? `<div class="search-result-meta"><i class="fas fa-calendar"></i> ${result.date}</div>` : ''}
                        </div>
                    </a>
                `;
            });

            html += '</div>';
        });

        resultsContainer.innerHTML = html;
    }

    /**
     * Highlight search query in results
     */
    function highlightQuery(text, query) {
        if (!text || !query) return text;

        const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    /**
     * Escape special regex characters
     */
    function escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    /**
     * Advanced Filters
     */
    function initAdvancedFilters() {
        const filterToggles = document.querySelectorAll('[data-filter-toggle]');

        filterToggles.forEach(toggle => {
            toggle.addEventListener('click', function () {
                const targetId = this.getAttribute('data-filter-toggle');
                const target = document.getElementById(targetId);

                if (target) {
                    target.classList.toggle('filter-expanded');
                    const icon = this.querySelector('i');
                    if (icon) {
                        icon.classList.toggle('fa-chevron-down');
                        icon.classList.toggle('fa-chevron-up');
                    }
                }
            });
        });

        // Multi-select filters
        initMultiSelectFilters();

        // Date range filters
        initDateRangeFilters();

        // Reset filters
        const resetButtons = document.querySelectorAll('[data-reset-filters]');
        resetButtons.forEach(btn => {
            btn.addEventListener('click', resetFilters);
        });
    }

    /**
     * Multi-select filters
     */
    function initMultiSelectFilters() {
        const multiSelects = document.querySelectorAll('[data-multi-select]');

        multiSelects.forEach(select => {
            const options = select.querySelectorAll('input[type="checkbox"]');

            options.forEach(option => {
                option.addEventListener('change', function () {
                    updateFilters();
                });
            });
        });
    }

    /**
     * Date range filters
     */
    function initDateRangeFilters() {
        const dateRangeInputs = document.querySelectorAll('[data-date-range]');

        dateRangeInputs.forEach(input => {
            input.addEventListener('change', function () {
                validateDateRange();
                updateFilters();
            });
        });
    }

    /**
     * Validate date range
     */
    function validateDateRange() {
        const startDate = document.querySelector('[data-date-range="start"]');
        const endDate = document.querySelector('[data-date-range="end"]');

        if (startDate && endDate && startDate.value && endDate.value) {
            if (new Date(startDate.value) > new Date(endDate.value)) {
                endDate.value = startDate.value;
                showNotification('End date cannot be before start date', 'warning');
            }
        }
    }

    /**
     * Update filters and refresh results
     */
    function updateFilters() {
        const filters = collectActiveFilters();
        applyFilters(filters);
    }

    /**
     * Collect all active filters
     */
    function collectActiveFilters() {
        const filters = {};

        // Multi-select checkboxes
        document.querySelectorAll('[data-multi-select]').forEach(container => {
            const filterName = container.getAttribute('data-multi-select');
            const checked = container.querySelectorAll('input[type="checkbox"]:checked');

            if (checked.length > 0) {
                filters[filterName] = Array.from(checked).map(cb => cb.value);
            }
        });

        // Date ranges
        const startDate = document.querySelector('[data-date-range="start"]');
        const endDate = document.querySelector('[data-date-range="end"]');

        if (startDate && startDate.value) {
            filters.start_date = startDate.value;
        }
        if (endDate && endDate.value) {
            filters.end_date = endDate.value;
        }

        // Single selects
        document.querySelectorAll('[data-filter-select]').forEach(select => {
            if (select.value) {
                const filterName = select.getAttribute('data-filter-select');
                filters[filterName] = select.value;
            }
        });

        return filters;
    }

    /**
     * Apply filters to results
     */
    function applyFilters(filters) {
        const params = new URLSearchParams();

        Object.keys(filters).forEach(key => {
            if (Array.isArray(filters[key])) {
                filters[key].forEach(value => params.append(key, value));
            } else {
                params.set(key, filters[key]);
            }
        });

        // Update URL without reload (for browser back button)
        const newUrl = `${window.location.pathname}?${params.toString()}`;
        window.history.pushState({}, '', newUrl);

        // Reload page with filters or use AJAX
        window.location.href = newUrl;
    }

    /**
     * Reset all filters
     */
    function resetFilters() {
        // Clear all checkboxes
        document.querySelectorAll('[data-multi-select] input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });

        // Clear date ranges
        document.querySelectorAll('[data-date-range]').forEach(input => {
            input.value = '';
        });

        // Clear selects
        document.querySelectorAll('[data-filter-select]').forEach(select => {
            select.selectedIndex = 0;
        });

        // Reload without params
        window.location.href = window.location.pathname;
    }

    /**
     * Search History
     */
    function initSearchHistory() {
        displaySearchHistory();
    }

    /**
     * Save search to history
     */
    function saveSearchHistory(query) {
        if (!query || query.length < 2) return;

        let history = JSON.parse(localStorage.getItem('searchHistory') || '[]');

        // Remove duplicates
        history = history.filter(item => item !== query);

        // Add to beginning
        history.unshift(query);

        // Keep only last 10
        history = history.slice(0, 10);

        localStorage.setItem('searchHistory', JSON.stringify(history));
    }

    /**
     * Display search history
     */
    function displaySearchHistory() {
        const historyContainer = document.getElementById('search-history');
        if (!historyContainer) return;

        const history = JSON.parse(localStorage.getItem('searchHistory') || '[]');

        if (history.length === 0) {
            historyContainer.style.display = 'none';
            return;
        }

        let html = '<h5>Recent Searches</h5><ul class="search-history-list">';

        history.forEach(query => {
            html += `
                <li>
                    <a href="?q=${encodeURIComponent(query)}" class="search-history-item">
                        <i class="fas fa-history"></i> ${query}
                    </a>
                    <button class="search-history-remove" data-query="${query}">
                        <i class="fas fa-times"></i>
                    </button>
                </li>
            `;
        });

        html += '</ul>';
        historyContainer.innerHTML = html;

        // Remove from history
        historyContainer.querySelectorAll('.search-history-remove').forEach(btn => {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                const query = this.getAttribute('data-query');
                removeFromHistory(query);
            });
        });
    }

    /**
     * Remove item from search history
     */
    function removeFromHistory(query) {
        let history = JSON.parse(localStorage.getItem('searchHistory') || '[]');
        history = history.filter(item => item !== query);
        localStorage.setItem('searchHistory', JSON.stringify(history));
        displaySearchHistory();
    }

    /**
     * Quick Filters - Single click filters
     */
    function initQuickFilters() {
        const quickFilters = document.querySelectorAll('[data-quick-filter]');

        quickFilters.forEach(filter => {
            filter.addEventListener('click', function (e) {
                e.preventDefault();

                const filterValue = this.getAttribute('data-quick-filter');
                const filterType = this.getAttribute('data-filter-type');

                // Remove active class from siblings
                this.parentElement.querySelectorAll('[data-quick-filter]').forEach(f => {
                    f.classList.remove('active');
                });

                // Add active class
                this.classList.add('active');

                // Apply quick filter
                applyQuickFilter(filterType, filterValue);
            });
        });
    }

    /**
     * Apply quick filter
     */
    function applyQuickFilter(type, value) {
        const params = new URLSearchParams(window.location.search);

        if (value === 'all' || !value) {
            params.delete(type);
        } else {
            params.set(type, value);
        }

        window.location.href = `${window.location.pathname}?${params.toString()}`;
    }

    /**
     * Show notification
     */
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `filter-notification filter-notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = 'position:fixed;top:2rem;right:2rem;padding:1rem 1.5rem;background:#2196f3;color:white;border-radius:8px;z-index:10000;animation:slideIn 0.3s ease;';

        if (type === 'warning') {
            notification.style.background = '#ff9800';
        } else if (type === 'error') {
            notification.style.background = '#f44336';
        }

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => document.body.removeChild(notification), 300);
        }, 3000);
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Export for external use
    window.SearchFilter = {
        performGlobalSearch,
        applyFilters,
        resetFilters,
        saveSearchHistory
    };

})();
