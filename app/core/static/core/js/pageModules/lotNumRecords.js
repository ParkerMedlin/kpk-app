import { DeleteLotNumModal, AddLotNumModal, EditLotNumModal } from '../objects/modalObjects.js';
import { ShiftSelectCheckBoxes } from '../objects/pageUtilities.js'
import { CreateCountListButton, GHSSheetGenerator } from '../objects/buttonObjects.js'

$(document).ready(function(){
    const thisShiftSelectCheckBoxes = new ShiftSelectCheckBoxes();
    const thisGHSSheetGenerator = new GHSSheetGenerator();
    let thisScheduleItemModal;

    const $addLotNumButton = $("#addLotNumButton");
    const $batchDeleteButton = $('#batchDeleteButton');
    const deleteButtons = document.querySelectorAll('.deleteBtn');
    const checkBoxes = document.querySelectorAll('.rowCheckBox');
    const $duplicateBtns = $(".duplicateBtn");
    const $addToScheduleLinks = $(".addToScheduleLink");

    const thisAddLotNumModal = new AddLotNumModal();
    $duplicateBtns.each(function(){
        $(this).click(thisAddLotNumModal.setAddLotModalInputs);
    });
    $addLotNumButton.click(function() {
        $(this).click(thisAddLotNumModal.setAddLotModalInputs);
    });
    thisAddLotNumModal.formElement.prop("action", "/core/add-lot-num-record/?redirect-page=lot-num-records")

    const thisEditLotNumModal = new EditLotNumModal();
    
    const thisDeleteLotNumModal = new DeleteLotNumModal();
    checkBoxes.forEach(checkBox => {
        checkBox.addEventListener('click', function(){
            let item_codes = [];
            $('td input:checked').each(function() {
                item_codes.push($(this).attr("name"));
            });
            $batchDeleteButton.show();
            $batchDeleteButton.attr("dataitemid", item_codes);
        });
    });
    deleteButtons.forEach(delButton => {
        delButton.addEventListener('click', thisDeleteLotNumModal.setModalButtons);
    });
    $batchDeleteButton.click(thisDeleteLotNumModal.setModalButtons);

    const thisCreateCountListButton = new CreateCountListButton();


});