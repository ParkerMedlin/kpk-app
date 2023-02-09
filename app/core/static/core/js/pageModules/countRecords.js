import { DeleteCountRecordModal, EditConfirmCountRecordModal } from '../objects/modalObjects.js'
import { CreateCountsReportButton } from '../objects/buttonObjects.js'

$(document).ready(function() {
    const $createReportButton = $('#createReportButton');
    const $batchDeleteButton = $('#batchDeleteButton');
    const $batchEditButton = $('#batchEditButton');
    const deleteButtons = document.querySelectorAll('.deleteBtn');
    const editButtons = document.querySelectorAll('.editBtn');
    const checkBoxes = document.querySelectorAll('.reportCheckBox');
    
    const thisDeleteCountRecordModal = new DeleteCountRecordModal();
    const thisEditConfirmCountRecordModal = new EditConfirmCountRecordModal();
    const thisCreateCountsReportButton = new CreateCountsReportButton();

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