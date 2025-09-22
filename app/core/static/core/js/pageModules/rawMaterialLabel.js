import { RawLabelLookupForm } from '../objects/lookupFormObjects.js'
import { RawMaterialLabelPrintButton } from '../objects/buttonObjects.js'
// import { RawMaterialLabelPage } from '../objects/pageObjects.js'

$(document).ready(function(){
    const firstRawLabelLookupForm = new RawLabelLookupForm($("#id_item_code_1"),$("#id_item_description_1"),$("#location_field_1"),$("#topUnitsField"));
    const secondRawLabelLookupForm = new RawLabelLookupForm($("#id_item_code_2"),$("#id_item_description_2"),$("#location_field_2"),$("#bottomUnitsField"));
    const thisRawMaterialLabelPrintButton = new RawMaterialLabelPrintButton(document.getElementById("rawMaterialLabelPrintButton"));
    // const thisRawMaterialLabelPage = new RawMaterialLabelPage();
});