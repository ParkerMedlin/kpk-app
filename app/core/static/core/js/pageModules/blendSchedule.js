import { AddLotNumModal } from '../objects/modalObjects.js';
const thisAddLotNumModal = new AddLotNumModal();
import { ShiftSelectCheckBoxes } from '../objects/pageUtilities.js'

$(document).ready(function(){
    $('.lotNumButton').each(function(){
        $(this).click(thisAddLotNumModal.setAddLotModalInputs);
    });
    const thisShiftSelectCheckBoxes = new ShiftSelectCheckBoxes();
    const urlParameters = new URLSearchParams(window.location.search);
    let blendArea = urlParameters.get('blendarea');
    thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule`);
});