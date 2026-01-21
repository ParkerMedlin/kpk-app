$(document).ready(function(){
    $('#whereUsedReportTable').DataTable({
        paging: false,
        dom: 'Bfrtip',
        buttons: ['copy', 'csv', 'excel', 'print']
    });
});
