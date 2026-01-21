$(document).ready(function(){
    $('#startronReportTable').DataTable({
        paging: false,
        dom: 'Bfrtip',
        buttons: ['copy', 'csv', 'excel', 'print']
    });
});
