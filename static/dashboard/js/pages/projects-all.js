(function () {
    document.addEventListener('DOMContentLoaded', function () {
        const searchInput = document.getElementById('searchProjects');
        const rows = Array.from(document.querySelectorAll('.data-table tbody tr[data-category]'));
        const filterButtons = Array.from(document.querySelectorAll('.filter-btn'));
        const bulkSelectAll = document.getElementById('bulkSelectAll');
        const bulkCheckboxes = Array.from(document.querySelectorAll('.bulk-checkbox'));

        DashboardPageTools.initRowSearch({
            input: searchInput,
            rows
        });

        DashboardPageTools.initButtonFilters({
            buttons: filterButtons,
            rows,
            rowAttribute: 'category'
        });

        DashboardPageTools.initBulkSelection({
            masterCheckbox: bulkSelectAll,
            itemCheckboxes: bulkCheckboxes
        });
    });
})();
