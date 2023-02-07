import { DeleteLotNumModal, AddLotNumModal, AddDeskOneItemModal, AddDeskTwoItemModal } from '../objects/modalObjects.js';

$(document).ready(function(){
    let thisScheduleItemModal;

    const $addLotNumButton = $("#addLotNumButton");
    const $batchDeleteButton = $('#batchDeleteButton');
    const deleteButtons = document.querySelectorAll('.deleteBtn');
    const checkBoxes = document.querySelectorAll('.rowCheckBox');
    const $duplicateBtns = $(".duplicateBtn");
    const $addToScheduleLinks = $(".addToScheduleLink");


    $addToScheduleLinks.each(function(){
        $(this).click(function(){
            if ($(this).attr('data-blendDesk')=='Desk_1'){
                thisScheduleItemModal = new AddDeskOneItemModal()
            } else if ($(this).attr('data-blendDesk')=='Desk_2') {
                thisScheduleItemModal = new AddDeskTwoItemModal()
            }
            thisScheduleItemModal.setUpScheduleModal($(this));
        });
    });


    const thisAddLotNumModal = new AddLotNumModal();
    $duplicateBtns.each(function(){
        $(this).click(thisAddLotNumModal.setAddLotModalInputs);
    });
    $addLotNumButton.click(function() {
        $(this).click(thisAddLotNumModal.setAddLotModalInputs);
    });

    
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

});