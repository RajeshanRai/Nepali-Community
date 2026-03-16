/**
 * Programs & Events JavaScript
 * Handles event registration, filtering, and dynamic interactions
 */

(function () {
    'use strict';

    // CSRF Token utility
    function isValidCSRFToken(token) {
        return typeof token === 'string' && (token.length === 32 || token.length === 64);
    }

    function getCookie(name) {
        const cookies = document.cookie ? document.cookie.split(';') : [];

        for (let i = 0; i < cookies.length; i += 1) {
            const cookie = cookies[i].trim();

            if (cookie.startsWith(name + '=')) {
                return decodeURIComponent(cookie.slice(name.length + 1));
            }
        }

        return '';
    }

    function getCSRFToken() {
        const inputToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value?.trim() || '';
        const cookieToken = getCookie('csrftoken').trim();

        if (isValidCSRFToken(inputToken)) {
            return inputToken;
        }

        if (isValidCSRFToken(cookieToken)) {
            return cookieToken;
        }

        return '';
    }

    // Show loading state
    function showLoading(button) {
        const originalText = button.innerHTML;
        button.dataset.originalText = originalText;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    }

    // Hide loading state
    function hideLoading(button) {
        button.disabled = false;
        if (button.dataset.nextText) {
            button.innerHTML = button.dataset.nextText;
            delete button.dataset.nextText;
            return;
        }
        button.innerHTML = button.dataset.originalText || 'Submit';
    }

    // Show notification
    function showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            <span>${message}</span>
        `;
        notification.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            background: ${type === 'success' ? '#4caf50' : '#f44336'};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            animation: slideIn 0.3s ease;
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // Handle Event Registration
    function handleRegistration() {
        const registerButtons = document.querySelectorAll('.btn-register');
        const unregisterButtons = document.querySelectorAll('.btn-unregister');

        registerButtons.forEach(btn => {
            btn.addEventListener('click', async function (e) {
                e.preventDefault();
                const programId = this.dataset.programId;
                const csrfToken = getCSRFToken();

                if (!programId) return;
                if (!csrfToken) {
                    showNotification('Security token missing. Refresh the page and try again.', 'error');
                    return;
                }

                showLoading(this);

                try {
                    const response = await fetch(`/programs/${programId}/register/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken,
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });

                    const data = await response.json();

                    if (response.ok && data.success) {
                        showNotification('Successfully registered for the event!', 'success');
                        // Convert to unregister button
                        this.classList.remove('btn-register', 'btn-primary');
                        this.classList.add('btn-unregister', 'btn-secondary');
                        this.dataset.nextText = '<i class="fas fa-check"></i> Registered';

                        // Update attendance count
                        updateAttendanceCount(programId, 1);
                    } else {
                        showNotification(data.message || data.error || 'Failed to register. Please try again.', 'error');
                    }
                } catch (error) {
                    console.error('Registration error:', error);
                    showNotification('An error occurred. Please try again.', 'error');
                } finally {
                    hideLoading(this);
                }
            });
        });

        unregisterButtons.forEach(btn => {
            btn.addEventListener('click', async function (e) {
                e.preventDefault();
                const programId = this.dataset.programId;
                const csrfToken = getCSRFToken();

                if (!programId) return;
                if (!csrfToken) {
                    showNotification('Security token missing. Refresh the page and try again.', 'error');
                    return;
                }

                const confirmed = await window.GlobalUI.confirm({
                    title: 'Unregister from event',
                    message: 'Are you sure you want to unregister from this event?',
                    okText: 'Unregister',
                    variant: 'danger'
                });

                if (!confirmed) {
                    return;
                }

                showLoading(this);

                try {
                    const response = await fetch(`/programs/${programId}/unregister/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken,
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });

                    const data = await response.json();

                    if (response.ok && data.success) {
                        showNotification('Successfully unregistered from the event.', 'success');
                        // Convert to register button
                        this.classList.remove('btn-unregister', 'btn-secondary');
                        this.classList.add('btn-register', 'btn-primary');
                        this.dataset.nextText = '<i class="fas fa-calendar-plus"></i> Register';

                        // Update attendance count
                        updateAttendanceCount(programId, -1);
                    } else {
                        showNotification(data.error || 'Failed to unregister. Please try again.', 'error');
                    }
                } catch (error) {
                    console.error('Unregistration error:', error);
                    showNotification('An error occurred. Please try again.', 'error');
                } finally {
                    hideLoading(this);
                }
            });
        });
    }

    // Update attendance count display
    function updateAttendanceCount(programId, delta) {
        const eventCard = document.querySelector(`[data-program-id="${programId}"]`)?.closest('.event-card');
        if (eventCard) {
            const attendanceSpan = eventCard.querySelector('.meta span:has(.fa-users)');
            if (attendanceSpan) {
                const currentCount = parseInt(attendanceSpan.textContent.match(/\d+/)[0]);
                const newCount = Math.max(0, currentCount + delta);
                attendanceSpan.innerHTML = `<i class="fas fa-users"></i> ${newCount} attending`;
            }
        }
    }

    // Handle Event Request Form
    function handleEventRequestForm() {
        const form = document.getElementById('event-request-form');
        if (!form) return;

        form.addEventListener('submit', async function (e) {
            e.preventDefault();

            const formData = new FormData(form);
            const submitBtn = form.querySelector('.submit-btn');
            const csrfToken = getCSRFToken();

            if (!csrfToken) {
                showNotification('Security token missing. Refresh the page and try again.', 'error');
                return;
            }

            showLoading(submitBtn);

            try {
                const response = await fetch('/programs/request/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'  // ensure view returns JSON
                    }
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    showNotification('Event request submitted successfully! We\'ll review it soon.', 'success');
                    form.reset();
                } else {
                    showNotification(data.message || data.error || 'Failed to submit request. Please try again.', 'error');
                }
            } catch (error) {
                console.error('Form submission error:', error);
                showNotification('An error occurred. Please try again.', 'error');
            } finally {
                hideLoading(submitBtn);
            }
        });
    }

    // Skeleton Loader
    function showSkeletonLoaders(count = 3) {
        const eventList = document.querySelector('.event-list');
        if (!eventList) return;

        eventList.innerHTML = '';

        for (let i = 0; i < count; i++) {
            const skeleton = document.createElement('div');
            skeleton.className = 'skeleton-event-card';
            skeleton.innerHTML = `
                <div class="skeleton-date skeleton-loader"></div>
                <div class="skeleton-title skeleton-loader"></div>
                <div class="skeleton-text skeleton-loader"></div>
                <div class="skeleton-text skeleton-loader" style="width: 80%;"></div>
                <div class="skeleton-meta skeleton-loader"></div>
            `;
            eventList.appendChild(skeleton);
        }
    }

    // Search with debounce
    function setupSearch() {
        const searchInput = document.querySelector('.event-search input[name="q"]');
        if (!searchInput) return;

        let debounceTimeout;
        searchInput.addEventListener('input', function () {
            clearTimeout(debounceTimeout);
            debounceTimeout = setTimeout(() => {
                this.form.submit();
            }, 500);
        });
    }

    // Animate form groups on scroll
    function animateFormGroups() {
        const formGroups = document.querySelectorAll('.animated-group');

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.animation = 'fadeInUp 0.6s ease forwards';
                }
            });
        }, { threshold: 0.1 });

        formGroups.forEach(group => {
            group.style.opacity = '0';
            observer.observe(group);
        });
    }

    // Add CSS animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    `;
    document.head.appendChild(style);

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        handleRegistration();
        handleEventRequestForm();
        setupSearch();
        animateFormGroups();
    }

})();
