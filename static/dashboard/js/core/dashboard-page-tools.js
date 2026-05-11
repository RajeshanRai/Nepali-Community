(function () {
    const DashboardPageTools = window.DashboardPageTools = window.DashboardPageTools || {};

    DashboardPageTools.getCsrfToken = function () {
        const inputToken = document.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
        if (inputToken) {
            return inputToken;
        }

        const metaToken = document.querySelector('meta[name="csrf-token"]')?.content;
        if (metaToken) {
            return metaToken;
        }

        const cookieName = 'csrftoken';
        const cookies = document.cookie ? document.cookie.split(';') : [];
        for (const rawCookie of cookies) {
            const cookie = rawCookie.trim();
            if (cookie.startsWith(cookieName + '=')) {
                return decodeURIComponent(cookie.slice(cookieName.length + 1));
            }
        }

        return '';
    };

    DashboardPageTools.showToast = function (message, type = 'info') {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
            return;
        }

        const container = document.getElementById('toastContainer');
        if (!container) {
            return;
        }

        const toast = document.createElement('div');
        toast.className = 'toast toast-' + type;
        toast.innerHTML = [
            '<i class="fas fa-',
            type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle',
            '"></i><span>',
            message,
            '</span>'
        ].join('');

        container.appendChild(toast);
        window.setTimeout(() => toast.remove(), 3000);
    };

    DashboardPageTools.replaceIdToken = function (template, id) {
        return (template || '').replace('__id__', String(id));
    };

    DashboardPageTools.postForm = async function (url, data = {}, fetchOptions = {}) {
        const formData = new FormData();
        const csrfToken = DashboardPageTools.getCsrfToken();

        if (csrfToken) {
            formData.append('csrfmiddlewaretoken', csrfToken);
        }

        Object.entries(data).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                formData.append(key, value);
            }
        });

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                ...(fetchOptions.headers || {})
            },
            body: formData,
            ...fetchOptions
        });

        const contentType = response.headers.get('content-type') || '';
        const payload = contentType.includes('application/json')
            ? await response.json()
            : await response.text();

        if (!response.ok) {
            const errorMessage = typeof payload === 'string'
                ? payload.slice(0, 200)
                : payload.message || 'Request failed';
            throw new Error(errorMessage);
        }

        return payload;
    };

    DashboardPageTools.bindActionButtons = function (root = document) {
        root.querySelectorAll('[data-dashboard-navigate]').forEach((element) => {
            if (element.dataset.dashboardBound === 'true') {
                return;
            }

            element.dataset.dashboardBound = 'true';
            element.addEventListener('click', function () {
                const targetUrl = this.dataset.dashboardNavigate;
                if (targetUrl) {
                    window.location.href = targetUrl;
                }
            });
        });

        root.querySelectorAll('[data-dashboard-delete-url]').forEach((element) => {
            if (element.dataset.dashboardBound === 'true') {
                return;
            }

            element.dataset.dashboardBound = 'true';
            element.addEventListener('click', function () {
                if (typeof window.confirmDelete !== 'function') {
                    return;
                }

                window.confirmDelete({
                    url: this.dataset.dashboardDeleteUrl,
                    itemName: this.dataset.itemName || 'item',
                    itemType: this.dataset.itemType || 'record'
                });
            });
        });
    };

    DashboardPageTools.initRowSearch = function ({ input, rows, textSelector, onUpdate } = {}) {
        if (!input || !rows?.length) {
            return;
        }

        const filter = function () {
            const searchTerm = input.value.trim().toLowerCase();
            let visibleCount = 0;

            rows.forEach((row) => {
                const sourceText = textSelector ? textSelector(row) : row.textContent;
                const isVisible = !searchTerm || String(sourceText).toLowerCase().includes(searchTerm);
                row.style.display = isVisible ? '' : 'none';
                if (isVisible) {
                    visibleCount += 1;
                }
            });

            if (typeof onUpdate === 'function') {
                onUpdate(visibleCount);
            }
        };

        input.addEventListener('input', filter);
    };

    DashboardPageTools.initButtonFilters = function ({ buttons, rows, rowAttribute, onUpdate } = {}) {
        if (!buttons?.length || !rows?.length || !rowAttribute) {
            return;
        }

        buttons.forEach((button) => {
            button.addEventListener('click', function () {
                buttons.forEach((item) => item.classList.remove('active'));
                this.classList.add('active');

                const filterValue = this.dataset.filter;
                let visibleCount = 0;

                rows.forEach((row) => {
                    const matches = filterValue === 'all' || row.dataset[rowAttribute] === filterValue;
                    row.style.display = matches ? '' : 'none';
                    if (matches) {
                        visibleCount += 1;
                    }
                });

                if (typeof onUpdate === 'function') {
                    onUpdate(visibleCount);
                }
            });
        });
    };

    DashboardPageTools.initBulkSelection = function ({ masterCheckbox, itemCheckboxes } = {}) {
        if (!masterCheckbox || !itemCheckboxes?.length) {
            return;
        }

        masterCheckbox.addEventListener('change', function () {
            itemCheckboxes.forEach((checkbox) => {
                checkbox.checked = this.checked;
            });
        });
    };

    document.addEventListener('DOMContentLoaded', function () {
        DashboardPageTools.bindActionButtons();
    });
})();
