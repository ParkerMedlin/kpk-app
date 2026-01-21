import { initDataTableWithExport } from '../objects/tableObjects.js';

$(document).ready(function(){
    initDataTableWithExport('#countsAndTransactionsTable', {
        order: [[4, 'desc']],
        buttons: ['copy', 'csv', 'excel', 'print'],
        paging: false
    });
});