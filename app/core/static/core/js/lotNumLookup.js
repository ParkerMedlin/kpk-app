//var caching
let availableItemCodes;
let availableItemDesc;
let $itemCodeInput = $("#id_item_code");
let $itemDescriptionInput = $("#id_item_description");
let $searchLink = $("#lotNumSearchLink");
let $warningParagraph = $("#warningParagraph");
let $animation = $(".animation");


function getAllItemCodeAndDesc(){
    $.getJSON('/core/getBOMfields/?restriction=blends-only', function(data) {
        billOfMaterialsFields = data;
        }).then(function(billOfMaterialsFields) {
            availableItemCodes = billOfMaterialsFields['item_codes'];
            availableItemDesc = billOfMaterialsFields['item_descriptions'];
    });
}

function getItemInfo(lookupValue, lookupType){
    let itemData;
    let jsonURL;
    if (lookupType=="item-code"){
        jsonURL = `/core/infofromitemcode_request/?item=${lookupValue}`
    } else if (lookupType=="item-desc"){
        jsonURL = `/core/infofromitemdesc_request/?item=${lookupValue}`
    }
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
        $searchLink.hide();
    }).always(function() {
        $animation.toggle();
        $itemCodeInput.removeClass('loading');
        $itemDescriptionInput.removeClass('loading');
    });
    return itemData;
}

function indicateLoading(whichField) {
    if (whichField=="item-code") {
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
    $searchLink.attr("href", `/core/reports/Lot-Numbers/${itemData.item_code}`);
}

try { 
    $( function() {    
        getAllItemCodeAndDesc();

        // ===============  Item Number Search  ==============
        $itemCodeInput.autocomplete({
            minLength: 2,
            autoFocus: true,
            source: function (request, response) {
                let results = $.ui.autocomplete.filter(availableItemCodes, request.term);
                response(results.slice(0,10));
            },
            change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                indicateLoading("item-code");
                let itemCode;
                if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                    itemCode = $itemCodeInput.val();
                } else {
                    itemCode = ui.item.label.toUpperCase();
                }
                console.log(itemCode);
                let itemData = getItemInfo(itemCode, "item-code");
                console.log(itemData);
                setFields(itemData);
            },
            select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                indicateLoading("item-code");
                let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                console.log(itemCode);
                let itemData = getItemInfo(itemCode, "item-code");
                console.log(itemData);
                setFields(itemData);
            },
        });
        
        //   ===============  Description Search  ===============
        $itemDescriptionInput.autocomplete({ // Sets up a dropdown for the item_description field 
            source: function (request, response) {
                let results = $.ui.autocomplete.filter(availableItemDesc, request.term);
                response(results.slice(0,300));
            },
            change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                indicateLoading("item-desc");
                let itemDesc;
                if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                    itemDesc = $itemDescriptionInput.val();
                } else {
                    itemDesc = ui.item.label.toUpperCase();
                }
                itemData = getItemInfo(itemDesc, "item-desc");
                setFields(itemData);
            },
            select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                indicateLoading("item-desc");
                let itemDesc = ui.item.label.toUpperCase();
                itemData = getItemInfo(itemDesc, "item-desc");
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
    $searchLink.show();
});
$itemDescriptionInput.focus(function(){
    $animation.hide();
    $warningParagraph.hide();
    $searchLink.show();
});