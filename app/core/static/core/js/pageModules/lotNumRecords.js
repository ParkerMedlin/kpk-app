import { DeleteLotNumModal, AddLotNumModal, EditLotNumModal } from '../objects/modalObjects.js';
import { ShiftSelectCheckBoxes } from '../objects/pageUtilities.js'
import { CreateCountListButton, GHSSheetGenerator, CreateBlendLabelButton, EditLotNumButton } from '../objects/buttonObjects.js'

$(document).ready(function(){
    const thisShiftSelectCheckBoxes = new ShiftSelectCheckBoxes();
    const thisGHSSheetGenerator = new GHSSheetGenerator();
    let thisScheduleItemModal;

    const $addLotNumButton = $("#addLotNumButton");
    const $batchDeleteButton = $('#batchDeleteButton');
    const $createCountListButton = $("#create_list");
    const deleteButtons = document.querySelectorAll('.deleteBtn');
    const editLotButtons = document.querySelectorAll('.editLotButton');
    const checkBoxes = document.querySelectorAll('.rowCheckBox');
    const $duplicateBtns = $(".duplicateBtn");
    const $addToScheduleLinks = $(".addToScheduleLink");

    const thisAddLotNumModal = new AddLotNumModal();
    $duplicateBtns.each(function(){
        $(this).click(thisAddLotNumModal.setAddLotModalInputs);
    });
    $addLotNumButton.click(function(e) {
        e.preventDefault();
        $(this).click(thisAddLotNumModal.setAddLotModalInputs);
    });
    thisAddLotNumModal.formElement.prop("action", "/core/add-lot-num-record/?redirect-page=lot-num-records")

    
    const thisDeleteLotNumModal = new DeleteLotNumModal();

    const thisEditLotNumModal = new EditLotNumModal();
    editLotButtons.forEach(button => {
        let thisEditLotNumButton = new EditLotNumButton(button);
    })

    checkBoxes.forEach(checkBox => {
        checkBox.addEventListener('click', function(){
            let item_codes = [];
            $('td input:checked').each(function() {
                item_codes.push($(this).attr("name"));
            });
            $createCountListButton.show();
            $batchDeleteButton.show();
            $batchDeleteButton.attr("dataitemid", item_codes);
        });
    });
    deleteButtons.forEach(delButton => {
        delButton.addEventListener('click', thisDeleteLotNumModal.setModalButtons);
    });
    $batchDeleteButton.click(thisDeleteLotNumModal.setModalButtons);

    const thisCreateCountListButton = new CreateCountListButton();

    const blendLabelLinks = document.querySelectorAll(".blendLabelLink");
    let dialog = document.querySelector('#blendLabelDialog');
    blendLabelLinks.forEach(function(link) {
        let thisCreateBlendLabelButton = new CreateBlendLabelButton(link);
        link.addEventListener('click', function(event) {
            dialog.showModal();
            $("#printButton").attr("data-encoded-item-code", event.currentTarget.getAttribute("data-encoded-item-code"));
            $("#printButton").attr("data-lot-number", event.currentTarget.getAttribute("data-lot-number"));
            const batchQuantity = event.currentTarget.getAttribute("data-lot-quantity");
            const labelQuantity = Math.ceil(batchQuantity / 250)*2;
            $("#labelQuantity").val(labelQuantity);
        });
    });

    // const thisZebraPrintButton = new ZebraPrintButton(document.querySelector('#printButton'));

});