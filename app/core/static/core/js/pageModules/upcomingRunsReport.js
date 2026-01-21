$(document).ready(function(){
    $('#upcomingRunsReportTable').DataTable({
        paging: false,
        dom: 'Bfrtip',
        buttons: ['copy', 'csv', 'excel', 'print'],
        columnDefs: [
            { orderable: false, targets: [2,3,5,8] }  // 0-based column index
        ]
    });
});