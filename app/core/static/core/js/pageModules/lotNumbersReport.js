$(document).ready(function(){
    $('#upcomingRunsReportTable').DataTable({
        paging: false,
        dom: 'Bfrtip',
        buttons: ['copy', 'csv', 'excel', 'print'],
        columnDefs: [
            { orderable: false, targets: [1,2,5,6] }  // 0-based column index
        ]
    });
});