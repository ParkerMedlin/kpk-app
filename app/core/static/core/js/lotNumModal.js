//var caching
let availableItemCodes;
let availableItemDescriptions;
let $itemCodeInput = $("#id_newLotModal-item_code");
let $itemDescriptionInput = $("#id_newLotModal-item_description");
let $animation = $(".animation");

function getAllItemCodeAndDesc(){
    $.getJSON('/core/getBOMfields/?restriction=blends-only', function(data) {
        billOfMaterialsFields = data;
        }).then(function(billOfMaterialsFields) {
            availableItemCodes = billOfMaterialsFields['item_codes'];
            availableItemDescriptions = billOfMaterialsFields['item_descriptions'];
    });
}

function getItemData(lookupValue, lookupType){
    let itemData;
    let jsonURL = `/core/item_location_request/?item=${lookupValue}&lookupType=${lookupType}`;
    $.ajax({
        url: jsonURL,
        async: false,
        dataType: 'json',
        success: function(data) {
            itemData = data;
        }
    }).fail(function() { // err handle
        console.log("Item not found. Check search terms and try again.");
    }).always(function() {
        $animation.toggle();
        $itemCodeInput.removeClass('loading');
        $itemDescriptionInput.removeClass('loading');
    });
    return itemData;
}

function indicateLoading(whichField) {
    if (whichField=="itemCode") {
        $itemDescriptionInput.val("");
    } else {
        $itemCodeInput.val("");
    }
    $animation.toggle();
    $itemCodeInput.addClass('loading');
    $itemDescriptionInput.addClass('loading');
}

function setFields(itemData){
    $itemCodeInput.val(itemData.item_code);
    $itemDescriptionInput.val(itemData.item_description);
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
                let itemData = getItemData(itemCode, "itemCode");
                setFields(itemData);
            },
            select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                indicateLoading();
                let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                let itemData = getItemData(itemCode, "itemCode");
                setFields(itemData);
            },
        });

        //   ===============  Description Search  ===============
        $itemDescriptionInput.autocomplete({ // Sets up a dropdown for the part number field 
            minLength: 3,
            autoFocus: true,
            source: function (request, response) {
                let results = $.ui.autocomplete.filter(availableItemDescriptions, request.term);
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
                let itemData = getItemData(itemDesc, "itemDescription");
                setFields(itemData);
            },
            select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                indicateLoading();
                let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                let itemData = getItemData(itemDesc, "itemDescription");
                setFields(itemData);
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