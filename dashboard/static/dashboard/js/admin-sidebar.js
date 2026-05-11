// ===================================
// ADMIN DASHBOARD - SIDEBAR JAVASCRIPT
// ===================================

// Global state
let sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
const SIDEBAR_SCROLL_KEY = 'dashboardSidebarScrollTop';

// Initialize sidebar functionality
function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const mobileToggle = document.getElementById('mobileToggle');
    const sidebarNav = document.querySelector('.sidebar-nav');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');
    const sidebarQuickFilter = document.getElementById('sidebarQuickFilter');

    if (!sidebar || sidebar.dataset.sidebarInitialized === 'true') {
        return;
    }
    sidebar.dataset.sidebarInitialized = 'true';

    const sectionCounterState = new WeakMap();

    function animateSectionCount(node, fromValue, toValue) {
        const start = Number.isFinite(fromValue) ? fromValue : 0;
        const end = Number.isFinite(toValue) ? toValue : 0;

        if (start === end) {
            node.textContent = String(end);
            return;
        }

        const duration = 220;
        const startTime = performance.now();
        node.classList.add('is-updating');

        function tick(now) {
            const elapsed = now - startTime;
            const progress = Math.min(1, elapsed / duration);
            const current = Math.round(start + ((end - start) * progress));
            node.textContent = String(current);

            if (progress < 1) {
                requestAnimationFrame(tick);
            } else {
                node.classList.remove('is-updating');
                node.textContent = String(end);
            }
        }

        requestAnimationFrame(tick);
    }

    function updateSectionCounters() {
        document.querySelectorAll('.sidebar .nav-section').forEach((section) => {
            const title = section.querySelector('.nav-section-title');
            if (!title) return;

            let countNode = title.querySelector('.nav-section-count');
            if (!countNode) {
                countNode = document.createElement('span');
                countNode.className = 'nav-section-count';
                countNode.textContent = '0';
                title.appendChild(countNode);
            }

            const visibleItems = Array.from(section.querySelectorAll('.nav-item')).filter((item) => {
                if (item.classList.contains('is-filtered-out')) return false;
                return item.style.display !== 'none';
            }).length;

            const previous = sectionCounterState.has(countNode)
                ? sectionCounterState.get(countNode)
                : Number(countNode.textContent || '0');

            animateSectionCount(countNode, Number(previous || 0), visibleItems);
            sectionCounterState.set(countNode, visibleItems);
        });
    }

    function persistSidebarScroll() {
        if (!sidebarNav) return;
        sessionStorage.setItem(SIDEBAR_SCROLL_KEY, String(sidebarNav.scrollTop));
    }

    function restoreSidebarScroll() {
        if (!sidebarNav) return;
        const savedScroll = Number(sessionStorage.getItem(SIDEBAR_SCROLL_KEY));
        if (Number.isFinite(savedScroll) && savedScroll >= 0) {
            sidebarNav.scrollTop = savedScroll;
        }
    }

    restoreSidebarScroll();

    // Apply collapsed state from localStorage
    if (sidebarCollapsed && window.innerWidth > 1024) {
        sidebar.classList.add('collapsed');
    }

    function setSidebarToggleState() {
        if (!sidebarToggle) {
            return;
        }
        const isExpanded = window.innerWidth <= 1024
            ? sidebar.classList.contains('show')
            : !sidebar.classList.contains('collapsed');
        sidebarToggle.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
    }

    function syncMobileState() {
        const isMobile = window.innerWidth <= 1024;
        const isOpen = sidebar.classList.contains('show');
        document.body.classList.toggle('sidebar-mobile-open', isMobile && isOpen);
        if (sidebarBackdrop) {
            sidebarBackdrop.setAttribute('aria-hidden', isMobile && isOpen ? 'false' : 'true');
        }
        setSidebarToggleState();
    }

    function toggleDesktopSidebar() {
        sidebar.classList.toggle('collapsed');
        sidebarCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', String(sidebarCollapsed));
        setSidebarToggleState();
        updateSectionCounters();
    }

    function toggleMobileSidebar() {
        sidebar.classList.toggle('show');
        syncMobileState();
    }

    function closeMobileSidebar() {
        sidebar.classList.remove('show');
        syncMobileState();
    }

    function handleSidebarToggleClick(event) {
        event.preventDefault();
        event.stopPropagation();

        if (window.innerWidth <= 1024) {
            toggleMobileSidebar();
            return;
        }

        toggleDesktopSidebar();
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', handleSidebarToggleClick);
    }

    if (mobileToggle) {
        mobileToggle.addEventListener('click', handleSidebarToggleClick);
    }

    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener('click', function () {
            if (window.innerWidth <= 1024) {
                closeMobileSidebar();
            }
        });
    }

    // Close sidebar on mobile when clicking outside
    document.addEventListener('click', function (e) {
        if (window.innerWidth <= 1024) {
            const sidebar = document.getElementById('sidebar');
            const mobileToggle = document.getElementById('mobileToggle');

            if (!sidebar) {
                return;
            }

            const clickedInsideSidebar = sidebar.contains(e.target);
            const clickedMobileToggle = mobileToggle ? mobileToggle.contains(e.target) : false;

            if (!clickedInsideSidebar && !clickedMobileToggle) {
                closeMobileSidebar();
            }
        }
    });

    // Close sidebar on mobile when clicking nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function () {
            persistSidebarScroll();
            if (window.innerWidth <= 1024) {
                closeMobileSidebar();
            }
        });
    });

    document.querySelectorAll('.nav-section-title').forEach((titleNode) => {
        titleNode.setAttribute('role', 'button');
        titleNode.setAttribute('tabindex', '0');
        const sectionNode = titleNode.closest('.nav-section');
        if (!sectionNode) return;

        function toggleSection() {
            sectionNode.classList.toggle('is-collapsed');
            const collapsed = sectionNode.classList.contains('is-collapsed');
            sectionNode.querySelectorAll('.nav-item').forEach((item) => {
                item.style.display = collapsed ? 'none' : '';
            });
            updateSectionCounters();
        }

        titleNode.addEventListener('click', () => {
            if (sidebar.classList.contains('collapsed')) return;
            if (window.innerWidth > 768) return;
            toggleSection();
        });

        titleNode.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            if (sidebar.classList.contains('collapsed')) return;
            if (window.innerWidth > 768) return;
            toggleSection();
        });
    });

    if (sidebarQuickFilter) {
        sidebarQuickFilter.addEventListener('input', function (event) {
            const query = String(event.target.value || '').trim().toLowerCase();
            const items = Array.from(document.querySelectorAll('.sidebar .nav-item'));

            items.forEach((item) => {
                const text = item.textContent ? item.textContent.toLowerCase() : '';
                const matches = !query || text.includes(query);
                item.classList.toggle('is-filtered-out', !matches);
            });

            document.querySelectorAll('.sidebar .nav-section').forEach((section) => {
                const visibleCount = section.querySelectorAll('.nav-item:not(.is-filtered-out)').length;
                section.style.display = visibleCount > 0 ? '' : 'none';
            });

            updateSectionCounters();
        });
    }

    if (sidebarNav) {
        sidebarNav.addEventListener('scroll', persistSidebarScroll, { passive: true });
    }

    window.addEventListener('beforeunload', persistSidebarScroll);

    window.addEventListener('resize', function () {
        if (window.innerWidth > 1024) {
            sidebar.classList.remove('show');
        }
        if (window.innerWidth > 768) {
            document.querySelectorAll('.sidebar .nav-section').forEach((section) => {
                section.classList.remove('is-collapsed');
                section.style.display = '';
                section.querySelectorAll('.nav-item').forEach((item) => {
                    if (!item.classList.contains('is-filtered-out')) {
                        item.style.display = '';
                    }
                });
            });
        }
        syncMobileState();
        updateSectionCounters();
    });

    syncMobileState();
    updateSectionCounters();
}

