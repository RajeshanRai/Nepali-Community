(function () {
    'use strict';

    async function handleRequestAction(requestId, action, reason = '') {
        const config = document.getElementById('requestsPageConfig');
        let urlTemplate;

        if (action === 'approve') {
            urlTemplate = config.dataset.approveUrlTemplate;
        } else if (action === 'reject') {
            urlTemplate = config.dataset.rejectUrlTemplate;
        } else if (action === 'view') {
            const detailsUrlTemplate = config.dataset.detailsUrlTemplate;
            const url = detailsUrlTemplate.replace('__id__', requestId);
            try {
                const response = await fetch(url);
                if (!response.ok) throw new Error('Failed to fetch details');
                const data = await response.json();
                showDetailsModal(data);
            } catch (error) {
                DashboardPageTools.showToast(error.message || 'Failed to load request details', 'error');
            }
            return;
        } else {
            return;
        }

        const url = urlTemplate.replace('__id__', requestId);

        try {
            const fetchOptions = {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                }
            };

            if (action === 'reject' && reason) {
                fetchOptions.body = JSON.stringify({ reason });
            }

            const response = await fetch(url, fetchOptions);
            const data = await response.json();

            if (data.success) {
                DashboardPageTools.showToast(data.message || `Request ${action}ed successfully`, 'success');
                // Reload the page after a short delay
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                DashboardPageTools.showToast(data.message || `Failed to ${action} request`, 'error');
            }
        } catch (error) {
            DashboardPageTools.showToast(error.message || `Error ${action}ing request`, 'error');
        }
    }

    function getCsrfToken() {
        const name = 'csrftoken';
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

    function showDetailsModal(data) {
        const modal = document.getElementById('detailsModal');
        const detailsBody = document.getElementById('detailsBody');

        // Build HTML for details
        let html = '<div class="request-details">';
        html += `<p><strong>Title:</strong> ${data.title || 'N/A'}</p>`;
        html += `<p><strong>Description:</strong> ${data.description || 'N/A'}</p>`;
        html += `<p><strong>Requester:</strong> ${data.requester_name || 'N/A'}</p>`;
        html += `<p><strong>Email:</strong> ${data.requester_email || 'N/A'}</p>`;
        html += `<p><strong>Date:</strong> ${data.date || 'N/A'}</p>`;
        html += `<p><strong>Location:</strong> ${data.location || 'N/A'}</p>`;
        html += `<p><strong>Type:</strong> ${data.event_type || 'N/A'}</p>`;
        html += `<p><strong>Status:</strong> ${data.status || 'N/A'}</p>`;
        html += '</div>';

        detailsBody.innerHTML = html;
        modal.style.display = 'block';
    }

    function closeModal() {
        const modal = document.getElementById('detailsModal');
        modal.style.display = 'none';
    }

    document.addEventListener('DOMContentLoaded', function () {
        // Handle action buttons
        document.querySelectorAll('[data-request-action]').forEach((button) => {
            button.addEventListener('click', async function (e) {
                e.preventDefault();
                const action = this.dataset.requestAction;
                const requestId = this.dataset.requestId;

                try {
                    if (action === 'approve') {
                        const approved = await window.GlobalUI.confirm({
                            title: 'Approve request',
                            message: 'Are you sure you want to approve this request?',
                            okText: 'Approve'
                        });
                        if (approved) {
                            await handleRequestAction(requestId, 'approve');
                        }
                        return;
                    }

                    if (action === 'reject') {
                        const reason = await window.GlobalUI.prompt({
                            title: 'Reject request',
                            message: 'Enter rejection reason (optional):',
                            okText: 'Reject',
                            placeholder: 'Optional reason',
                            variant: 'danger'
                        });
                        if (reason !== null) {
                            await handleRequestAction(requestId, 'reject', reason);
                        }
                    }

                    if (action === 'view') {
                        await handleRequestAction(requestId, 'view');
                    }
                } catch (error) {
                    DashboardPageTools.showToast(error.message || 'Request failed', 'error');
                }
            });
        });

        // Handle modal close on background click
        document.getElementById('detailsModal')?.addEventListener('click', function (event) {
            if (event.target === this) {
                closeModal();
            }
        });

        // Handle modal close button
        document.querySelectorAll('[data-close-modal="detailsModal"]').forEach((element) => {
            element.addEventListener('click', closeModal);
        });
    });
})();
