import { initDataTableWithExport } from '../objects/tableObjects.js';

function formatCurrency(value) {
    const numericValue = Number.parseFloat(value);
    const safeValue = Number.isNaN(numericValue) ? 0 : numericValue;
    return safeValue.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

$(document).ready(function () {
    const tableEl = $('#excessBlendsTable');
    const totalEl = $('#filteredExcessValue');
    const badgeEl = $('#filteredCountBadge');
    const hideSelectedBtn = $('#hideSelectedBtn');
    const resetFiltersBtn = $('#resetFiltersBtn');
    const selectAllCheckbox = $('#selectAllExcess');

    if (!tableEl.length || !$.fn.DataTable) {
        return;
    }

    const filteredItemCodes = new Set();
    const originalTotal = Number.parseFloat(totalEl.data('original-total')) || 0;

    const table = initDataTableWithExport('#excessBlendsTable', {
        order: [[7, 'desc']],
        pageLength: 25,
        lengthMenu: [[25, 50, 100, -1], [25, 50, 100, 'All']],
        dom: 'Blfrtip',
        buttons: ['copy', 'csv', 'excel', 'pdf', 'print'],
        columnDefs: [
            {
                targets: 0,
                orderable: false,
                searchable: false,
                className: 'text-center'
            }
        ]
    });

    const filterFn = function (settings, data, dataIndex) {
        if (settings.nTable !== tableEl.get(0)) {
            return true;
        }
        const rowNode = table.row(dataIndex).node();
        if (!rowNode) {
            return true;
        }
        const itemCode = rowNode.getAttribute('data-item-code');
        return !itemCode || !filteredItemCodes.has(itemCode);
    };

    $.fn.dataTable.ext.search.push(filterFn);

    function updateTotals() {
        let runningTotal = 0;
        table.rows({ filter: 'applied' }).every(function () {
            const rowNode = this.node();
            const valueCell = $(rowNode).find('.excess-value');
            const rawValue = Number.parseFloat(valueCell.data('value'));
            if (!Number.isNaN(rawValue)) {
                runningTotal += rawValue;
            }
        });

        totalEl.text(formatCurrency(runningTotal));
        totalEl.attr('data-current-total', runningTotal);
    }

    function updateBadge() {
        const hiddenCount = filteredItemCodes.size;
        if (!hiddenCount) {
            badgeEl.hide().text('');
            return;
        }
        const currentTotal = Number.parseFloat(totalEl.attr('data-current-total')) || 0;
        const removedValue = Math.max(originalTotal - currentTotal, 0);
        badgeEl
            .text(`${hiddenCount} hidden ($${formatCurrency(removedValue)})`)
            .show();
    }

    function updateHideButtonState() {
        const checkedCount = tableEl.find('tbody input.excess-filter-checkbox:checked').length;
        hideSelectedBtn.prop('disabled', checkedCount === 0);
    }

    tableEl.on('change', 'tbody input.excess-filter-checkbox', updateHideButtonState);

    hideSelectedBtn.on('click', function () {
        const selectedCheckboxes = tableEl.find('tbody input.excess-filter-checkbox:checked');
        if (!selectedCheckboxes.length) {
            return;
        }
        selectedCheckboxes.each(function () {
            const row = this.closest('tr');
            if (!row) {
                return;
            }
            const itemCode = row.getAttribute('data-item-code');
            if (itemCode) {
                filteredItemCodes.add(itemCode);
            }
        });

        hideSelectedBtn.prop('disabled', true);
        selectAllCheckbox.prop('checked', false);
        table.draw(false);
        updateBadge();
    });

    resetFiltersBtn.on('click', function () {
        if (!filteredItemCodes.size) {
            tableEl.find('tbody input.excess-filter-checkbox').prop('checked', false);
            selectAllCheckbox.prop('checked', false);
            hideSelectedBtn.prop('disabled', true);
            updateTotals();
            updateBadge();
            return;
        }

        filteredItemCodes.clear();
        selectAllCheckbox.prop('checked', false);
        hideSelectedBtn.prop('disabled', true);
        table.draw(false);
        updateBadge();
    });

    selectAllCheckbox.on('change', function () {
        const shouldSelect = $(this).is(':checked');
        tableEl.find('tbody input.excess-filter-checkbox').prop('checked', shouldSelect);
        updateHideButtonState();
    });

    table.on('draw', function () {
        tableEl.find('tbody input.excess-filter-checkbox').prop('checked', false);
        selectAllCheckbox.prop('checked', false);
        hideSelectedBtn.prop('disabled', true);
        updateTotals();
        updateBadge();
    });

    table.on('destroy', function () {
        const index = $.fn.dataTable.ext.search.indexOf(filterFn);
        if (index !== -1) {
            $.fn.dataTable.ext.search.splice(index, 1);
        }
    });

    $(window).on('unload', function () {
        const index = $.fn.dataTable.ext.search.indexOf(filterFn);
        if (index !== -1) {
            $.fn.dataTable.ext.search.splice(index, 1);
        }
    });

    updateTotals();
    updateBadge();
});
