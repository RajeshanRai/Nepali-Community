(function () {
    function easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    function animateCountValue(el) {
        if (!el || el.dataset.countupDone === 'true') {
            return;
        }

        const rawText = (el.textContent || '').trim();
        const match = rawText.match(/^(\D*)([\d,]+)(\D*)$/);
        if (!match) {
            el.dataset.countupDone = 'true';
            return;
        }

        const prefix = match[1] || '';
        const numberText = match[2] || '0';
        const suffix = match[3] || '';
        const target = parseInt(numberText.replace(/,/g, ''), 10);

        if (!Number.isFinite(target)) {
            el.dataset.countupDone = 'true';
            return;
        }

        const duration = 950;
        const startTime = performance.now();
        const startValue = 0;

        el.dataset.countupDone = 'true';

        function tick(now) {
            const elapsed = now - startTime;
            const progress = Math.min(1, elapsed / duration);
            const eased = easeOutCubic(progress);
            const current = Math.round(startValue + (target - startValue) * eased);
            el.textContent = `${prefix}${current.toLocaleString()}${suffix}`;

            if (progress < 1) {
                requestAnimationFrame(tick);
            }
        }

        requestAnimationFrame(tick);
    }

    function animateMetricCounters(container) {
        if (!container) {
            return;
        }

        container.querySelectorAll('[data-countup]').forEach((counterEl) => {
            animateCountValue(counterEl);
        });
    }

    function getCookie(name) {
        const cookies = document.cookie ? document.cookie.split('; ') : [];
        for (const cookie of cookies) {
            const parts = cookie.split('=');
            const key = decodeURIComponent(parts[0]);
            if (key === name) {
                return decodeURIComponent(parts.slice(1).join('='));
            }
        }
        return null;
    }

    function showNotification(message, type = 'info', title = 'Notification', autoClose = true) {
        const overlay = document.getElementById('notification-overlay');
        const modal = document.getElementById('notification-modal');
        const titleEl = document.getElementById('notification-title');
        const messageEl = document.getElementById('notification-message');
        const iconEl = document.getElementById('notification-icon-content');

        if (!overlay || !modal || !titleEl || !messageEl || !iconEl) {
            return;
        }

        modal.className = 'notification-modal';
        modal.classList.add(type);

        titleEl.textContent = title;
        messageEl.textContent = message;

        if (type === 'success') {
            iconEl.textContent = '✓';
            if (!title || title === 'Notification') {
                titleEl.textContent = 'Success';
            }
        } else if (type === 'error') {
            iconEl.textContent = '✕';
            if (!title || title === 'Notification') {
                titleEl.textContent = 'Error';
            }
        } else {
            iconEl.textContent = 'ℹ️';
        }

        overlay.classList.add('show');
        modal.classList.remove('closing');

        if (autoClose) {
            setTimeout(closeNotification, 3000);
        }
    }

    function closeNotification() {
        const overlay = document.getElementById('notification-overlay');
        const modal = document.getElementById('notification-modal');

        if (!overlay || !modal) {
            return;
        }

        modal.classList.add('closing');
        overlay.classList.add('closing');

        setTimeout(() => {
            overlay.classList.remove('show', 'closing');
            modal.classList.remove('closing');
        }, 300);
    }

    window.closeNotification = closeNotification;

    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                if (entry.target.classList.contains('home-v2-metric-card')) {
                    animateMetricCounters(entry.target);
                }
            }
        });
    }, { threshold: 0.15 });

    document.querySelectorAll('.reveal-up').forEach((item) => revealObserver.observe(item));

    // Hero Background Slideshow
    (function () {
        const slides = document.querySelectorAll('.hero-slide');
        if (slides.length < 2) return;
        let current = 0;
        setInterval(function () {
            slides[current].classList.remove('active');
            current = (current + 1) % slides.length;
            slides[current].classList.add('active');
        }, 5500);
    })();

    const isAuthenticated = document.documentElement.dataset.userAuthenticated === 'true';
    const loginUrl = '/users/login/';

    function isValidCsrfToken(token) {
        return typeof token === 'string' && (token.length === 32 || token.length === 64);
    }

    function resolveCsrfToken() {
        const formToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value?.trim() || '';
        const cookieToken = (getCookie('csrftoken') || '').trim();

        if (isValidCsrfToken(formToken)) {
            return formToken;
        }

        if (isValidCsrfToken(cookieToken)) {
            return cookieToken;
        }

        return '';
    }

    function updateAttendance(card, delta) {
        const countSpan = card.querySelector('.home-v2-meta span:last-child');
        if (!countSpan) {
            return;
        }

        const currentText = countSpan.textContent || '';
        const matched = currentText.match(/(\d+)/);
        const currentCount = matched ? parseInt(matched[1], 10) : 0;
        const nextCount = Math.max(0, currentCount + delta);
        countSpan.innerHTML = `<i class="fas fa-user-check"></i> ${nextCount} attending`;
    }

    function attachRegisterHandler(btn) {
        btn.addEventListener('click', async function () {
            const programId = this.getAttribute('data-program-id');
            if (!isAuthenticated) {
                const next = encodeURIComponent(window.location.pathname + window.location.search);
                window.location.href = `${loginUrl}?next=${next}`;
                return;
            }
            const confirmed = await window.GlobalUI.confirm({
                title: 'Register for Event',
                message: 'Do you want to register for this event?',
                okText: 'Register',
                variant: 'primary'
            });
            if (!confirmed) return;
            const csrfToken = resolveCsrfToken();
            if (!csrfToken) {
                showNotification('Security token missing. Refresh the page and try again.', 'error', 'Security Check Failed');
                return;
            }
            const self = this;
            fetch(`/programs/${programId}/register/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showNotification(data.message || 'Registered successfully', 'success', 'Registration Successful');
                        self.textContent = 'Unregister';
                        self.classList.remove('btn-primary');
                        self.classList.add('btn-secondary');
                        self.classList.remove('btn-register');
                        self.classList.add('btn-unregister');
                        const card = self.closest('.home-v2-program-card');
                        if (card) {
                            updateAttendance(card, 1);
                        }
                        attachUnregisterHandler(self);
                    } else {
                        showNotification(data.message || 'Registration failed', 'error', 'Registration Failed');
                    }
                })
                .catch(() => {
                    showNotification('An error occurred during registration.', 'error', 'Error');
                });
        });
    }

    function attachUnregisterHandler(btn) {
        btn.addEventListener('click', async function () {
            const programId = this.getAttribute('data-program-id');
            const confirmed = await window.GlobalUI.confirm({
                title: 'Unregister from Event',
                message: 'Do you want to unregister from this event?',
                okText: 'Unregister',
                variant: 'danger'
            });
            if (!confirmed) return;
            const csrfToken = resolveCsrfToken();
            if (!csrfToken) {
                showNotification('Security token missing. Refresh the page and try again.', 'error', 'Security Check Failed');
                return;
            }
            const self = this;
            fetch(`/programs/${programId}/unregister/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showNotification(data.message || 'Unregistered', 'success', 'Unregistered');
                        self.textContent = 'Register';
                        self.classList.remove('btn-secondary');
                        self.classList.add('btn-primary');
                        self.classList.remove('btn-unregister');
                        self.classList.add('btn-register');
                        const card = self.closest('.home-v2-program-card');
                        if (card) {
                            updateAttendance(card, -1);
                        }
                        attachRegisterHandler(self);
                    } else {
                        showNotification(data.message || 'Unregister failed', 'error', 'Error');
                    }
                })
                .catch(() => {
                    showNotification('Unregister request failed', 'error', 'Error');
                });
        });
    }

    document.querySelectorAll('.btn-register').forEach(btn => attachRegisterHandler(btn));
    document.querySelectorAll('.btn-unregister').forEach(btn => attachUnregisterHandler(btn));

    const warningTrigger = document.getElementById('homeWarningTrigger');
    if (warningTrigger) {
        const warningMessage = warningTrigger.dataset.warningMessage || 'Please review your account warning.';
        const warningTime = warningTrigger.dataset.warningTime || '';

        warningTrigger.addEventListener('click', function () {
            const fullMessage = warningTime
                ? `${warningMessage} (Issued: ${warningTime})`
                : warningMessage;
            showNotification(fullMessage, 'error', 'Account Warning', false);
        });

        // Auto-highlight the warning once when homepage loads.
        setTimeout(() => {
            const fullMessage = warningTime
                ? `${warningMessage} (Issued: ${warningTime})`
                : warningMessage;
            showNotification(fullMessage, 'error', 'Account Warning', true);
        }, 600);
    }
})();
