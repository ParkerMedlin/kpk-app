//var caching
let availableItemCodes;
let availableItemDesc;
let $itemCodeInput = $("#id_part_number");
let $itemDescInput = $("#id_description");
let $animation = $(".animation");

function getAllItemCodeAndDesc(){
    $.getJSON('/core/getblendBOMfields/', function(data) {
        blendBOMFields = data;
        }).then(function(blendBOMFields) {
            availableItemCodes = blendBOMFields['itemcodes'];
            availableItemDesc = blendBOMFields['itemcodedescs'];
    });
}

function getItemData(lookupValue, lookupType){
    let itemData;
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
            itemData = data;
        }
    }).fail(function() { // err handle
        console.log("Item not found. Check search terms and try again.");
    }).always(function() {
        $animation.toggle();
        $itemCodeInput.removeClass('loading');
        $itemDescInput.removeClass('loading');
    });
    return itemData;
}

function indicateLoading(whichField) {
    if (whichField=="item-code") {
        $itemDescInput.val("");
    } else {
        $itemCodeInput.val("");
    }
    $animation.toggle();
    $itemCodeInput.addClass('loading');
    $itemDescInput.addClass('loading');
}

function setFields(itemData){
    $itemCodeInput.val(itemData.itemcode);
    $itemDescInput.val(itemData.description);
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
                let itemData = getItemData(itemCode, "item-code");
                setFields(itemData);
            },
            select: function(event , ui) { // Autofill desc when select event happens to the part_number field 
                indicateLoading();
                let itemCode = ui.item.label.toUpperCase(); // Make sure the part_number field is uppercase
                let itemData = getItemData(itemCode, "item-code");
                setFields(itemData);
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
                let itemData = getItemData(itemDesc, "item-desc");
                setFields(itemData);
            },
            select: function(event , ui) { // Autofill desc when select event happens to the part_number field 
                indicateLoading();
                let itemDesc = ui.item.label.toUpperCase(); // Make sure the part_number field is uppercase
                let itemData = getItemData(itemDesc, "item-desc");
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
$itemDescInput.focus(function(){
    $animation.hide();
});