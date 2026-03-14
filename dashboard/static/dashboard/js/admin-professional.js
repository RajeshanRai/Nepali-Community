(function () {
    function toSortableValue(text) {
        const clean = (text || '').trim();
        const numberMatch = clean.replace(/[$,%#\s,]/g, '');
        const numberValue = Number(numberMatch);
        if (!Number.isNaN(numberValue) && clean !== '') {
            return numberValue;
        }
        return clean.toLowerCase();
    }

    function enhanceTableSorting(table) {
        const headers = table.querySelectorAll('thead th');
        if (!headers.length) {
            return;
        }

        headers.forEach((header, index) => {
            header.style.cursor = 'pointer';
            header.title = 'Click to sort';
            let direction = 'asc';

            header.addEventListener('click', () => {
                const body = table.tBodies[0];
                if (!body) {
                    return;
                }

                const rows = Array.from(body.querySelectorAll('tr'));
                const dataRows = rows.filter((row) => row.querySelectorAll('td').length === headers.length);
                if (!dataRows.length) {
                    return;
                }

                dataRows.sort((leftRow, rightRow) => {
                    const leftValue = toSortableValue(leftRow.cells[index]?.innerText || '');
                    const rightValue = toSortableValue(rightRow.cells[index]?.innerText || '');

                    if (leftValue < rightValue) {
                        return direction === 'asc' ? -1 : 1;
                    }
                    if (leftValue > rightValue) {
                        return direction === 'asc' ? 1 : -1;
                    }
                    return 0;
                });

                dataRows.forEach((row) => body.appendChild(row));
                direction = direction === 'asc' ? 'desc' : 'asc';
            });
        });
    }

    function addTableShadows() {
        document.querySelectorAll('.table-responsive').forEach((container) => {
            const update = () => {
                const atStart = container.scrollLeft <= 0;
                const atEnd = container.scrollLeft + container.clientWidth >= container.scrollWidth - 1;
                container.style.boxShadow = atStart && atEnd
                    ? 'none'
                    : 'inset 12px 0 10px -14px rgba(15, 23, 42, 0.35), inset -12px 0 10px -14px rgba(15, 23, 42, 0.35)';
            };
            container.addEventListener('scroll', update);
            update();
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.data-table').forEach((table) => {
            if (!table.dataset.disableSorting) {
                enhanceTableSorting(table);
            }
        });

        addTableShadows();
    });
})();
