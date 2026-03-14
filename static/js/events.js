// ===== EVENT REQUEST FORM AND CALENDAR FUNCTIONALITY =====

// Initialize calendar on page load
document.addEventListener('DOMContentLoaded', function () {
    initializeCalendar();
    setupFormEnhancements();
    setupFormSubmission();
    setupNepaliObservanceFilters();
});

// ===== CALENDAR FUNCTIONALITY =====
function initializeCalendar() {
    let currentDate = new Date();

    const dayPanel = document.getElementById('calendar-day-panel');
    const selectedDateLabel = document.getElementById('selected-date-label');
    const selectedDateCount = document.getElementById('selected-date-count');
    const dayEventsList = document.getElementById('day-events-list');
    const dayEventsEmpty = document.getElementById('day-events-empty');
    const nepaliMonthFilter = document.getElementById('nepali-month-filter');

    function syncNepaliMonthFilter(monthName) {
        if (!nepaliMonthFilter) {
            return;
        }

        const hasMatchingMonth = Array.from(nepaliMonthFilter.options).some((option) => option.value === monthName);
        const nextValue = hasMatchingMonth ? monthName : 'all';

        if (nepaliMonthFilter.value !== nextValue) {
            nepaliMonthFilter.value = nextValue;
            nepaliMonthFilter.dispatchEvent(new Event('change'));
        }
    }

    function formatReadableDate(year, month, day) {
        const dateObj = new Date(year, month, day);
        return dateObj.toLocaleDateString('en-US', {
            weekday: 'long',
            month: 'long',
            day: 'numeric',
            year: 'numeric'
        });
    }

    function showDayEvents(dateStr, year, month, day) {
        if (!dayPanel || !selectedDateLabel || !selectedDateCount || !dayEventsList || !dayEventsEmpty) {
            return;
        }

        const allPrograms = window.allPrograms || {};
        const dayData = allPrograms[dateStr] || { count: 0, events: [] };

        selectedDateLabel.textContent = formatReadableDate(year, month, day);
        selectedDateCount.textContent = dayData.count > 0
            ? `${dayData.count} event${dayData.count > 1 ? 's' : ''} scheduled`
            : 'No events scheduled';

        dayEventsList.innerHTML = '';

        if (dayData.count > 0 && Array.isArray(dayData.events)) {
            dayEventsEmpty.style.display = 'none';

            dayData.events.forEach((eventItem) => {
                const eventType = eventItem.type ? String(eventItem.type).replace(/_/g, ' ') : 'Event';
                const eventRow = document.createElement('a');
                eventRow.className = 'day-event-item';
                eventRow.href = `/programs/${eventItem.id}/`;
                eventRow.innerHTML = `
                    <div class="day-event-main">
                        <strong>${eventItem.title || 'Untitled Event'}</strong>
                        <span>${eventType}</span>
                    </div>
                    <i class="fas fa-arrow-right"></i>
                `;
                dayEventsList.appendChild(eventRow);
            });
        } else {
            dayEventsEmpty.style.display = 'flex';
        }
    }

    function renderCalendar() {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        const currentMonthName = currentDate.toLocaleDateString('en-US', { month: 'long' });

        // Update header
        const monthYearEl = document.getElementById('month-year');
        if (monthYearEl) {
            monthYearEl.textContent =
                currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
        }

        syncNepaliMonthFilter(currentMonthName);

        // Clear previous days
        const grid = document.getElementById('calendar-grid');
        if (!grid) return;

        grid.innerHTML = '';

        // Get calendar structure
        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const daysInPrevMonth = new Date(year, month, 0).getDate();

        // Previous month days
        for (let i = firstDay - 1; i >= 0; i--) {
            const day = document.createElement('div');
            day.className = 'calendar-day other-month';
            day.textContent = daysInPrevMonth - i;
            grid.appendChild(day);
        }

        // Current month days
        const today = new Date();
        const allPrograms = window.allPrograms || {};

        for (let day = 1; day <= daysInMonth; day++) {
            const dayEl = document.createElement('div');
            dayEl.className = 'calendar-day';
            dayEl.textContent = day;

            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

            // Check if today
            if (day === today.getDate() && month === today.getMonth() && year === today.getFullYear()) {
                dayEl.classList.add('today');
            }

            // Check if has events
            if (allPrograms[dateStr] && allPrograms[dateStr].count > 0) {
                dayEl.classList.add('has-event');
                const eventList = allPrograms[dateStr].events || [];
                if (eventList.length > 0) {
                    const titles = eventList.map(e => e.title).join('\n');
                    dayEl.title = titles;
                }
            }

            dayEl.style.cursor = 'pointer';
            dayEl.addEventListener('click', () => {
                grid.querySelectorAll('.calendar-day.selected').forEach((cell) => {
                    cell.classList.remove('selected');
                });
                dayEl.classList.add('selected');
                showDayEvents(dateStr, year, month, day);
            });

            grid.appendChild(dayEl);
        }

        // Next month days
        const totalCells = grid.children.length;
        const remainingCells = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
        for (let day = 1; day <= remainingCells; day++) {
            const dayEl = document.createElement('div');
            dayEl.className = 'calendar-day other-month';
            dayEl.textContent = day;
            grid.appendChild(dayEl);
        }
    }

    // Navigation buttons
    const prevBtn = document.getElementById('prev-month');
    const nextBtn = document.getElementById('next-month');

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            currentDate.setMonth(currentDate.getMonth() - 1);
            renderCalendar();
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            currentDate.setMonth(currentDate.getMonth() + 1);
            renderCalendar();
        });
    }

    renderCalendar();
}

