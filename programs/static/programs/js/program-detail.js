(function () {
    'use strict';

    const page = document.querySelector('[data-program-detail]');

    if (!page) {
        return;
    }

    const toast = document.querySelector('[data-program-toast]');
    const attendanceNodes = document.querySelectorAll('[data-attendance-count]');
    const progressBar = document.querySelector('[data-detail-progress]');
    const revealNodes = document.querySelectorAll('[data-reveal]');
    const registrationForm = document.querySelector('[data-registration-form]');
    const registerButton = document.querySelector('[data-register-button]');
    const shareButton = document.querySelector('[data-share-program]');
    const calendarButton = document.querySelector('[data-download-ics]');

    const programId = page.dataset.programId;
    const programTitle = page.dataset.programTitle || 'Community Event';
    const programDate = page.dataset.programDate;
    const programLocation = page.dataset.programLocation || 'TBA';
    const programDescription = page.dataset.programDescription || 'Join us for this community program.';
    const programUrl = page.dataset.programUrl || window.location.href;
    const registerUrl = '/programs/' + programId + '/register/';
    const unregisterUrl = '/programs/' + programId + '/unregister/';

    let isRegisteredState = Boolean(registerButton && registerButton.classList.contains('is-registered'));

    function readCookie(name) {
        const cookies = document.cookie ? document.cookie.split(';') : [];

        for (let i = 0; i < cookies.length; i += 1) {
            const cookie = cookies[i].trim();

            if (cookie.startsWith(name + '=')) {
                return decodeURIComponent(cookie.slice(name.length + 1));
            }
        }

        return '';
    }

    function isValidCSRFToken(token) {
        if (!token) {
            return false;
        }

        // Django accepts 32-char cookie token or 64-char masked form token.
        return token.length === 32 || token.length === 64;
    }

    function getCSRFToken() {
        const formTokenField = registrationForm ? registrationForm.querySelector('[name=csrfmiddlewaretoken]') : null;
        const anyTokenField = document.querySelector('[name=csrfmiddlewaretoken]');
        const candidates = [
            formTokenField ? formTokenField.value.trim() : '',
            anyTokenField ? anyTokenField.value.trim() : '',
            readCookie('csrftoken').trim()
        ];

        for (let i = 0; i < candidates.length; i += 1) {
            if (isValidCSRFToken(candidates[i])) {
                return candidates[i];
            }
        }

        return '';
    }

    function showToast(message, type) {
        if (!toast) {
            return;
        }

        toast.textContent = message;
        toast.classList.toggle('is-error', type === 'error');
        toast.classList.add('is-visible');

        window.clearTimeout(showToast.timeoutId);
        showToast.timeoutId = window.setTimeout(function () {
            toast.classList.remove('is-visible');
        }, 3200);
    }

    function setLoadingState(isLoading) {
        if (!registerButton) {
            return;
        }

        registerButton.classList.toggle('is-loading', isLoading);
        registerButton.disabled = isLoading;

        if (isLoading) {
            registerButton.dataset.originalHtml = registerButton.innerHTML;
            registerButton.innerHTML = '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i><span>Processing...</span>';
            return;
        }

        if (registerButton.dataset.originalHtml) {
            registerButton.innerHTML = registerButton.dataset.originalHtml;
            delete registerButton.dataset.originalHtml;
        }
    }

    function setAttendanceCount(value) {
        attendanceNodes.forEach(function (node) {
            node.textContent = value;
        });
    }

    function adjustAttendance(delta) {
        const firstNode = attendanceNodes[0];
        const currentValue = firstNode ? Number.parseInt(firstNode.textContent, 10) || 0 : 0;
        setAttendanceCount(Math.max(0, currentValue + delta));
    }

    function syncAuthenticatedButton(isRegistered) {
        if (!registrationForm || registrationForm.dataset.authenticated !== 'true' || !registerButton) {
            return;
        }

        isRegisteredState = isRegistered;
        const icon = isRegistered ? 'fa-check-circle' : 'fa-ticket';
        const label = isRegistered ? "You're registered" : 'Register now';
        registerButton.classList.toggle('is-registered', isRegistered);
        registerButton.innerHTML = '<i class="fas ' + icon + '" aria-hidden="true"></i><span>' + label + '</span>';
        registerButton.dataset.originalHtml = registerButton.innerHTML;
        registrationForm.action = isRegistered ? unregisterUrl : registerUrl;
    }

    function parseRegistrationResponseMessage(data) {
        if (!data) {
            return '';
        }

        return String(data.message || data.error || '').toLowerCase();
    }

    async function submitRegistration(event) {
        event.preventDefault();

        if (!registrationForm || !programId) {
            return;
        }

        const isAuthenticated = registrationForm.dataset.authenticated === 'true';
        const action = isAuthenticated && isRegisteredState ? 'unregister' : 'register';
        const targetUrl = isAuthenticated ? (action === 'unregister' ? unregisterUrl : registerUrl) : registrationForm.action;
        const formData = new FormData(registrationForm);
        const csrfToken = getCSRFToken();

        setLoadingState(true);

        if (!isValidCSRFToken(csrfToken)) {
            showToast('Security token missing. Refresh the page and try again.', 'error');
            setLoadingState(false);
            return;
        }

        try {
            const response = await fetch(targetUrl, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            let data = null;

            try {
                data = await response.json();
            } catch (jsonError) {
                // Keep null and let error handling below produce a friendly message.
            }

            const message = parseRegistrationResponseMessage(data);
            const isAlreadyRegistered = message.includes('already registered');
            const isAlreadyUnregistered = message.includes('not registered') || message.includes('not register');

            if (isAuthenticated) {
                if (action === 'register') {
                    if (response.ok && data && data.success) {
                        syncAuthenticatedButton(true);
                        adjustAttendance(1);
                        showToast(data.message || 'Registration completed.', 'success');
                    } else if (response.ok && isAlreadyRegistered) {
                        // Server confirms user is registered; sync button without forcing reload.
                        syncAuthenticatedButton(true);
                        showToast(data.message || 'You are already registered.', 'success');
                    } else {
                        throw new Error((data && (data.message || data.error)) || 'Unable to register right now.');
                    }
                } else {
                    if (response.ok && data && data.success) {
                        syncAuthenticatedButton(false);
                        adjustAttendance(-1);
                        showToast(data.message || 'Registration removed.', 'success');
                    } else if (response.ok && isAlreadyUnregistered) {
                        // Server confirms user is not registered; sync button without forcing reload.
                        syncAuthenticatedButton(false);
                        showToast(data.message || 'You are already unregistered.', 'success');
                    } else {
                        throw new Error((data && (data.message || data.error)) || 'Unable to unregister right now.');
                    }
                }
            } else {
                if (!response.ok || !data || !data.success) {
                    throw new Error((data && (data.message || data.error)) || 'Unable to complete registration.');
                }
                registrationForm.reset();
                adjustAttendance(1);
                showToast(data.message || 'Guest registration completed.', 'success');
            }
        } catch (error) {
            showToast(error.message || 'Something went wrong. Please try again.', 'error');
        } finally {
            setLoadingState(false);
        }
    }

    async function shareProgram() {
        const payload = {
            title: programTitle,
            text: programDescription,
            url: programUrl
        };

        try {
            if (navigator.share) {
                await navigator.share(payload);
                showToast('Event link shared.', 'success');
                return;
            }

            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(programUrl);
                showToast('Event link copied to clipboard.', 'success');
                return;
            }
        } catch (error) {
            showToast('Share was cancelled.', 'error');
            return;
        }

        showToast('Sharing is not supported on this device.', 'error');
    }

    function toIcsDate(dateString) {
        return String(dateString || '').replace(/-/g, '');
    }

    function nextDate(dateString) {
        const parts = String(dateString || '').split('-').map(Number);

        if (parts.length !== 3 || parts.some(Number.isNaN)) {
            return dateString;
        }

        const date = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
        date.setUTCDate(date.getUTCDate() + 1);

        return [
            date.getUTCFullYear(),
            String(date.getUTCMonth() + 1).padStart(2, '0'),
            String(date.getUTCDate()).padStart(2, '0')
        ].join('-');
    }

    function escapeIcs(value) {
        return String(value || '')
            .replace(/\\/g, '\\\\')
            .replace(/,/g, '\\,')
            .replace(/;/g, '\\;')
            .replace(/\n/g, '\\n');
    }

    function downloadCalendarInvite() {
        if (!programDate) {
            showToast('Calendar export is unavailable because the event date is missing.', 'error');
            return;
        }

        const start = toIcsDate(programDate);
        const end = toIcsDate(nextDate(programDate));
        const content = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//Nepali Community of Vancouver//Programs//EN',
            'BEGIN:VEVENT',
            'UID:' + programId + '@ncv-programs',
            'DTSTAMP:' + start + 'T000000Z',
            'DTSTART;VALUE=DATE:' + start,
            'DTEND;VALUE=DATE:' + end,
            'SUMMARY:' + escapeIcs(programTitle),
            'DESCRIPTION:' + escapeIcs(programDescription),
            'LOCATION:' + escapeIcs(programLocation),
            'URL:' + escapeIcs(programUrl),
            'END:VEVENT',
            'END:VCALENDAR'
        ].join('\r\n');

        const blob = new Blob([content], { type: 'text/calendar;charset=utf-8' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');

        link.href = url;
        link.download = programTitle.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') + '.ics';
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
        showToast('Calendar file downloaded.', 'success');
    }

    function updateProgress() {
        if (!progressBar) {
            return;
        }

        const scrollTop = window.scrollY;
        const documentHeight = document.documentElement.scrollHeight - window.innerHeight;
        const progress = documentHeight > 0 ? (scrollTop / documentHeight) * 100 : 0;
        progressBar.style.width = Math.min(100, Math.max(0, progress)) + '%';
    }

    function setupRevealAnimations() {
        if (!revealNodes.length) {
            return;
        }

        const observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.14,
            rootMargin: '0px 0px -30px 0px'
        });

        revealNodes.forEach(function (node, index) {
            node.style.transitionDelay = Math.min(index * 60, 360) + 'ms';
            observer.observe(node);
        });
    }

    if (registrationForm) {
        registrationForm.addEventListener('submit', submitRegistration);
    }

    if (shareButton) {
        shareButton.addEventListener('click', shareProgram);
    }

    if (calendarButton) {
        calendarButton.addEventListener('click', downloadCalendarInvite);
    }

    window.addEventListener('scroll', updateProgress, { passive: true });
    updateProgress();
    setupRevealAnimations();
})();