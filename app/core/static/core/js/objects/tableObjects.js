export class FilterForm {
    constructor(options = {}) {
        this.inputSelector = options.inputSelector || '#id_filter_criteria';
        this.tableSelector = options.tableSelector || '#displayTable';
        this.rowSelector = options.rowSelector || 'tr.filterableRow';
        this.ignoreSelectors = Array.isArray(options.ignoreSelectors) ? options.ignoreSelectors : [];

        try {
            this.setUpFiltering();
        } catch (err) {
            console.error(err.message);
        }
    }

    setUpFiltering() {
        const $input = $(this.inputSelector);
        if (!$input.length) {
            console.warn(`FilterForm: input element not found for selector ${this.inputSelector}`);
            return;
        }

        $input.on('keyup', () => {
            const value = this._normalizeText($input.val());
            $(`${this.tableSelector} ${this.rowSelector}`).each((_, element) => {
                const $row = $(element);
                const rowText = this._getRowSearchText($row);
                const isMatch = rowText.includes(value);

                $row.toggle(isMatch);
                if (isMatch) {
                    $row.addClass('chosen');
                } else {
                    $row.removeClass('chosen');
                }
            });
        });
    }

    _getRowSearchText($row) {
        let text;

        if (this.ignoreSelectors.length) {
            const $clone = $row.clone();
            this.ignoreSelectors.forEach((selector) => {
                $clone.find(selector).remove();
            });
            text = $clone.text();
        } else {
            text = $row.text();
        }

        return this._normalizeText(text);
    }

    _normalizeText(value) {
        return (value || '').toString().toLowerCase().replace(/\s+/g, '');
    }
}

export function initDataTableWithExport(tableSelector, options = {}) {
    if (!tableSelector) {
        console.warn('initDataTableWithExport: tableSelector is required');
        return null;
    }

    const $table = $(tableSelector);
    if (!$table.length) {
        console.warn(`initDataTableWithExport: no table found for selector ${tableSelector}`);
        return null;
    }

    const defaults = {
        paging: false,
        order: [[0, 'asc']],
        dom: 'Bfrtip',
        buttons: ['copy', 'csv', 'excel', 'print']
    };

    try {
        return $table.DataTable({ ...defaults, ...options });
    } catch (error) {
        console.error('initDataTableWithExport: failed to initialize DataTable', error);
        alert('Unable to initialize table with export options.');
        return null;
    }
}

export class SortableRows {
    constructor(options = {}) {
        this.tableSelector = options.tableSelector;
        this.rowSelector = options.rowSelector || '.tableBodyRow';
        this.orderColumnIndex = options.orderColumnIndex ?? 0;
        this.onReorder = typeof options.onReorder === 'function' ? options.onReorder : () => {};
        this.getRowId = options.getRowId || ((row) => $(row).data('id'));

        this._init();
    }

    _init() {
        if (!this.tableSelector) {
            console.warn('SortableRows: tableSelector is required');
            return;
        }

        const $table = $(this.tableSelector);
        if (!$table.length) {
            console.warn(`SortableRows: no table found for selector ${this.tableSelector}`);
            return;
        }

        $table.sortable({
            items: this.rowSelector,
            cursor: 'move',
            axis: 'y',
            dropOnEmpty: false,
            start: (e, ui) => ui.item.addClass('selected'),
            stop: (e, ui) => {
                ui.item.removeClass('selected');
                this._updateOrderValues();
                this._invokeCallback();
            }
        });
    }

    _updateOrderValues() {
        $(this.tableSelector).find('tr').each((index, row) => {
            if (index > 0) {
                $(row).find('td').eq(this.orderColumnIndex).html(index);
            }
        });
    }

    _invokeCallback() {
        const orderedData = [];
        $(this.tableSelector).find(this.rowSelector).each((index, row) => {
            orderedData.push({
                id: this.getRowId(row),
                order: index + 1
            });
        });

        try {
            this.onReorder(orderedData);
        } catch (error) {
            console.error('SortableRows: onReorder callback failed', error);
            alert('Unable to update order. Please try again.');
        }
    }

    destroy() {
        try {
            $(this.tableSelector).sortable('destroy');
        } catch (error) {
            console.error('SortableRows: destroy failed', error);
        }
    }
}