// ===== FORM ENHANCEMENTS =====
function setupFormEnhancements() {
    // Character counter for description
    const descEl = document.getElementById('req-description');
    if (descEl) {
        descEl.addEventListener('input', function () {
            const counter = document.getElementById('char-count');
            if (counter) {
                counter.textContent = this.value.length;
            }
        });
    }
}

// ===== FORM SUBMISSION WITH DYNAMIC UPDATES =====
function setupFormSubmission() {
    const form = document.getElementById('event-request-form');
    if (!form) return;

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        const submitBtn = document.getElementById('submit-request');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';

        const formData = new FormData(form);

        fetch('/programs/request/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                    getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                const resultEl = document.getElementById('request-result');
                if (resultEl) {
                    resultEl.style.display = 'block';
                    resultEl.classList.remove('error');

                    if (data.success) {
                        resultEl.classList.add('success-message');
                        resultEl.innerHTML = `
                        <i class="fas fa-check-circle"></i>
                        <strong>Success!</strong> Your event request has been submitted. 
                        The admin will review it and get back to you soon.
                    `;
                        form.reset();
                        document.getElementById('char-count').textContent = '0';

                        // Auto hide after 5 seconds
                        setTimeout(() => {
                            resultEl.style.display = 'none';
                        }, 5000);
                    } else {
                        resultEl.classList.add('error');
                        resultEl.textContent = data.message || 'Error submitting request. Please try again.';
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                const resultEl = document.getElementById('request-result');
                if (resultEl) {
                    resultEl.style.display = 'block';
                    resultEl.classList.add('error');
                    resultEl.textContent = 'An error occurred. Please try again.';
                }
            })
            .finally(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            });
    });
}

function setupNepaliObservanceFilters() {
    const monthFilter = document.getElementById('nepali-month-filter');
    const categoryButtons = document.querySelectorAll('.nepali-filter-btn');
    const observanceCards = document.querySelectorAll('.nepali-event-card');
    const emptyState = document.getElementById('nepali-events-empty');
    const countBadge = document.getElementById('nepali-dates-count');

    if (!observanceCards.length || !categoryButtons.length) {
        return;
    }

    let activeCategory = 'all';

    function cardMatchesMonth(card, selectedMonth) {
        if (selectedMonth === 'all') {
            return true;
        }

        const monthsRaw = card.dataset.months || '';
        if (!monthsRaw) {
            return false;
        }

        const months = monthsRaw.split(',').map((item) => item.trim()).filter(Boolean);
        return months.includes(selectedMonth);
    }

    function applyFilters() {
        const selectedMonth = monthFilter ? monthFilter.value : 'all';
        let visibleCount = 0;

        observanceCards.forEach((card) => {
            const cardCategory = card.dataset.category || '';
            const matchCategory = activeCategory === 'all' || cardCategory === activeCategory;
            const matchMonth = cardMatchesMonth(card, selectedMonth);
            const isVisible = matchCategory && matchMonth;

            card.style.display = isVisible ? '' : 'none';
            if (isVisible) {
                visibleCount += 1;
            }
        });

        if (emptyState) {
            emptyState.style.display = visibleCount > 0 ? 'none' : 'flex';
        }

        if (countBadge) {
            countBadge.textContent = `${visibleCount} item${visibleCount !== 1 ? 's' : ''}`;
        }
    }

    function resetCategoryToAll() {
        activeCategory = 'all';
        categoryButtons.forEach((btn) => {
            const isAllButton = (btn.dataset.category || 'all') === 'all';
            btn.classList.toggle('active', isAllButton);
        });
    }

    if (monthFilter) {
        monthFilter.addEventListener('change', () => {
            resetCategoryToAll();
            applyFilters();
        });
    }

    categoryButtons.forEach((button) => {
        button.addEventListener('click', () => {
            categoryButtons.forEach((btn) => btn.classList.remove('active'));
            button.classList.add('active');
            activeCategory = button.dataset.category || 'all';
            applyFilters();
        });
    });

    applyFilters();
}

// Utility function to get CSRF token
function getCookie(name) {
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
