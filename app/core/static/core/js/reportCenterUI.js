//var caching
let availableItemCodes;
let availableItemDesc;
let $itemCodeInput = $("#id_part_number");
let $itemDescInput = $("#id_description");
let $reportLink = $("#reportLink");
let $warningParagraph = $("#warningParagraph");
let $animation = $(".animation");
let $reportOptions = $(".reportOption");


function getAllItemCodeAndDesc(){
    $.getJSON('/core/getblendBOMfields/?restriction=blends-only', function(data) {
        blendBOMFields = data;
        }).then(function(blendBOMFields) {
            availableItemCodes = blendBOMFields['itemcodes'];
            availableItemDesc = blendBOMFields['itemdescs'];
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
        $reportLink.hide();
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
    let itemCode = itemData.itemcode
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
            change: function(event, ui) { // Autofill desc when change event happens to the part_number field 
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
            select: function(event , ui) { // Autofill desc when select event happens to the part_number field 
                indicateLoading("item-code");
                let itemCode = ui.item.label.toUpperCase(); // Make sure the part_number field is uppercase
                console.log(itemCode);
                let itemData = getItemInfo(itemCode, "item-code");
                console.log(itemData);
                setFields(itemData);
            },
        });
        
        //   ===============  Description Search  ===============
        $itemDescInput.autocomplete({ // Sets up a dropdown for the description field 
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
                itemData = getItemInfo(itemDesc, "item-desc");
                setFields(itemData);
            },
            select: function(event , ui) { // Autofill desc when select event happens to the part_number field 
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


$(document).ready(function(){
    //let initialReportType = 
    //$reportLink.prop('href', `${reportType}/${itemCode}`);

    $("#id_which_report").change(function(event) {
        let itemCode = $reportLink.prop('data-itemcode');
        let reportType = $("#id_which_report").val().replace(' ', '-');
        console.log(`${reportType}/${itemCode}`);
        $reportLink.prop('href', `${reportType}/${itemCode}`);
    });

});