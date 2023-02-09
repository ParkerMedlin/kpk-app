import { AddLotNumModal } from '../objects/modalObjects.js';
import { CreateCountListButton } from '../objects/buttonObjects.js'



$(document).ready(function(){
    const thisAddLotNumModal = new AddLotNumModal();
    $('.lotNumButton').each(function(){
        $(this).click(thisAddLotNumModal.setAddLotModalInputs);
    });
    $('input[type="checkbox"').each(function(){
        $(this).click(function() {
            $('#create_list').show();
        });
    });
    thisAddLotNumModal.formElement.prop("action", "/core/addlotnumrecord/blendshortages")
    const thisCreateCountListButton = new CreateCountListButton();
});