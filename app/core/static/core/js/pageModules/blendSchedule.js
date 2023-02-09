import { AddLotNumModal } from '../objects/modalObjects.js';
const thisAddLotNumModal = new AddLotNumModal();

$(document).ready(function(){
    $('.lotNumButton').each(function(){
        $(this).click(thisAddLotNumModal.setAddLotModalInputs);
    });
    const urlParameters = new URLSearchParams(window.location.search);
    let blendArea = urlParameters.get('blendarea');
    thisAddLotNumModal.formElement.prop("action", `/core/addlotnumrecord/blendschedule?=${blendArea}`);
});