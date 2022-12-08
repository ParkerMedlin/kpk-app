$(document).ready(function() {
    const $batchDeleteButton = $('#batchDeleteButton');
    const $modalButtonLink = $("#modalButtonLink");
    const $modalLabel = $('#lotNumConfirmModalLabel');
    const $modalBody = $('#lotNumConfirmModalBody');
    const $modalButton = $('#modalButton');
    const deleteButtons = document.querySelectorAll('.deleteBtn');
    //const editButtons = document.querySelectorAll('.editBtn');
    const checkBoxes = document.querySelectorAll('.rowCheckBox');
    
    console.log('')


    deleteButtons.forEach(delButton => {
        delButton.addEventListener('click', function setModalButton(e) {
            let count_id = e.target.getAttribute("dataitemid");
            let encoded_list = btoa(JSON.stringify(count_id));
            checkBoxes.forEach(checkBox => {
                checkBox.checked = false;
            });
            $modalButtonLink.attr("href", `/core/deletelotnumrecords/${encoded_list}`);
            $modalLabel.text('Confirm Deletion');
            $modalBody.text('Are you sure?');
            $modalButton.text('Delete');
            $modalButton.removeClass( "btn-primary" ).addClass( "btn-outline-danger" );
        });
    });


    //editButtons.forEach(editButton => {
    //    editButton.addEventListener('click', function setModalButton(e) {
    //        let count_id = e.target.getAttribute("dataitemid");
    //        let encoded_list = btoa(JSON.stringify(count_id));
    //        checkBoxes.forEach(checkBox => {
    //            checkBox.checked = false;
    //        });
    //        $modalButtonLink.attr("href", `/core/countlist/display/${encoded_list}`);
    //        $modalLabel.text('Confirm Edit');
    //        $modalBody.text('Edit the selected count?');
    //        $modalButton.text('Edit');
    //        $modalButton.removeClass( "btn-outline-danger" ).addClass( "btn-primary" );
    //    });
    //});
    
    
    checkBoxes.forEach(checkBox => {
        checkBox.addEventListener('click', function(){
            $batchDeleteButton.show();
        });
    });


    //$createReportButton.click(function() {
    //    let part_numbers = [];
    //    $('td input:checked').each(function() {
    //        part_numbers.push($(this).attr("name"));
    //    });
    //    console.log(part_numbers)
    //    if (part_numbers.length === 0) {
    //        alert("Please check at least one row to include in the report.")
    //    } else {
    //        // https://stackoverflow.com/questions/4505871/good-way-to-serialize-a-list-javascript-ajax
    //        let encoded_list = btoa(JSON.stringify(part_numbers));
    //        console.log(encoded_list)
    //        base_url = window.location.href.split('core')[0];
    //        // https://stackoverflow.com/questions/503093/how-do-i-redirect-to-another-webpage
    //        window.location.replace(base_url + "core/displayfinishedcounts/"+encoded_list)
    //    }
    //});


    $batchDeleteButton.click(function() {
        let part_numbers = [];
        $('td input:checked').each(function() {
            part_numbers.push($(this).attr("name"));
        });
        console.log(part_numbers)
        if (part_numbers.length === 0) {
            alert("Please check at least one row to delete.")
        } else {
            let encoded_list = btoa(JSON.stringify(part_numbers));
            base_url = window.location.href.split('core')[0];
            $modalButtonLink.attr("href", `/core/deletelotnumrecords/${encoded_list}`);
            $modalLabel.text('Confirm Deletion');
            $modalButton.text('Delete');
            $modalButton.addClass("btn-outline-danger").removeClass("btn-primary");
            $modalBody.text('Are you sure?');
        }
    });

    //$batchEditButton.click(function() {
    //    let part_numbers = [];
    //    $('td input:checked').each(function() {
    //        part_numbers.push($(this).attr("name"));
    //    });
    //    console.log(part_numbers)
    //    if (part_numbers.length === 0) {
    //        alert("Please check at least one row to delete.")
    //    } else {
    //        let encoded_list = btoa(JSON.stringify(part_numbers));
    //        console.log(encoded_list)
    //        base_url = window.location.href.split('core')[0];
    //        $modalButtonLink.attr("href", `/core/countlist/display/${encoded_list}`);
    //        $modalLabel.text('Confirm Edit');
    //        if (part_numbers.length==1){
    //            modalBodyString = 'Edit the selected count?'
    //        } else {
    //            modalBodyString = 'Edit the selected counts?'
    //        }
    //        $modalBody.text(modalBodyString);
    //        $modalButton.text('Edit');
    //        $modalButton.removeClass("btn-outline-danger").addClass("btn-primary");
    //    }
    //});



});