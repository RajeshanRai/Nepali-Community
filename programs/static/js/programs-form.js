// ===== Countdown and Event Request Form =====

document.addEventListener('DOMContentLoaded', function () {
    // Simple countdown for May 15, 2026
    (function () {
        const end = new Date('2026-05-15T00:00:00');
        const cnt = document.getElementById('countdown');
        if (!cnt) {
            return;
        }
        function update() {
            const now = new Date();
            const diff = end - now;
            if (diff <= 0) { cnt.textContent = 'Event started!'; return; }
            const days = Math.floor(diff / 86400000);
            const hrs = Math.floor(diff % 86400000 / 3600000);
            const mins = Math.floor(diff % 3600000 / 60000);
            cnt.textContent = days + ' days ' + hrs + ' hrs ' + mins + ' min';
        }
        update(); setInterval(update, 60000);
    })();

    // Handle request form submission
    const eventRequestForm = document.getElementById('event-request-form');
    if (eventRequestForm) {
        eventRequestForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const form = new FormData(eventRequestForm);
            form.set('event_type', document.getElementById('req-event-type')?.value || 'other');
            form.set('community', document.getElementById('req-community')?.value || '');
            form.set('requester_name', document.getElementById('req-name')?.value || '');
            form.set('requester_email', document.getElementById('req-email')?.value || '');
            form.set('requester_phone', document.getElementById('req-phone')?.value || '');

            fetch('/programs/request/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: form
            })
                .then(async r => {
                    const data = await r.json().catch(() => ({ success: false, message: 'Invalid server response' }));
                    return { ok: r.ok, data };
                })
                .then(data => {
                    const res = document.getElementById('request-result');
                    res.style.display = 'block';
                    res.textContent = data.data?.message || 'Submitted';
                    if (data.ok && data.data?.success) {
                        res.style.color = 'green';
                        eventRequestForm.reset();
                    } else {
                        res.style.color = 'red';
                    }
                })
                .catch(err => {
                    console.error(err);
                    const res = document.getElementById('request-result');
                    res.style.display = 'block';
                    res.style.color = 'red';
                    res.textContent = 'An error occurred while submitting the request.';
                });
        });
    }
});
