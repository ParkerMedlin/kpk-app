import { initDataTableWithExport } from '../objects/tableObjects.js';

$(document).ready(function () {
    initDataTableWithExport('#inventoryCountsTable', {
        order: [[3, 'desc']],
        buttons: ['copy', 'csv', 'excel', 'print']
    });
});