// Initialize dropdowns
function initDropdowns() {
    // Notifications dropdown
    const notificationBtn = document.getElementById('notificationBtn');
    const notificationsMenu = document.getElementById('notificationsMenu');

    if (notificationBtn && notificationsMenu) {
        notificationBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            notificationsMenu.classList.toggle('show');

            // Close user menu if open
            const userMenu = document.getElementById('userMenu');
            if (userMenu) {
                userMenu.classList.remove('show');
            }
        });
    }

    // User dropdown
    const userBtn = document.getElementById('userBtn');
    const userMenu = document.getElementById('userMenu');

    if (userBtn && userMenu) {
        userBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            userMenu.classList.toggle('show');
            userBtn.setAttribute('aria-expanded', userMenu.classList.contains('show') ? 'true' : 'false');

            // Close notifications menu if open
            if (notificationsMenu) {
                notificationsMenu.classList.remove('show');
            }
        });
    }

    // Close dropdowns when clicking outside
    document.addEventListener('click', function () {
        if (notificationsMenu) {
            notificationsMenu.classList.remove('show');
        }
        if (userMenu) {
            userMenu.classList.remove('show');
        }
        if (userBtn) {
            userBtn.setAttribute('aria-expanded', 'false');
        }
    });

    // Prevent dropdown from closing when clicking inside
    if (notificationsMenu) {
        notificationsMenu.addEventListener('click', function (e) {
            e.stopPropagation();
        });
    }

    if (userMenu) {
        userMenu.addEventListener('click', function (e) {
            e.stopPropagation();
        });
    }
}

