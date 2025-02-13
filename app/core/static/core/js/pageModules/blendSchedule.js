import { AddLotNumModal } from '../objects/modalObjects.js';
import { ShiftSelectCheckBoxes } from '../objects/pageUtilities.js'
import { getMatchingLotNumbers } from '../requestFunctions/requestFunctions.js'
import { AddScheduleStopperButton, TableSorterButton, GHSSheetGenerator, CreateBlendLabelButton } from '../objects/buttonObjects.js' 

$(document).ready(function(){
    const thisGHSSheetGenerator = new GHSSheetGenerator();
    const thisShiftSelectCheckBoxes = new ShiftSelectCheckBoxes();
    const urlParameters = new URLSearchParams(window.location.search);
    let blendArea = urlParameters.get('blend-area');
    console.log(blendArea);
    if (blendArea == 'Hx') {
      const thisAddLotNumModal = new AddLotNumModal();
      $('.lotNumButton').each(function(){
          $(this).click(thisAddLotNumModal.setAddLotModalInputs);
      });
      thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-hx`);
    } else if (blendArea == 'Dm') {
      const thisAddLotNumModal = new AddLotNumModal();
      $('.lotNumButton').each(function(){
          $(this).click(thisAddLotNumModal.setAddLotModalInputs);
      });
      thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-dm`);
    } else if (blendArea == 'Totes') {
      const thisAddLotNumModal = new AddLotNumModal();
      $('.lotNumButton').each(function(){
          $(this).click(thisAddLotNumModal.setAddLotModalInputs);
      });
      thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-totes`);
    } else if (blendArea == 'Desk_1') {
        // thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-desk-1`);
        new TableSorterButton('deskScheduleTable', 'Short');
        new AddScheduleStopperButton(document.getElementById("noteRowButton"), 'Desk_1');
    } else if (blendArea == 'Desk_2') {
        // thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-desk-2`);
        const thisTableSorter = new TableSorterButton('deskScheduleTable', 'Short');
        const thisAddScheduleStopperButton = new AddScheduleStopperButton(document.getElementById("noteRowButton"), 'Desk_2');
        document.getElementById('sortByShortButton').click();
    }

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


});