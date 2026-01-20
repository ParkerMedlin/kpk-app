import { initDataTableWithExport } from '../objects/tableObjects.js';

$(document).ready(function () {
    initDataTableWithExport('#transactionMismatchesTable', {
        order: [[2, 'desc']],
        buttons: ['copy', 'csv', 'excel', 'print']
    });
});
