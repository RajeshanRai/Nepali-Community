(function () {
    function textContent(node) {
        return (node?.textContent || '').replace(/\s+/g, ' ').trim();
    }

    function setCellLabels(table) {
        const headers = Array.from(table.querySelectorAll('thead th')).map((th, index) => {
            const label = textContent(th);
            return label || ('Field ' + String(index + 1));
        });
        if (!headers.length) {
            return;
        }

        table.querySelectorAll('tbody tr').forEach((row) => {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                if (cell.hasAttribute('colspan')) {
                    return;
                }

                const label = headers[index] || ('Field ' + String(index + 1));
                if (!cell.dataset.label || cell.dataset.label === '') {
                    cell.setAttribute('data-label', label);
                }
            });
        });
    }

    function applyDensity(table) {
        const columnCount = table.querySelectorAll('thead th').length;
        if (columnCount >= 8) {
            table.classList.add('dct-table-dense');
        }
    }

    function syncScrollShadows(wrapper) {
        if (!wrapper) {
            return;
        }

        const canScroll = wrapper.scrollWidth > wrapper.clientWidth + 2;
        const left = wrapper.scrollLeft;
        const maxLeft = wrapper.scrollWidth - wrapper.clientWidth - 1;

        wrapper.classList.toggle('dct-can-scroll-left', canScroll && left > 2);
        wrapper.classList.toggle('dct-can-scroll-right', canScroll && left < maxLeft);
    }

    function watchScroll(wrapper) {
        if (!wrapper) {
            return;
        }

        const onSync = function () {
            syncScrollShadows(wrapper);
        };

        wrapper.addEventListener('scroll', onSync, { passive: true });
        window.addEventListener('resize', onSync);
        onSync();
    }

    function animateRows(table) {
        const rows = Array.from(table.querySelectorAll('tbody tr'));
        if (!rows.length) {
            return;
        }

        if (!('IntersectionObserver' in window)) {
            rows.forEach((row) => row.classList.add('dct-row-visible'));
            return;
        }

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('dct-row-visible');
                        observer.unobserve(entry.target);
                    }
                });
            },
            { rootMargin: '0px 0px -8% 0px', threshold: 0.05 }
        );

        rows.forEach((row) => {
            row.classList.add('dct-row-enter');
            observer.observe(row);
        });
    }

    function enhanceTable(table) {
        if (!table || table.dataset.dctEnhanced === 'true') {
            return;
        }

        table.dataset.dctEnhanced = 'true';
        table.classList.add('dct-table');

        const wrapper = table.closest('.table-responsive');
        if (wrapper) {
            wrapper.classList.add('dct-table-wrap');
            watchScroll(wrapper);
        }

        setCellLabels(table);
        applyDensity(table);
        animateRows(table);
    }

    function initDashboardTables() {
        document.querySelectorAll('table.data-table').forEach(enhanceTable);
    }

    document.addEventListener('DOMContentLoaded', initDashboardTables);
})();