// Initialize global search
function initGlobalSearch() {
    const searchInput = document.getElementById('globalSearch');

    if (searchInput) {
        let searchTimeout;

        searchInput.addEventListener('input', function (e) {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();

            if (query.length < 2) return;

            searchTimeout = setTimeout(() => {
                performGlobalSearch(query);
            }, 500);
        });

        // Search on Enter key
        searchInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const query = e.target.value.trim();
                if (query.length >= 2) {
                    performGlobalSearch(query);
                }
            }
        });
    }
}

function normalizePath(path) {
    if (!path) return '/';
    return path.length > 1 && path.endsWith('/') ? path.slice(0, -1) : path;
}

function extractPathFromElement(element) {
    if (!element) return null;

    if (element.matches('a[href]')) {
        try {
            const url = new URL(element.getAttribute('href'), window.location.origin);
            return normalizePath(url.pathname);
        } catch {
            return null;
        }
    }

    const onClick = element.getAttribute('onclick') || '';
    const match = onClick.match(/window\.location\.href\s*=\s*['"]([^'"]+)['"]/);
    if (match && match[1]) {
        try {
            const url = new URL(match[1], window.location.origin);
            return normalizePath(url.pathname);
        } catch {
            return null;
        }
    }

    return null;
}

function getMatchScore(targetPath, currentPath) {
    if (!targetPath || targetPath === '#') return -1;
    if (currentPath === targetPath) return 1000 + targetPath.length;
    if (currentPath.startsWith(`${targetPath}/`)) return 500 + targetPath.length;
    return -1;
}

function shouldUseExactDashboardMatch(element) {
    return !!element.closest('.page-header-actions');
}

function initRouteHighlights() {
    const currentPath = normalizePath(window.location.pathname);

    const navItems = Array.from(document.querySelectorAll('.sidebar .nav-item'));
    navItems.forEach(item => item.classList.remove('active', 'route-active'));

    let bestNavItem = null;
    let bestNavScore = -1;

    navItems.forEach(item => {
        const itemPath = extractPathFromElement(item);
        const score = getMatchScore(itemPath, currentPath);
        if (score > bestNavScore) {
            bestNavScore = score;
            bestNavItem = item;
        }
    });

    if (bestNavItem) {
        bestNavItem.classList.add('active', 'route-active');
    }

    const dashboardTargets = Array.from(document.querySelectorAll(
        '.quick-action-card, .stat-link, .view-all-link, .action-btn, .page-header-actions .btn, .sidebar-favorite-link'
    ));

    dashboardTargets.forEach(item => {
        if (item.hasAttribute('data-ignore-route-highlight')) {
            return;
        }
        item.classList.remove('dashboard-route-active');
        const itemPath = extractPathFromElement(item);
        const score = getMatchScore(itemPath, currentPath);
        const matches = shouldUseExactDashboardMatch(item)
            ? score >= 1000
            : score >= 0;
        if (matches) {
            item.classList.add('dashboard-route-active');
        }
    });
}

