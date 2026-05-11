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
        const normalizedType = type === 'error' ? 'error' : (type === 'warning' ? 'warning' : (type === 'success' ? 'success' : 'info'));
        const iconByType = {
            success: 'circle-check',
            error: 'triangle-exclamation',
            warning: 'circle-exclamation',
            info: 'circle-info'
        };

        const text = title && title !== 'Notification'
            ? `${title}: ${message}`
            : message;

        let flashWrap = document.querySelector('.site-flash-wrap.dynamic-home-flash');
        if (!flashWrap) {
            flashWrap = document.createElement('div');
            flashWrap.className = 'site-flash-wrap dynamic-home-flash';
            flashWrap.setAttribute('aria-live', 'polite');
            flashWrap.setAttribute('aria-label', 'Notifications');

            const contentRoot = document.querySelector('.home-v2');
            if (contentRoot && contentRoot.parentNode) {
                contentRoot.parentNode.insertBefore(flashWrap, contentRoot);
            } else {
                document.body.prepend(flashWrap);
            }
        }

        const flash = document.createElement('div');
        flash.className = `site-flash site-flash-${normalizedType}`;
        flash.setAttribute('role', 'alert');
        flash.innerHTML = `
            <i class="fas fa-${iconByType[normalizedType]}" aria-hidden="true"></i>
            <div>${text}</div>
        `;

        flashWrap.appendChild(flash);

        if (autoClose) {
            setTimeout(() => {
                flash.remove();
                if (!flashWrap.childElementCount) {
                    flashWrap.remove();
                }
            }, 3200);
        }
    }

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

    function initTestimonialMotion() {
        const strip = document.querySelector('.home-v2-testimonial-strip');
        if (!strip) {
            return;
        }

        const cards = Array.from(strip.querySelectorAll('.home-v2-testimonial-card'));
        if (!cards.length) {
            return;
        }

        cards.forEach((card, index) => {
            card.style.setProperty('--testimonial-delay', `${index * 0.1}s`);
        });

        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (reduceMotion) {
            return;
        }

        cards.forEach((card) => {
            card.addEventListener('mousemove', (event) => {
                const rect = card.getBoundingClientRect();
                const x = ((event.clientX - rect.left) / rect.width) * 100;
                const y = ((event.clientY - rect.top) / rect.height) * 100;

                card.style.setProperty('--spot-x', `${x}%`);
                card.style.setProperty('--spot-y', `${y}%`);
            });

            card.addEventListener('mouseleave', () => {
                card.style.removeProperty('--spot-x');
                card.style.removeProperty('--spot-y');
            });
        });

        let spotlightIndex = 0;
        const rotateSpotlight = () => {
            cards.forEach((card) => card.classList.remove('is-spotlight'));
            cards[spotlightIndex].classList.add('is-spotlight');
            spotlightIndex = (spotlightIndex + 1) % cards.length;
        };

        rotateSpotlight();
        window.setInterval(rotateSpotlight, 2400);
    }

    initTestimonialMotion();


})();
