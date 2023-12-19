export  function printBlendLabel(imageData){
    let response;
    let printURL = `/core/print-blend-label?imageData=${imageData}`;
    $.post(printURL,{"imageData": imageData}, function(response) {
        if (response.status == 'Success') {
            console.log('Label printed successfully.');
        } else {
            alert('Failed to print label: ' + response.message);
        }
    });
}; 