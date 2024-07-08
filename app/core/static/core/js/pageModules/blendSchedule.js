import { AddLotNumModal } from '../objects/modalObjects.js';
const thisAddLotNumModal = new AddLotNumModal();
import { ShiftSelectCheckBoxes } from '../objects/pageUtilities.js'
import { getMatchingLotNumbers } from '../requestFunctions/requestFunctions.js'

$(document).ready(function(){
    $('.lotNumButton').each(function(){
        $(this).click(thisAddLotNumModal.setAddLotModalInputs);
    });
    const thisShiftSelectCheckBoxes = new ShiftSelectCheckBoxes();
    const urlParameters = new URLSearchParams(window.location.search);
    let blendArea = urlParameters.get('blend-area');
    console.log(blendArea);
    if (blendArea == 'Hx') {
        thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-hx`);
    } else if (blendArea == 'Dm') {
        thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-dm`);
    } else if (blendArea == 'Totes') {
        thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-totes`);
    } else if (blendArea == 'Desk_1') {
        thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-desk-1`);
    } else if (blendArea == 'Desk_2') {
        thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-desk-2`);
    }
});