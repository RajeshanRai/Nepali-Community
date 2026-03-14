// ===== Custom Notification System =====

function showNotification(message, type = 'info', title = 'Notification', autoClose = true) {
    const overlay = document.getElementById('notification-overlay');
    const modal = document.getElementById('notification-modal');
    const titleEl = document.getElementById('notification-title');
    const messageEl = document.getElementById('notification-message');
    const iconEl = document.getElementById('notification-icon-content');

    // Reset classes
    modal.className = 'notification-modal';
    modal.classList.add(type);

    // Set content
    titleEl.textContent = title;
    messageEl.textContent = message;

    // Set icon based on type
    if (type === 'success') {
        iconEl.textContent = '✓';
        if (!title || title === 'Notification') titleEl.textContent = 'Success';
    } else if (type === 'error') {
        iconEl.textContent = '✕';
        if (!title || title === 'Notification') titleEl.textContent = 'Error';
    } else {
        iconEl.textContent = 'ℹ️';
    }

    // Show modal
    overlay.classList.add('show');
    modal.classList.remove('closing');

    // Auto-close after 3 seconds
    if (autoClose) {
        setTimeout(() => {
            closeNotification();
        }, 3000);
    }
}

function closeNotification() {
    const overlay = document.getElementById('notification-overlay');
    const modal = document.getElementById('notification-modal');

    modal.classList.add('closing');
    overlay.classList.add('closing');

    setTimeout(() => {
        overlay.classList.remove('show', 'closing');
        modal.classList.remove('closing');
    }, 300);
}

// ===== Registration & Unregistration Logic (AJAX, no modal) =====

document.addEventListener('DOMContentLoaded', function () {
    const registerButtons = document.querySelectorAll('.btn-register');
    const unregisterButtons = document.querySelectorAll('.btn-unregister');
    const IS_AUTH = document.documentElement.getAttribute('data-user-authenticated') === 'true';

    function attachRegisterHandler(btn) {
        btn.addEventListener('click', function () {
            const programId = this.getAttribute('data-program-id');
            if (!IS_AUTH) {
                // redirect guests to login with next
                const next = encodeURIComponent(window.location.pathname + window.location.search);
                window.location.href = '/users/login/?next=' + next;
                return;
            }
            const self = this;
            fetch(`/programs/${programId}/register/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showNotification(data.message, 'success', 'Registration Successful');
                        self.textContent = 'Unregister';
                        self.classList.remove('btn-primary');
                        self.classList.add('btn-secondary');
                        self.classList.remove('btn-register');
                        self.classList.add('btn-unregister');

                        // Increment count
                        const card = self.closest('.event-card');
                        if (card) {
                            const countSpan = card.querySelector('.meta span:last-child');
                            if (countSpan) {
                                const parts = countSpan.textContent.trim().split(' ');
                                let num = parseInt(parts[0]) || 0;
                                countSpan.textContent = (num + 1) + ' attending';
                            }
                        }

                        // attach unregister handler
                        attachUnregisterHandler(self);
                    } else {
                        showNotification(data.message, 'error', 'Registration Failed');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification('An error occurred during registration.', 'error', 'Error');
                });
        });
    }

    function attachUnregisterHandler(btn) {
        btn.addEventListener('click', function () {
            const programId = this.getAttribute('data-program-id');
            const self = this;
            fetch(`/programs/${programId}/unregister/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showNotification(data.message, 'success', 'Unregistered');
                        self.textContent = 'Register';
                        self.classList.remove('btn-secondary');
                        self.classList.add('btn-primary');
                        self.classList.remove('btn-unregister');
                        self.classList.add('btn-register');

                        // Decrement count
                        const card = self.closest('.event-card');
                        if (card) {
                            const countSpan = card.querySelector('.meta span:last-child');
                            if (countSpan) {
                                const parts = countSpan.textContent.trim().split(' ');
                                let num = parseInt(parts[0]) || 0;
                                countSpan.textContent = Math.max(0, num - 1) + ' attending';
                            }
                        }

                        // attach register handler
                        attachRegisterHandler(self);
                    } else {
                        showNotification(data.message, 'error', 'Error');
                    }
                })
                .catch(err => {
                    console.error(err);
                    showNotification('Unregister request failed', 'error', 'Error');
                });
        });
    }

    registerButtons.forEach(btn => attachRegisterHandler(btn));
    unregisterButtons.forEach(btn => attachUnregisterHandler(btn));
});
