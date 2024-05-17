import { AddLotNumModal } from '../objects/modalObjects.js';
import { CreateCountListButton } from '../objects/buttonObjects.js'
import { ShiftSelectCheckBoxes } from '../objects/pageUtilities.js'
import { FilterForm } from '../objects/lookupFormObjects.js'



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
    thisAddLotNumModal.formElement.prop("action", "/core/add-lot-num-record/?redirect-page=blend-shortages")
    const thisCreateCountListButton = new CreateCountListButton();
    const thisFilterForm = new FilterForm();

    // encode any componentItemCode values in any shortage flag dropdowns
    // and append that value to the end of the PO report url
    $('.po-report-link').each(function(){
        let encodedComponentItemCode = btoa($(this).data("compitemcode"));
        // console.log($(this).data("compitemcode"));
        $(this).prop("href", `${$(this).prop("href")}?itemCode=${encodedComponentItemCode}`);
    });

    // encode any componentItemCode values in any shortage flag dropdowns
    // and append that value to the end of the usage report url
    $('.usage-report-link').each(function(){
        let encodedComponentItemCode = btoa($(this).data("compitemcode"));
        // console.log($(this).data("compitemcode"));
        $(this).prop("href", `${$(this).prop("href")}?itemCode=${encodedComponentItemCode}`);
    });
    const thisShiftSelectCheckBoxes = new ShiftSelectCheckBoxes();
});