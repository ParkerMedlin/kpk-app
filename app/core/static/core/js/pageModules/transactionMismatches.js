import { initDataTableWithExport } from '../objects/tableObjects.js';

$(document).ready(function () {
    initDataTableWithExport('#transactionMismatchesTable', {
        order: [[2, 'desc']],
        buttons: ['copy', 'csv', 'excel', 'print'],
        columnDefs: [
            { orderable: false, targets: [3,4,5] }  // 0-based column index
        ]
    });
});
