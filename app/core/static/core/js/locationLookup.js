//var caching
let availableItemCodes;
let availableItemDesc;
let $itemCodeInput = $("#id_part_number");
let $itemDescInput = $("#id_description");
let $itemLocation = $('#id_location');
let $itemQty = $('#id_quantity')
let $animation = $(".animation");

function getAllItemCodeAndDesc(){
    $.getJSON('/core/getblendBOMfields/?restriction=no-blends', function(data) {
        blendBOMFields = data;
        }).then(function(blendBOMFields) {
            availableItemCodes = blendBOMFields['itemcodes'];
            availableItemDesc = blendBOMFields['itemdescs'];
    });
}

function getLocation(lookupValue, lookupType){
    let locationData;
    let jsonURL;
    if (lookupType=="item-code"){
        jsonURL = `/core/chemloc_request_itemcode/?item=${lookupValue}`
    } else if (lookupType=="item-desc"){
        jsonURL = `/core/chemloc_request_itemdesc/?item=${lookupValue}`
    }
    $.ajax({
        url: jsonURL,
        async: false,
        dataType: 'json',
        success: function(data) {
            locationData = data;
        }
    }).fail(function() { // err handle
        console.log("Item not found. Check search terms and try again.");
        $itemLocation.text("Item not found. Check search terms and try again.");
        $itemQty.text("Item not found. Check search terms and try again.");
    }).always(function() {
        $animation.toggle();
        $itemCodeInput.removeClass('loading');
        $itemDescInput.removeClass('loading');
    });
    return locationData;
}

function indicateLoading(whichField) {
    if (whichField=="item-code") {
        $itemDescInput.val("");
    } else {
        $itemCodeInput.val("");
    }
    $itemLocation.text("");
    $itemQty.text("");
    $animation.toggle();
    $itemCodeInput.addClass('loading');
    $itemDescInput.addClass('loading');
}

function setFields(locationData){
    $itemCodeInput.val(locationData.itemcode);
    $itemDescInput.val(locationData.description);
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
            change: function(event, ui) { // Autofill desc when change event happens to the part_number field 
                indicateLoading("item-code");
                let itemCode;
                if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                    itemCode = $itemCodeInput.val();
                } else {
                    itemCode = ui.item.label.toUpperCase();
                }
                let locationData = getLocation(itemCode, "item-code");
                setFields(locationData);
            },
            select: function(event , ui) { // Autofill desc when select event happens to the part_number field 
                indicateLoading();
                let itemCode = ui.item.label.toUpperCase(); // Make sure the part_number field is uppercase
                let locationData = getLocation(itemCode, "item-code");
                setFields(locationData);
            },
        });

        //   ===============  Description Search  ===============
        $itemDescInput.autocomplete({ // Sets up a dropdown for the part number field 
            minLength: 3,
            autoFocus: true,
            source: function (request, response) {
                let results = $.ui.autocomplete.filter(availableItemDesc, request.term);
                response(results.slice(0,300));
            },
            change: function(event, ui) { // Autofill desc when change event happens to the part_number field 
                indicateLoading("item-desc");
                let itemDesc;
                if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                    itemDesc = $itemDescInput.val();
                } else {
                    itemDesc = ui.item.label.toUpperCase();
                }
                let locationData = getLocation(itemDesc, "item-desc");
                setFields(locationData);
            },
            select: function(event , ui) { // Autofill desc when select event happens to the part_number field 
                indicateLoading();
                let itemDesc = ui.item.label.toUpperCase(); // Make sure the part_number field is uppercase
                let locationData = getLocation(itemDesc, "item-desc");
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
$itemDescInput.focus(function(){
    $animation.hide();
});