//var caching
let availableItemCodes;
let availableItemDesc;
const $itemCodeInput = $("#id_item_code");
const $itemDescriptionInput = $("#id_item_description");
const $reportTypeSelect = $("#id_which_report")
const $reportLink = $("#reportLink");
const $warningParagraph = $("#warningParagraph");
const $animation = $(".animation");
const $reportOptions = $(".reportOption");


function getAllItemCodeAndDesc(){
    $.getJSON('/core/getBOMfields', function(data) {
        BOMFields = data;
        }).then(function(BOMFields) {
            availableItemCodes = BOMFields['item_codes'];
            availableItemDesc = BOMFields['item_descriptions'];
    });
}

function getItemInfo(lookupValue, lookupType){
    let itemData;
    let jsonURL = `/prodverse/item_info_request/?item=${lookupValue}&lookupType=${lookupType}`
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
        $reportLink.hide();
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
    let itemCode = itemData.item_code
    $reportLink.prop("data-itemcode", itemCode);
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
                let reportType = $reportTypeSelect.val().replaceAll(' ', '-');
                $reportLink.prop('href', `${reportType}/${itemCode}`);
                $reportLink.show();
            },
            select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                indicateLoading("itemCode");
                let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                console.log(itemCode);
                let itemData = getItemInfo(itemCode, "itemCode");
                console.log(itemData);
                setFields(itemData);
                let reportType = $reportTypeSelect.val().replaceAll(' ', '-');
                $reportLink.prop('href', `${reportType}/${itemCode}`);
                $reportLink.show();
            },
        });
        
        //   ===============  Description Search  ===============
        $itemDescriptionInput.autocomplete({ // Sets up a dropdown for the description field 
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
                let reportType = $reportTypeSelect.val().replaceAll(' ', '-');
                let itemCode = $itemCodeInput.val();
                $reportLink.prop('href', `${reportType}/${itemCode}`);
                $reportLink.show();
            },
            select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                indicateLoading("itemDescription");
                let itemDesc = ui.item.label.toUpperCase();
                itemData = getItemInfo(itemDesc, "itemDescription");
                setFields(itemData);
                let reportType = $reportTypeSelect.val().replaceAll(' ', '-');
                let itemCode = $itemCodeInput.val();
                $reportLink.prop('href', `${reportType}/${itemCode}`);
                $reportLink.show();
            },
        });
    });
} catch (pnError) {
    console.log(pnError)
};


$(document).ready(function(){
    $reportTypeSelect.change(function(event) {
        let reportType = $reportTypeSelect.val().replaceAll(' ', '-');
        if ($itemCodeInput.val()!="" && $itemDescriptionInput.val()!="" | reportType=="Startron-Runs"){
            $reportLink.show();
        };
        let itemCode = $itemCodeInput.val();
        if (reportType=="Startron-Runs") { 
            $("#itemCodeRow").prop("style", "display: none;");
            $("#itemDescriptionRow").prop("style", "display: none;");
            itemCode="n-a"
            $reportLink.show();
        }else{
            $("#itemCodeRow").show();
            $("#itemDescriptionRow").show();
        };
        console.log(`${reportType}/${itemCode}`);
        $reportLink.prop('href', `${reportType}/${itemCode}`);
    });

});