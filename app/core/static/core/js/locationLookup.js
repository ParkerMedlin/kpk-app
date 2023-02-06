import { getAllItemCodeAndDesc } from './requestFunctions/requestFunctions.js'

//var caching
// let availableItemCodes;
// let availableItemDesc;
let $itemCodeInput = $("#id_item_code");
let $itemDescriptionInput = $("#id_item_description");
let $itemLocation = $('#id_location');
let $itemQty = $('#id_quantity')
let $animation = $(".animation");

function setFields(locationData){
    $itemCodeInput.val(locationData.item_code);
    $itemDescriptionInput.val(locationData.item_description);
    $itemLocation.text(locationData.general_location + ", " + locationData.specific_location);
    $itemQty.text(locationData.qtyonhand + " " + locationData.standard_uom + " on hand.");
}

try {
    $( function() {
        getAllItemCodeAndDesc();

        // ===============  Item Number Search  ==============
        $itemCodeInput.autocomplete({ // Sets up a dropdown for the part number field 
            minLength: 2,
            autoFocus: true,
            source: function (request, response) {
                let results = $.ui.autocomplete.filter(availableItemCodes, request.term);
                response(results.slice(0,10));
            },
            change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                indicateLoading("itemCode");
                let itemCode;
                if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                    itemCode = $itemCodeInput.val();
                } else {
                    itemCode = ui.item.label.toUpperCase();
                }
                let locationData = getLocation(itemCode, "itemCode");
                setFields(locationData);
            },
            select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                indicateLoading();
                let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                let locationData = getLocation(itemCode, "itemCode");
                setFields(locationData);
            },
        });

        //   ===============  Description Search  ===============
        $itemDescriptionInput.autocomplete({ // Sets up a dropdown for the part number field 
            minLength: 3,
            autoFocus: true,
            source: function (request, response) {
                let results = $.ui.autocomplete.filter(availableItemDesc, request.term);
                response(results.slice(0,300));
            },
            change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                indicateLoading("itemDescription");
                let itemDesc;
                if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                    itemDesc = $itemDescriptionInput.val();
                } else {
                    itemDesc = ui.item.label.toUpperCase();
                }
                let locationData = getLocation(itemDesc, "itemDescription");
                setFields(locationData);
            },
            select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                indicateLoading();
                let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                let locationData = getLocation(itemDesc, "itemDescription");
                setFields(locationData);
            },
        });
    });
} catch (pnError) {
    console.log(pnError)
};




$itemCodeInput.focus(function(){
    $animation.hide();
}); 
$itemDescriptionInput.focus(function(){
    $animation.hide();
});