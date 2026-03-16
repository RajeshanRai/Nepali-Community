

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
