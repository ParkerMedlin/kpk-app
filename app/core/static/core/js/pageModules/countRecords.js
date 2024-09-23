import { EditConfirmCountRecordModal } from '../objects/modalObjects.js'
import { CreateCountsReportButton, BatchEditCountRecordsButton, CreateCountListButton } from '../objects/buttonObjects.js'
import { RecountsButton, RecordNumberButton } from '../objects/buttonObjects.js'
import { ShiftSelectCheckBoxes } from '../objects/pageUtilities.js'

$(document).ready(function() {
    const thisRecountsButton = new RecountsButton();
    const thisCreateCountListButton = new CreateCountListButton();
    const $createReportButton = $('#createReportButton');
    const $batchEditButton = $('#batchEditButton');
    const $batchDeleteButton = $('#batchDeleteButton');
    const deleteButtons = document.querySelectorAll('.deleteBtn');
    const editButtons = document.querySelectorAll('.editBtn');
    const checkBoxes = document.querySelectorAll('.reportCheckBox');
    
    // const thisDeleteCountRecordModal = new DeleteCountRecordModal();
    const thisEditConfirmCountRecordModal = new EditConfirmCountRecordModal();
    const thisCreateCountsReportButton = new CreateCountsReportButton();
    // const thisBatchDeleteCountRecordsButton = new BatchDeleteCountRecordsButton(thisDeleteCountRecordModal);
    const thisBatchEditCountRecordsButton = new BatchEditCountRecordsButton(thisEditConfirmCountRecordModal);

    // deleteButtons.forEach(delButton => {
    //     delButton.addEventListener('click', thisDeleteCountRecordModal.setModalButtons);
    //     });
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

    $('#recountsButton').click(function(){
        $createReportButton.show();
        $batchDeleteButton.show();
        $batchEditButton.show();
        $batchDeleteButton.attr('dataitemid', )
    });
    
    const thisShiftSelectCheckBoxes = new ShiftSelectCheckBoxes();
    const thisRecordNumberButton  = new RecordNumberButton(document.getElementById("recordNumberButton"));
});