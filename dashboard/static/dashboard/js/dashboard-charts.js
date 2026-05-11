(function () {
    const payloadNode = document.getElementById('dashboard-chart-data');
    if (!payloadNode || typeof Chart === 'undefined') {
        return;
    }

    const localTimeNode = document.getElementById('dashboard-local-time');
    if (localTimeNode) {
        localTimeNode.textContent = new Date().toLocaleString();
    }

    const chartData = JSON.parse(payloadNode.textContent);
    const isDark = document.documentElement.dataset.theme === 'dark';

    const colors = {
        primary: '#8B1E3F',
        secondary: '#FF6B6B',
        accent: '#4ECDC4',
        warning: '#FFD93D',
        info: '#6C5CE7',
        grid: isDark ? 'rgba(255,255,255,0.12)' : '#f0f0f0',
        text: isDark ? '#e5e7eb' : '#666'
    };

    const baseConfig = {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                labels: {
                    font: { family: "'Poppins', sans-serif", size: 12 },
                    color: colors.text,
                    usePointStyle: true,
                    padding: 20
                }
            }
        }
    };

    function makeTickStyle() {
        return {
            font: { family: "'Poppins', sans-serif" },
            color: colors.text
        };
    }

    const regByEventCtx = document.getElementById('registrationsByEventChart');
    if (regByEventCtx) {
        new Chart(regByEventCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: chartData.registrationsByEvent.labels,
                datasets: [{
                    label: 'Registrations',
                    data: chartData.registrationsByEvent.data,
                    backgroundColor: colors.primary,
                    borderColor: colors.primary,
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                ...baseConfig,
                indexAxis: 'y',
                scales: {
                    x: { beginAtZero: true, grid: { color: colors.grid }, ticks: makeTickStyle() },
                    y: { grid: { display: false }, ticks: makeTickStyle() }
                }
            }
        });
    }

    const eventTypesCtx = document.getElementById('eventTypesChart');
    if (eventTypesCtx) {
        new Chart(eventTypesCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: chartData.eventTypes.labels,
                datasets: [{
                    data: chartData.eventTypes.data,
                    backgroundColor: [colors.primary, colors.secondary, colors.accent, colors.warning, colors.info],
                    borderColor: isDark ? '#111827' : '#fff',
                    borderWidth: 3
                }]
            },
            options: {
                ...baseConfig,
                plugins: {
                    ...baseConfig.plugins,
                    legend: { ...baseConfig.plugins.legend, position: 'bottom' }
                }
            }
        });
    }

    const trendCtx = document.getElementById('registrationTrendChart');
    if (trendCtx) {
        new Chart(trendCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: chartData.registrationTrend.labels,
                datasets: [{
                    label: 'New Registrations',
                    data: chartData.registrationTrend.data,
                    borderColor: colors.primary,
                    backgroundColor: 'rgba(139, 30, 63, 0.08)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                    pointBackgroundColor: colors.primary,
                    pointBorderColor: isDark ? '#111827' : '#fff',
                    pointBorderWidth: 2,
                    pointHoverRadius: 6
                }]
            },
            options: {
                ...baseConfig,
                scales: {
                    y: { beginAtZero: true, grid: { color: colors.grid }, ticks: makeTickStyle() },
                    x: { grid: { display: false }, ticks: makeTickStyle() }
                }
            }
        });
    }

    const communityCtx = document.getElementById('usersByCommunityChart');
    if (communityCtx) {
        new Chart(communityCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: chartData.usersByCommunity.labels,
                datasets: [{
                    label: 'Members',
                    data: chartData.usersByCommunity.data,
                    backgroundColor: [colors.accent, colors.info, colors.secondary, colors.warning, colors.primary],
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                ...baseConfig,
                indexAxis: 'y',
                scales: {
                    x: { beginAtZero: true, grid: { color: colors.grid }, ticks: makeTickStyle() },
                    y: { grid: { display: false }, ticks: makeTickStyle() }
                }
            }
        });
    }

    const donationCtx = document.getElementById('donationsByMonthChart');
    if (donationCtx) {
        new Chart(donationCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: chartData.donationsByMonth.labels,
                datasets: [{
                    label: 'Donation Amount ($)',
                    data: chartData.donationsByMonth.data,
                    borderColor: colors.secondary,
                    backgroundColor: 'rgba(255, 107, 107, 0.12)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 5,
                    pointBackgroundColor: colors.secondary,
                    pointBorderColor: isDark ? '#111827' : '#fff',
                    pointBorderWidth: 2,
                    pointHoverRadius: 7
                }]
            },
            options: {
                ...baseConfig,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: colors.grid },
                        ticks: {
                            ...makeTickStyle(),
                            callback: function (value) {
                                return '$' + value;
                            }
                        }
                    },
                    x: { grid: { display: false }, ticks: makeTickStyle() }
                }
            }
        });
    }
})();