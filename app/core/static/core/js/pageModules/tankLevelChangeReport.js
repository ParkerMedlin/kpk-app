import { initDataTableWithExport } from '../objects/tableObjects.js';

$(document).ready(function () {
    initDataTableWithExport('#tankLevelChangeTable', {
        order: [[1, 'desc']],
        buttons: ['copy', 'csv', 'excel', 'print']
    });
});
