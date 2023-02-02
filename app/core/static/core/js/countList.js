let expected_quantity;
let counted_quantity;
let variance;
const $countedQuantityInputs = $('input[id*="counted_quantity"]');
const $allInputs = $('input');
const $saveCountsButton = $('#saveCountsButton');


let missedaCount = true;


$('input[id*=counted_quantity]').blur(function(){
    expected_quantity = $(this).parent().prev('td').children().first().val();
    console.log("expected qty: " + expected_quantity);
    counted_quantity = $(this).val();
    console.log("counted qty: " + counted_quantity);
    variance = counted_quantity - expected_quantity;
    console.log("variance: " + variance);
    $(this).parent().next('td').next('td').children().attr('value', variance.toFixed(4));

});

$(document).ready(function(){
    $('input[type="number"]').each(function(){
        $(this).attr("value", parseFloat(($(this).attr("value"))).toFixed(4));
    });

    $('input[name*="counted_quantity"]').each(function(){
        $(this).attr("value", Math.round($(this).attr("value")));
    });

    $('input[type=hidden]').each(function() {
        $(this).parent('td').attr('style', "display:none;");
    });

    $('input').each(function() {
        $(this).attr('tabindex', '-1');
    });

    $allInputs.each(function() {
        $(this).attr('readonly', true)
    });

    $countedQuantityInputs.each(function() {
        $(this).attr('tabindex', '0');
        $(this).removeAttr('readonly');
        $(this).on('focus', function() {
            $(this).addClass('entered')
            if ($(this).hasClass('missingCount')) {
                $(this).removeClass('missingCount');
            }
        });
    });

    $('#id_countListModal_item_code').removeAttr('readonly');
    $('#id_countListModal_item_description').removeAttr('readonly');
    
    $saveCountsButton.on('click', function(e){
        missedaCount = false;
        $countedQuantityInputs.each(function(e) {
            if (!($(this).hasClass('entered'))) {
                $(this).addClass('missingCount');
                missedaCount = true;
            }
            $(this).on('focus', function() {
                $(this).addClass('entered')
            });
        });
                
        if (missedaCount) {
            e.preventDefault();
            alert("Please fill in the missing counts.");
        }
        
    });

    $('table').keypress(
        function(event){
          if (event.which == '13') {
            event.preventDefault();
          }
      });

    let fullEncodedList = $("#encodedListDiv").attr("data-encoded-list");
    let thisRowIdEncoded;
    let thisRowID;

    $('.discardButtonCell').each(function(){
        thisRowID = $(this).prev().children().first().attr("value");
        thisRowIdEncoded = btoa(thisRowID)
        $(this).children().first().attr("href", `/core/delete_countrecord/countlist/${thisRowIdEncoded}/${fullEncodedList}`)
    });

    
    
});

//var caching
let availableItemCodes;
let availableItemDescriptions;
let $itemCodeInput = $("#id_countListModal_item_code");
let $itemDescriptionInput = $("#id_countListModal_item_description");
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