// Perform global search
function performGlobalSearch(query) {
    console.log('Searching for:', query);

    // Show search results dropdown
    showSearchResults([
        { type: 'project', title: 'Sample Project', url: '#' },
        { type: 'user', title: query, url: '#' },
        { type: 'volunteer', title: 'Volunteer Opportunity', url: '#' }
    ]);
}

// Show search results
function showSearchResults(results) {
    // TODO: Implement search results dropdown
    console.log('Search results:', results);
}

// Toast notification system
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');

    if (!toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icon = getToastIcon(type);

    toast.innerHTML = `
        <i class="fas fa-${icon}"></i>
        <span>${message}</span>
    `;

    toastContainer.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 5000);
}

function getToastIcon(type) {
    const icons = {
        success: 'check-circle',
        error: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Confirmation modal
function confirmAction(message, onConfirm) {
    const confirmPromise = window.GlobalUI.confirm({
        title: 'Please confirm',
        message,
        okText: 'Confirm'
    });

    confirmPromise.then((confirmed) => {
        if (confirmed) {
            onConfirm();
        }
    });
}

// Auto-dismiss alerts
document.addEventListener('DOMContentLoaded', function () {
    const alerts = document.querySelectorAll('.alert');

    alerts.forEach(alert => {
        const closeBtn = alert.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function () {
                alert.style.animation = 'fadeOut 0.3s ease';
                setTimeout(() => {
                    alert.remove();
                }, 300);
            });
        }

        // Auto dismiss after 5 seconds
        setTimeout(() => {
            if (alert.parentElement) {
                alert.style.animation = 'fadeOut 0.3s ease';
                setTimeout(() => {
                    alert.remove();
                }, 300);
            }
        }, 5000);
    });
});

// Expose global functions
window.showToast = showToast;
window.confirmAction = confirmAction;
window.initRouteHighlights = initRouteHighlights;

// AJAX helper function
function csrfSafeMethod(method) {
    return /^(GET|HEAD|OPTIONS|TRACE)$/.test(method);
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Setup AJAX with CSRF token
const csrftoken = document.querySelector('meta[name="csrf-token"]')?.content || getCookie('csrftoken') || '';

if (typeof window.fetch !== 'undefined') {
    const originalFetch = window.fetch;
    window.fetch = function (url, options = {}) {
        if (!csrfSafeMethod(options.method || 'GET') && csrftoken) {
            options.headers = options.headers || {};
            options.headers['X-CSRFToken'] = csrftoken;
        }
        return originalFetch(url, options);
    };
}

// Handle bulk actions
function initBulkActions() {
    const bulkSelectAll = document.getElementById('bulkSelectAll');
    const bulkCheckboxes = document.querySelectorAll('.bulk-checkbox');
    const bulkActionBtn = document.getElementById('bulkActionBtn');

    if (bulkSelectAll) {
        bulkSelectAll.addEventListener('change', function () {
            bulkCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateBulkActionButton();
        });
    }

    bulkCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateBulkActionButton);
    });

    function updateBulkActionButton() {
        const checkedCount = document.querySelectorAll('.bulk-checkbox:checked').length;
        if (bulkActionBtn) {
            bulkActionBtn.textContent = `Actions (${checkedCount})`;
            bulkActionBtn.disabled = checkedCount === 0;
        }
    }
}

// Export functionality
function exportData(format, endpoint) {
    showToast(`Exporting data as ${format.toUpperCase()}...`, 'info');

    // Create a temporary download link
    const link = document.createElement('a');
    link.href = `${endpoint}?format=${format}`;
    link.download = `export_${Date.now()}.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setTimeout(() => {
        showToast('Export completed successfully', 'success');
    }, 1000);
}

window.exportData = exportData;
window.initBulkActions = initBulkActions;

// Loading spinner
function showLoading() {
    const overlay = document.createElement('div');
    overlay.id = 'loadingOverlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;
    overlay.innerHTML = `
        <div style="background: white; padding: 30px; border-radius: 12px; text-align: center;">
            <i class="fas fa-spinner fa-spin" style="font-size: 40px; color: #3B82F6;"></i>
            <p style="margin-top: 15px; font-size: 16px; color: #1F2937;">Loading...</p>
        </div>
    `;
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.remove();
    }
}

window.showLoading = showLoading;
window.hideLoading = hideLoading;

console.log('Admin Dashboard JavaScript loaded successfully');
