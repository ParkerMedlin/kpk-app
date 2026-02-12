import { initDataTableWithExport } from '../objects/tableObjects.js';

$(document).ready(function () {
    initDataTableWithExport('#countStatusTable', {
        order: [[0, 'asc']],
        buttons: ['csv', 'excel'],
    });
});
