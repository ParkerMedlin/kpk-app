//var caching
let availableItemCodes;
let availableItemDesc;
let $itemPartNumInput = $("#id_part_number");
let $itemDescInput = $("#id_description");
let $itemLocation = $('#id_location');
let $itemQty = $('#id_quantity')
let $animation = $(".animation");

function getAllItemCodeAndDesc(){
    $.getJSON('/core/getblendBOMfields/', function(data) {
        blendBOMFields = data;
        }).then(function(blendBOMFields) {
            availableItemCodes = blendBOMFields['itemcodes'];
            availableItemDesc = blendBOMFields['itemcodedescs'];
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
        console.log("Part Number field is blank or not found.");
        $itemLocation.text("Part Number field is blank or not found.");
    }).always(function() {
        $animation.toggle();
        $itemPartNumInput.removeClass('loading');
        $itemDescInput.removeClass('loading');
    });
    return locationData;
}

function indicateLoading() {
    $itemDescInput.val("");
    $itemPartNumInput.val("")
    $itemLocation.text("");
    $itemQty.text("");
    $animation.toggle();
    $itemPartNumInput.addClass('loading');
    $itemDescInput.addClass('loading');
}

function setFields(locationData){
    $itemPartNumInput.val(locationData.itemcode);
    $itemDescInput.val(locationData.description);
    $itemLocation.text(locationData.general_location + ", " + locationData.specific_location);
    $itemQty.text(locationData.qtyonhand + " " + locationData.standard_uom + " on hand.");
}

try {
    $( function() {
        getAllItemCodeAndDesc();
        
        // ===============  Item Number Search  ==============
        $itemPartNumInput.autocomplete({ // Sets up a dropdown for the part number field 
            minLength: 2,
            autoFocus: true,
            source: function (request, response) {
                let results = $.ui.autocomplete.filter(availableItemCodes, request.term);
                response(results.slice(0,10));
            },
            change: function( event, ui ) { // Autofill desc when change event happens to the part_number field 
                indicateLoading();
                let itemCode = ui.item.label.toUpperCase(); // Make sure the part_number field is uppercase
                let locationData = getLocation(itemCode, "item-code");
                setFields(locationData);
            },
            select: function( event , ui ) { // Autofill desc when select event happens to the part_number field 
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
            change: function( event, ui ) { // Autofill desc when change event happens to the part_number field 
                indicateLoading();
                let itemDesc = ui.item.label.toUpperCase(); // Make sure the part_number field is uppercase
                let locationData = getLocation(itemDesc, "item-desc");
                setFields(locationData);
            },
            select: function( event , ui ) { // Autofill desc when select event happens to the part_number field 
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