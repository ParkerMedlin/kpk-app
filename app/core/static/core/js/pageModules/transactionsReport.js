import { initDataTableWithExport } from '../objects/tableObjects.js';

$(document).ready(function () {
    initDataTableWithExport('#transactionsReportTable', {
        order: [[4, 'desc']],
        buttons: ['copy', 'csv', 'excel', 'print']
    });
});
