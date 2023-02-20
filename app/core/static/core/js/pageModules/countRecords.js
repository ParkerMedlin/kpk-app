import { DeleteCountRecordModal, EditConfirmCountRecordModal } from '../objects/modalObjects.js'
import { CreateCountsReportButton, BatchDeleteCountRecordsButton, BatchEditCountRecordsButton } from '../objects/buttonObjects.js'

$(document).ready(function() {
    const $createReportButton = $('#createReportButton');
    const $batchEditButton = $('#batchEditButton');
    const $batchDeleteButton = $('#batchDeleteButton');
    const deleteButtons = document.querySelectorAll('.deleteBtn');
    const editButtons = document.querySelectorAll('.editBtn');
    const checkBoxes = document.querySelectorAll('.reportCheckBox');
    
    const thisDeleteCountRecordModal = new DeleteCountRecordModal();
    const thisEditConfirmCountRecordModal = new EditConfirmCountRecordModal();
    const thisCreateCountsReportButton = new CreateCountsReportButton();
    const thisBatchDeleteCountRecordsButton = new BatchDeleteCountRecordsButton(thisDeleteCountRecordModal);
    const thisBatchEditCountRecordsButton = new BatchEditCountRecordsButton(thisEditConfirmCountRecordModal);

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
});