//var caching
let availableItemCodes;
let availableItemDescriptions;
let $itemCodeInput = $("#id_lotNumModal-item_code");
let $itemDescriptionInput = $("#id_lotNumModal-item_description");
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
    let encodedList = $("#encodedListDiv").attr("encoded-list");
    let encodedItemCode = btoa(JSON.stringify(itemData.item_code));

    if($("#addCountLink").length){
        $("#addCountLink").prop('href', `/core/countlist/add/${encodedItemCode}/${encodedList}`);
    }
}

