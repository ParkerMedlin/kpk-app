let availableItemCodes;
let availableItemDesc;
let $itemCodeInput = $("#id_item_code");
let $itemDescriptionInput = $("#id_item_description");
let $itemQuantity = $("#item_quantity");
let $animation = $(".animation");
let $warningParagraph = $("#warningParagraph");
let $itemQtyContainer = $("#itemQtyContainer");


function getAllItemCodeAndDesc(){
    $.getJSON('/prodverse/getBOMfields/', function(data) {
        prodBOMFields = data;
        }).then(function(prodBOMFields) {
            availableItemCodes = prodBOMFields['itemcodes'];
            availableItemDesc = prodBOMFields['itemcodedescs'];
    });
}

function getItemInfo(lookupValue, lookupType){
    let itemData;
    let jsonURL = `/prodverse/item_info_request/?item=${lookupValue}&lookupType=${lookupType}`;
    console.log(jsonURL);
    $.ajax({
        url: jsonURL,
        async: false,
        dataType: 'json',
        success: function(data) {
            itemData = data;
        }
    }).fail(function() { // err handle
        console.log("Search terms are invalid or results are not found");
        $warningParagraph.show();
        $itemQtyContainer.hide();
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
    $itemQuantity.text(parseFloat(itemData.qtyOnHand) + " " + itemData.standardUOM);
}

try {
    $( function() {

        getAllItemCodeAndDesc();

        // ===============  Item Number Search  ===============
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
                console.log(itemCode);
                let itemData = getItemInfo(itemCode, "itemCode");
                console.log(itemData);
                setFields(itemData);
            },
            select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                indicateLoading("itemCode");
                let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                console.log(itemCode);
                let itemData = getItemInfo(itemCode, "itemCode");
                console.log(itemData);
                setFields(itemData);
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
                itemData = getItemInfo(itemDesc, "itemDescription");
                setFields(itemData);
            },
            select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                indicateLoading("itemDescription");
                let itemDesc = ui.item.label.toUpperCase();
                itemData = getItemInfo(itemDesc, "itemDescription");
                setFields(itemData);
            },
        });
    });
} catch (pnError) {
    console.log(pnError)
};

$itemCodeInput.focus(function(){
    $animation.hide();
    $warningParagraph.hide();
    $itemQtyContainer.show();
});
$itemDescriptionInput.focus(function(){
    $animation.hide();
    $warningParagraph.hide();
    $itemQtyContainer.show();
});