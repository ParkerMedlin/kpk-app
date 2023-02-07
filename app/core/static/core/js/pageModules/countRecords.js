import { DeleteCountRecordModal, EditConfirmCountRecordModal } from '../objects/modalObjects.js'

$(document).ready(function() {
    const $createReportButton = $('#createReportButton');
    const $batchDeleteButton = $('#batchDeleteButton');
    const $batchEditButton = $('#batchEditButton');
    const $modalButtonLink = $("#modalButtonLink");
    const $modalLabel = $('#countRecordsConfirmModalLabel');
    const $modalBody = $('#countRecordsConfirmModalBody');
    const $modalButton = $('#modalButton');
    const deleteButtons = document.querySelectorAll('.deleteBtn');
    const editButtons = document.querySelectorAll('.editBtn');
    const checkBoxes = document.querySelectorAll('.reportCheckBox');
    
    
    const thisDeleteCountRecordModal = new DeleteCountRecordModal();
    const thisEditConfirmCountRecordModal = new EditConfirmCountRecordModal();


    deleteButtons.forEach(delButton => {
        delButton.addEventListener('click', thisDeleteCountRecordModal.setModalButtons);
        });
    editButtons.forEach(editButton => {
        editButton.addEventListener('click', thisEditConfirmCountRecordModal.setModalButtons);
    });
    
    checkBoxes.forEach(checkBox => {
        checkBox.addEventListener('click', function(){
            $createReportButton.show();
            $batchDeleteButton.show();
            $batchEditButton.show();
        });
    });


    $createReportButton.click(function() {
        let item_codes = [];
        $('td input:checked').each(function() {
            item_codes.push($(this).attr("name"));
        });
        console.log(item_codes)
        if (item_codes.length === 0) {
            alert("Please check at least one row to include in the report.")
        } else {
            // https://stackoverflow.com/questions/4505871/good-way-to-serialize-a-list-javascript-ajax
            let encoded_list = btoa(JSON.stringify(item_codes));
            console.log(encoded_list)
            base_url = window.location.href.split('core')[0];
            // https://stackoverflow.com/questions/503093/how-do-i-redirect-to-another-webpage
            window.location.replace(base_url + "core/displayfinishedcounts/"+encoded_list)
        }
    });


    $batchDeleteButton.click(function() {
        let item_codes = [];
        $('td input:checked').each(function() {
            item_codes.push($(this).attr("name"));
        });
        console.log(item_codes)
        if (item_codes.length === 0) {
            alert("Please check at least one row to delete.")
        } else {
            let encoded_list = btoa(JSON.stringify(item_codes));
            console.log(encoded_list)
            console.log("endccciciidooococoococooooode")
            base_url = window.location.href.split('core')[0];
            $modalButtonLink.attr("href", `/core/delete_countrecord/countrecords/${encoded_list}/${encoded_list}`);
            $modalLabel.text('Confirm Deletion');
            $modalButton.text('Delete');
            $modalButton.addClass("btn-outline-danger").removeClass("btn-primary");
            $modalBody.text('Are you sure?');
        }
    });

    $batchEditButton.click(function() {
        let item_codes = [];
        $('td input:checked').each(function() {
            item_codes.push($(this).attr("name"));
        });
        console.log(item_codes)
        if (item_codes.length === 0) {
            alert("Please check at least one row to delete.")
        } else {
            let encoded_list = btoa(JSON.stringify(item_codes));
            console.log(encoded_list)
            base_url = window.location.href.split('core')[0];
            $modalButtonLink.attr("href", `/core/countlist/display/${encoded_list}`);
            $modalLabel.text('Confirm Edit');
            if (item_codes.length==1){
                modalBodyString = 'Edit the selected count?'
            } else {
                modalBodyString = 'Edit the selected counts?'
            }
            $modalBody.text(modalBodyString);
            $modalButton.text('Edit');
            $modalButton.removeClass("btn-outline-danger").addClass("btn-primary");
        }
    });



});