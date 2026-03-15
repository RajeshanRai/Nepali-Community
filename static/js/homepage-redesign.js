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
    const csrfToken = getCookie('csrftoken') || '';

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

    function bindRegister(btn) {
        btn.addEventListener('click', function () {
            const programId = this.getAttribute('data-program-id');

            if (!isAuthenticated) {
                const next = encodeURIComponent(window.location.pathname + window.location.search);
                window.location.href = `${loginUrl}?next=${next}`;
                return;
            }

            fetch(`/programs/${programId}/register/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then((response) => response.json())
                .then((data) => {
                    if (!data.success) {
                        showNotification(data.message || 'Registration failed', 'error', 'Registration Failed');
                        return;
                    }

                    showNotification(data.message || 'Registered successfully', 'success', 'Registration Successful');

                    this.textContent = 'Unregister';
                    this.classList.remove('btn-primary', 'btn-register');
                    this.classList.add('btn-secondary', 'btn-unregister');

                    const card = this.closest('.home-v2-program-card');
                    if (card) {
                        updateAttendance(card, 1);
                    }

                    bindUnregister(this);
                })
                .catch(() => {
                    showNotification('An error occurred during registration.', 'error', 'Error');
                });
        }, { once: true });
    }

    function bindUnregister(btn) {
        btn.addEventListener('click', function () {
            const programId = this.getAttribute('data-program-id');

            fetch(`/programs/${programId}/unregister/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then((response) => response.json())
                .then((data) => {
                    if (!data.success) {
                        showNotification(data.message || 'Unregister failed', 'error', 'Error');
                        return;
                    }

                    showNotification(data.message || 'Unregistered', 'success', 'Unregistered');

                    this.textContent = 'Register';
                    this.classList.remove('btn-secondary', 'btn-unregister');
                    this.classList.add('btn-primary', 'btn-register');

                    const card = this.closest('.home-v2-program-card');
                    if (card) {
                        updateAttendance(card, -1);
                    }

                    bindRegister(this);
                })
                .catch(() => {
                    showNotification('Unregister request failed', 'error', 'Error');
                });
        }, { once: true });
    }

    document.querySelectorAll('.btn-register').forEach((btn) => bindRegister(btn));
    document.querySelectorAll('.btn-unregister').forEach((btn) => bindUnregister(btn));

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
