(function () {
    function getConfig() {
        return document.getElementById('requestsPageConfig');
    }

    async function handleRequestAction(requestId, action, reason) {
        const config = getConfig();
        if (!config) {
            return;
        }

        const templateKey = action === 'approve' ? 'approveUrlTemplate' : 'rejectUrlTemplate';
        const url = DashboardPageTools.replaceIdToken(config.dataset[templateKey], requestId);
        const payload = reason ? { reason } : {};
        const result = await DashboardPageTools.postForm(url, payload);

        if (result.success) {
            DashboardPageTools.showToast(result.message || 'Request updated', 'success');
            window.setTimeout(() => window.location.reload(), 1200);
            return;
        }

        throw new Error(result.message || 'Unable to update request');
    }

    async function viewDetails(requestId) {
        const config = getConfig();
        if (!config) {
            return;
        }

        const url = DashboardPageTools.replaceIdToken(config.dataset.detailsUrlTemplate, requestId);
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        const data = await response.json();
        if (!data.success) {
            throw new Error('Unable to load request details');
        }

        document.getElementById('detailsBody').innerHTML = `
            <div class="request-details">
                <h4>${data.title}</h4>
                <p><strong>Requester:</strong> ${data.requester_name}</p>
                <p><strong>Email:</strong> ${data.requester_email}</p>
                <p><strong>Phone:</strong> ${data.requester_phone}</p>
                <p><strong>Date:</strong> ${data.date || 'TBD'}</p>
                <p><strong>Location:</strong> ${data.location}</p>
                <p><strong>Expected Attendees:</strong> ${data.target_attendees || 'N/A'}</p>
                <p><strong>Description:</strong></p>
                <p>${data.description}</p>
            </div>
        `;
        document.getElementById('detailsModal').classList.add('show');
    }

    function closeModal() {
        document.getElementById('detailsModal')?.classList.remove('show');
    }

    document.addEventListener('DOMContentLoaded', function () {
        const table = document.querySelector('.data-table');
        if (!table) {
            return;
        }

        table.addEventListener('click', async function (event) {
            const button = event.target.closest('[data-request-action]');
            if (!button) {
                return;
            }

            const requestId = button.dataset.requestId;
            const action = button.dataset.requestAction;

            try {
                if (action === 'view') {
                    await viewDetails(requestId);
                    return;
                }

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
            } catch (error) {
                DashboardPageTools.showToast(error.message || 'Request failed', 'error');
            }
        });

        document.getElementById('detailsModal')?.addEventListener('click', function (event) {
            if (event.target === this) {
                closeModal();
            }
        });

        document.querySelectorAll('[data-close-modal="detailsModal"]').forEach((element) => {
            element.addEventListener('click', closeModal);
        });
    });
})();
