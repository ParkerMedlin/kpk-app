import { initDataTableWithExport } from '../objects/tableObjects.js';

$(document).ready(function(){
    initDataTableWithExport('#countsAndTransactionsTable', {
        order: [[4, 'desc']],
        buttons: ['copy', 'csv', 'excel', 'print'],
        paging: false,
        columnDefs: [
            { orderable: false, targets: [0,1,2,3,5,6] }  // 0-based column index
        ]
    });
});