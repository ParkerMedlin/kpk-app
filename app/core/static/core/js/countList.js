$(document).ready(function(){
    $('input[type="number"]').each(function(){
        $(this).attr("value", Math.round($(this).attr("value")));
    });
});

let expected_quantity;
let counted_quantity;
let variance;

$('input[id*=counted_quantity]').blur(function(){
    expected_quantity = $(this).parent().prev('td').children().first().val();
    console.log("expected qty: " + expected_quantity);
    counted_quantity = $(this).val();
    console.log("counted qty: " + counted_quantity);
    variance = counted_quantity - expected_quantity;
    console.log("variance: " + variance);
    $(this).parent().next('td').next('td').children().attr('value', variance);
});

$(document).ready(function(){
    $('input[type=hidden]').each(function() {
        $(this).parent('td').attr('style', "display:none;");
    });

    let fullEncodedList = $("#encodedListDiv").attr("data-encoded-list");
    let thisRowIdEncoded;
    let thisRowId;

    $('.discardButtonCell').each(function(){
        thisRowID = $(this).prev().children().first().attr("value");
        thisRowIdEncoded = btoa(thisRowID)
        $(this).children().first().attr("href", `/core/delete_countrecord/countlist/${thisRowIdEncoded}/${fullEncodedList}`)
    });

});


// =============== ITEM LOOKUP =============== //
try { 
    $( function() {    
        //var caching
        let availableItemCodes;
        let availableItemDesc;
        let $itemPartNumInput = $("#id_part_number");
        let $itemDescInput = $("#id_description");
        let $animation = $(".animation");

        // Get itemcodes and descs 
        $.getJSON('/core/getblendBOMfields/', function(data) {
            blendBOMFields = data;
            }).then(function(blendBOMFields) {
                availableItemCodes = blendBOMFields['itemcodes'];
                availableItemDesc = blendBOMFields['itemcodedescs'];
        });


        // ===============  Item Number Search  ==============
        $itemPartNumInput.autocomplete({
            minLength: 2,
            autoFocus: true,
            source: function (request, response) {
                let results = $.ui.autocomplete.filter(availableItemCodes, request.term);
                response(results.slice(0,10));
            },
            change: function( event, ui ) { // Autofill desc when change event happens to the part_number field 
                $itemDescInput.val("");
                $animation.toggle();
                $itemPartNumInput.addClass('loading');
                $itemDescInput.addClass('loading');
                let item = ui.item.label.toUpperCase() // Make sure the part_number field is uppercase
                $.getJSON('/core/itemcodedesc_request/',{item:item}, // send json request with part number in request url
                    function(data) {
                        $itemDescInput.val(data); // Update desc value
                        currentURL = window.location.href;
                        currentEncodedList = currentURL.split('display/')[1];
                        partNumber = btoa(item);
                        console.log('test');
                        $('#addCountLink').attr('href', '/core/countlist/add/'+partNumber+'/'+currentEncodedList);
                })
                    .fail(function() { // err handle
                        console.log("Part Number field is blank or not found");
                        $itemDescInput.val("");
                    })
                    .always(function() {
                        $animation.toggle();
                        $itemPartNumInput.removeClass('loading');
                        $itemDescInput.removeClass('loading');
                    })
            },
            select: function( event , ui ) { // Autofill desc when select event happens to the part_number field 
                $itemDescInput.val("");
                $animation.toggle();
                $itemPartNumInput.addClass('loading');
                $itemDescInput.addClass('loading');
                let item = ui.item.label.toUpperCase() // Make sure the part_number field is uppercase
                $.getJSON('/core/itemcodedesc_request/',{item:item}, // send json request with part number in request url
                    function(data) {
                        $itemDescInput.val(data); // Update desc value
                        currentURL = window.location.href;
                        currentEncodedList = currentURL.split('display/')[1];
                        partNumber = btoa(item);
                        console.log('test');
                        $('#addCountLink').attr('href', '/core/countlist/add/'+partNumber+'/'+currentEncodedList);
                })
                    .fail(function() { // err handle
                        console.log("Part Number field is blank or not found");
                        $itemDescInput.val("");
                    })
                    .always(function() {
                        $animation.toggle();
                        $itemPartNumInput.removeClass('loading');
                        $itemDescInput.removeClass('loading');
                    })
            },
        });
        
        //   ===============  Description Search  ===============
        $itemDescInput.autocomplete({ // Sets up a dropdown for the description field 
            source: function (request, response) {
                console.log(availableItemDesc);
                console.log(request.term);
                let results = $.ui.autocomplete.filter(availableItemDesc, request.term);
                response(results.slice(0,300));
            },
            change: function( event, ui ) { // Autofill desc when change event happens to the part_number field 
                $itemPartNumInput.val("");
                var item = $itemDescInput.val();
                $.getJSON('/core/itemcode_request/',{item:item}, // send json request with desc in request url
                    function(data) {
                        $itemPartNumInput.val(data); // Update partnumber value
                        currentURL = window.location.href;
                        currentEncodedList = currentURL.split('display/')[1];
                        partNumber = btoa(data);
                        console.log('test');
                        $('#addCountLink').attr('href', '/core/countlist/add/'+partNumber+'/'+currentEncodedList);
                })
                    .fail(function() { // err handle
                        console.log("Part description field is blank or not found");
                        $itemPartNumInput.val("");
                    })
                    .always(function() {
                        $animation.toggle();
                        $itemPartNumInput.removeClass('loading');
                        $itemDescInput.removeClass('loading');
                    })
            },
            select: function( event , ui ) { // Autofill desc when select event happens to the part_number field 
                $itemPartNumInput.val("");
                var item = $itemDescInput.val();
                $.getJSON('/core/itemcode_request/',{item:item}, // send json request with description in request url
                    function(data) {
                        $itemPartNumInput.val(data); // Update part_number value
                        currentURL = window.location.href;
                        currentEncodedList = currentURL.split('display/')[1];
                        partNumber = btoa(data);
                        console.log('test');
                        $('#addCountLink').attr('href', '/core/countlist/add/'+partNumber+'/'+currentEncodedList);
                })
                    .fail(function() { // err handle
                        console.log("Part Number field is blank or not found");
                        $itemPartNumInput.val("");
                    })
                    .always(function() {
                        $animation.toggle();
                        $itemPartNumInput.removeClass('loading');
                        $itemDescInput.removeClass('loading');
                    })
            },
        });
    });
} catch (pnError) {
    console.log(pnError)
};
