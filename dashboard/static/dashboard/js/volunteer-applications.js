(function () {
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i += 1) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === `${name}=`) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function isValidCsrfToken(value) {
        return typeof value === 'string'
            && value !== 'NOTPROVIDED'
            && value !== 'undefined'
            && value !== 'null'
            && (value.length === 32 || value.length === 64);
    }

    function getCsrfToken() {
        const candidates = [];

        document.querySelectorAll('input[name="csrfmiddlewaretoken"]').forEach((input) => {
            candidates.push(input.value);
        });

        const hiddenToken = document.getElementById('csrfTokenValue');
        if (hiddenToken) {
            candidates.push(hiddenToken.value);
        }

        candidates.push(getCookie('csrftoken'));

        const valid = candidates.find((token) => isValidCsrfToken(token));
        return valid || '';
    }

    function notify(message, type) {
        if (typeof showToast === 'function') {
            showToast(message, type || 'info');
            return;
        }
        if (typeof showNotification === 'function') {
            showNotification(message, type || 'info');
            return;
        }
        alert(message);
    }

    function bindStatusFilters(containerId, tableId) {
        const container = document.getElementById(containerId);
        const table = document.getElementById(tableId);
        if (!container || !table) {
            return;
        }

        const buttons = container.querySelectorAll('.filter-btn');
        const rows = table.querySelectorAll('tbody tr[data-status]');

        buttons.forEach((button) => {
            button.addEventListener('click', () => {
                const selected = button.dataset.status;
                buttons.forEach((btn) => btn.classList.remove('active'));
                button.classList.add('active');

                rows.forEach((row) => {
                    const status = row.dataset.status;
                    const visible = selected === 'all' || status === selected;
                    row.style.display = visible ? '' : 'none';
                });
            });
        });
    }

    function bindSearch(inputId, tableId, fields) {
        const input = document.getElementById(inputId);
        const table = document.getElementById(tableId);
        if (!input || !table) {
            return;
        }

        const rows = table.querySelectorAll('tbody tr[data-status]');

        input.addEventListener('input', () => {
            const query = input.value.trim().toLowerCase();
            rows.forEach((row) => {
                const text = fields
                    .map((index) => (row.cells[index] ? row.cells[index].innerText : ''))
                    .join(' ')
                    .toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        });
    }

    function openDetailsModal(items) {
        const modal = document.getElementById('volunteerDetailsModal');
        const grid = document.getElementById('volunteerDetailsGrid');
        if (!modal || !grid) {
            return;
        }

        grid.innerHTML = items
            .map((item) => {
                const fullClass = item.full ? ' full' : '';
                return `<div class="detail-item${fullClass}"><label>${item.label}</label><p>${item.value || '-'}</p></div>`;
            })
            .join('');

        modal.classList.add('show');
        modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
    }

    function closeDetailsModal() {
        const modal = document.getElementById('volunteerDetailsModal');
        if (!modal) {
            return;
        }
        modal.classList.remove('show');
        modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
    }

    function bindDetailsModalClose() {
        document.querySelectorAll('[data-close-volunteer-modal]').forEach((node) => {
            node.addEventListener('click', closeDetailsModal);
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                closeDetailsModal();
            }
        });
    }

    function statusBadge(type, action) {
        if (action === 'approve') {
            return type === 'application'
                ? '<span class="status-badge status-approved">Approved</span>'
                : '<span class="status-badge status-approved">Contacted</span>';
        }

        return type === 'application'
            ? '<span class="status-badge status-rejected">Rejected</span>'
            : '<span class="status-badge status-rejected">Closed</span>';
    }

    async function postAction(url, extraData) {
        const csrfToken = getCsrfToken();
        if (!csrfToken) {
            throw new Error('CSRF token not found. Please refresh and try again.');
        }

        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', csrfToken);
        if (extraData && typeof extraData === 'object') {
            Object.keys(extraData).forEach((key) => {
                if (extraData[key] !== undefined && extraData[key] !== null) {
                    formData.append(key, extraData[key]);
                }
            });
        }

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData,
            credentials: 'same-origin'
        });

        if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`);
        }

        return response.json();
    }

    function updateRowAfterAction(row, type, action) {
        if (!row || action === 'delete') {
            if (row && action === 'delete') {
                row.remove();
            }
            return;
        }

        const statusCellIndex = type === 'application' ? 4 : 9;
        const statusCell = row.cells[statusCellIndex];
        const actionsCell = row.cells[row.cells.length - 1];

        if (statusCell) {
            statusCell.innerHTML = statusBadge(type, action);
        }

        if (row.dataset) {
            row.dataset.status = action === 'approve'
                ? (type === 'application' ? 'approved' : 'contacted')
                : (type === 'application' ? 'rejected' : 'closed');
        }

        if (actionsCell) {
            const id = actionsCell.querySelector('button[data-id]')?.dataset.id;
            if (!id) {
                return;
            }

            const scopeClass = type === 'application' ? 'action-application' : 'action-request';
            actionsCell.innerHTML = `
                <div class="action-buttons">
                    <button class="btn-icon btn-view ${scopeClass}" data-id="${id}" data-action="view" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn-icon btn-delete ${scopeClass}" data-id="${id}" data-action="delete" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
        }
    }

    function getDetailsPayload(type, row) {
        const data = row.dataset;
        if (type === 'application') {
            return [
                { label: 'Applicant', value: data.name },
                { label: 'Email', value: data.email },
                { label: 'Phone', value: data.phone },
                { label: 'Opportunity', value: data.opportunity },
                { label: 'Applied Date', value: data.applied },
                { label: 'Status', value: data.statusText },
                { label: 'Motivation', value: data.motivation, full: true },
                { label: 'Experience', value: data.experience, full: true },
                { label: 'Availability', value: data.availability, full: true }
            ];
        }

        return [
            { label: 'Name', value: data.name },
            { label: 'Email', value: data.email },
            { label: 'Phone', value: data.phone },
            { label: 'Address', value: data.address },
            { label: 'Type', value: data.type },
            { label: 'Expertise', value: data.expertise },
            { label: 'Schedule', value: data.schedule, full: true },
            { label: 'Purpose', value: data.purpose, full: true },
            { label: 'Submitted', value: data.submitted },
            { label: 'Status', value: data.statusText }
        ];
    }

    function actionVerb(action) {
        if (action === 'approve') return 'approve';
        if (action === 'reject') return 'reject';
        return 'delete';
    }

    function bindActionHandlers(scopeSelector, type) {
        document.querySelectorAll(scopeSelector).forEach((button) => {
            button.addEventListener('click', async () => {
                const action = button.dataset.action;
                const id = button.dataset.id;
                const row = button.closest('tr');

                if (!id || !action || !row) {
                    return;
                }

                if (action === 'view') {
                    openDetailsModal(getDetailsPayload(type, row));
                    return;
                }

                const noun = type === 'application' ? 'application' : 'request';
                const confirmed = await window.GlobalUI.confirm({
                    title: `${actionVerb(action).charAt(0).toUpperCase()}${actionVerb(action).slice(1)} ${noun}`,
                    message: `Are you sure you want to ${actionVerb(action)} this ${noun}?`,
                    okText: actionVerb(action).charAt(0).toUpperCase() + actionVerb(action).slice(1),
                    variant: action === 'reject' || action === 'delete' ? 'danger' : 'primary'
                });
                if (!confirmed) {
                    return;
                }

                const basePath = type === 'application'
                    ? '/dashboard/volunteers/applications/'
                    : '/dashboard/volunteers/requests/';

                button.disabled = true;

                try {
                    const response = await postAction(`${basePath}${id}/${action}/`);
                    updateRowAfterAction(row, type, action);
                    notify(response.message || 'Action completed successfully.', 'success');
                    bindActions();
                } catch (error) {
                    notify(error.message || 'Action failed.', 'error');
                } finally {
                    button.disabled = false;
                }
            });
        });
    }

    function bindRequestAssignmentDropdowns() {
        document.querySelectorAll('.request-opportunity-select').forEach((select) => {
            select.addEventListener('change', async () => {
                const opportunityId = select.value;
                const requestId = select.dataset.requestId;
                const row = select.closest('tr');

                if (!opportunityId || !requestId) {
                    return;
                }

                const optionLabel = select.options[select.selectedIndex] ? select.options[select.selectedIndex].text : 'selected program';
                const confirmed = await window.GlobalUI.confirm({
                    title: 'Assign volunteer request',
                    message: `Assign this volunteer request to "${optionLabel}"?`,
                    okText: 'Assign'
                });
                if (!confirmed) {
                    select.value = '';
                    return;
                }

                select.disabled = true;
                try {
                    const response = await postAction(`/dashboard/volunteers/requests/${requestId}/assign/`, {
                        opportunity_id: opportunityId
                    });
                    updateRowAfterAction(row, 'request', 'approve');
                    notify(response.message || 'Volunteer assigned successfully.', 'success');
                } catch (error) {
                    select.value = '';
                    notify(error.message || 'Assignment failed.', 'error');
                } finally {
                    select.disabled = false;
                }
            });
        });
    }

    function clearActionBindings() {
        document.querySelectorAll('.action-application, .action-request').forEach((button) => {
            const clone = button.cloneNode(true);
            button.parentNode.replaceChild(clone, button);
        });
    }

    function bindActions() {
        clearActionBindings();
        bindActionHandlers('.action-application', 'application');
        bindActionHandlers('.action-request', 'request');
    }

    document.addEventListener('DOMContentLoaded', () => {
        bindStatusFilters('application-status-filters', 'applications-table');
        bindStatusFilters('request-status-filters', 'requests-table');
        bindSearch('application-search', 'applications-table', [1, 2]);
        bindSearch('request-search', 'requests-table', [1, 2, 3]);
        bindRequestAssignmentDropdowns();
        bindDetailsModalClose();
        bindActions();
    });
})();
