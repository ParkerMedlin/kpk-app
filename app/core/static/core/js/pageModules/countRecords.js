import { DeleteCountRecordModal, EditConfirmCountRecordModal } from '../objects/modalObjects.js'
import { getItemCodesForCheckedBoxes } from '../uiFunctions/uiFunctions.js'

$(document).ready(function() {
    const $createReportButton = $('#createReportButton');
    const $batchDeleteButton = $('#batchDeleteButton');
    const $batchEditButton = $('#batchEditButton');
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

            $batchDeleteButton.attr('dataitemid', )
        });
    });


    $createReportButton.click(function() {
        let item_codes = getItemCodesForCheckedBoxes();
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


    $batchDeleteButton.click(function(e) {
        let itemCodes = getItemCodesForCheckedBoxes();
        e.currentTarget.setAttribute("dataitemid", itemCodes);
        if (itemCodes.length === 0) {
            alert("Please check at least one row to delete.")
        } else {
            thisDeleteCountRecordModal.setModalButtons(e);
        }
    });

    $batchEditButton.click(function(e) {
        let itemCodes = getItemCodesForCheckedBoxes();
        e.currentTarget.setAttribute("dataitemid", itemCodes);
        if (itemCodes.length === 0) {
            alert("Please check at least one row to delete.")
        } else {
            thisEditConfirmCountRecordModal.setModalButtons(e);
        }
    });



});