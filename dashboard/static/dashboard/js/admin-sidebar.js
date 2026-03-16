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

    if (!sidebar || sidebar.dataset.sidebarInitialized === 'true') {
        return;
    }
    sidebar.dataset.sidebarInitialized = 'true';

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

    function toggleDesktopSidebar() {
        sidebar.classList.toggle('collapsed');
        sidebarCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', String(sidebarCollapsed));
    }

    function toggleMobileSidebar() {
        sidebar.classList.toggle('show');
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
                sidebar.classList.remove('show');
            }
        }
    });

    // Close sidebar on mobile when clicking nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function () {
            persistSidebarScroll();
            if (window.innerWidth <= 1024) {
                sidebar.classList.remove('show');
            }
        });
    });

    if (sidebarNav) {
        sidebarNav.addEventListener('scroll', persistSidebarScroll, { passive: true });
    }

    window.addEventListener('beforeunload', persistSidebarScroll);
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
        '.quick-action-card, .stat-link, .view-all-link, .action-btn, .page-header-actions .btn'
    ));

    dashboardTargets.forEach(item => {
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
