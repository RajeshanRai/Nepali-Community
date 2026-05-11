/**
 * Global delete confirmation handler.
 * Uses the shared GlobalUI confirm modal and DashboardPageTools CSRF helper.
 */

function resolveCsrfToken() {
    if (window.DashboardPageTools && typeof window.DashboardPageTools.getCsrfToken === 'function') {
        return window.DashboardPageTools.getCsrfToken();
    }

    const inputToken = document.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
    if (inputToken) {
        return inputToken;
    }

    const metaToken = document.querySelector('meta[name="csrf-token"]')?.content;
    if (metaToken) {
        return metaToken;
    }

    return '';
}

/**
 * Show delete confirmation modal
 * @param {Object} options - Configuration options
 * @param {string} options.url - DELETE endpoint URL
 * @param {string} options.itemName - Name of item being deleted (e.g., "Community: Nepal")
 * @param {string} options.itemType - Type of item (e.g., "category", "event", "opportunity")
 * @param {Object} options.dependencies - Optional dependency information
 * @param {number} options.dependencies.count - Total number of dependencies
 * @param {Array} options.dependencies.items - Array of dependency descriptions
 */
function confirmDelete(options) {
    const itemName = options?.itemName || 'this item';
    const hasDependencies = !!(options?.dependencies && options.dependencies.count > 0);

    let message = `Are you sure you want to delete "${itemName}"?`;
    if (hasDependencies) {
        const depCount = options.dependencies.count;
        message += ` This item has ${depCount} dependencies and may not be deletable until related items are removed or reassigned.`;
    } else {
        message += ' This action cannot be undone.';
    }

    const confirmPromise = window.GlobalUI
        ? window.GlobalUI.confirm({
            title: 'Confirm deletion',
            message,
            okText: 'Delete',
            variant: 'danger'
        })
        : Promise.resolve(false);

    confirmPromise.then((confirmed) => {
        if (!confirmed) {
            return;
        }

        const csrfToken = resolveCsrfToken();
        const formData = new FormData();
        if (csrfToken) {
            formData.append('csrfmiddlewaretoken', csrfToken);
        }

        fetch(options.url, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {})
            },
            body: formData
        })
            .then(async (response) => {
                const contentType = response.headers.get('content-type') || '';
                const payload = contentType.includes('application/json')
                    ? await response.json()
                    : await response.text();

                if (!response.ok) {
                    if (typeof payload === 'object' && payload) {
                        throw new Error(payload.error || payload.message || 'Delete failed');
                    }

                    if (typeof payload === 'string') {
                        throw new Error(payload.includes('CSRF')
                            ? 'Delete blocked by CSRF validation. Please refresh and try again.'
                            : 'Delete failed.');
                    }

                    throw new Error('Delete failed');
                }

                return payload;
            })
            .then((data) => {
                const messageText = typeof data === 'object' && data
                    ? (data.message || 'Item deleted successfully')
                    : 'Item deleted successfully';
                showToast(messageText, 'success');
                setTimeout(() => window.location.reload(), 700);
            })
            .catch((error) => {
                showToast(error.message || 'Failed to delete item', 'error');
            });
    });
}

/**
 * Close the delete confirmation modal
 */
function closeDeleteModal() {
    const modal = document.getElementById('deleteModal');
    if (modal) {
        modal.classList.remove('show');
    }
    document.body.classList.remove('modal-open');
}

/**
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} type - Toast type ('success', 'error', 'warning', 'info')
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const iconMap = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    toast.innerHTML = `
        <i class="fas ${iconMap[type] || iconMap.info}"></i>
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">&times;</button>
    `;

    container.appendChild(toast);

    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);

    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Close modal on ESC key
document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
        closeDeleteModal();
    }
});

// Close modal when clicking overlay
document.addEventListener('click', function (e) {
    if (e.target.classList.contains('modal-overlay')) {
        closeDeleteModal();
    }
});
