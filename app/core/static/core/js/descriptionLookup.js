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
                let item = ui.item.label.toUpperCase(); // Make sure the part_number field is uppercase
                $.getJSON('/core/itemcodedesc_request/',{item:item}, // send json request with part number in request url
                    function(data) {
                        $itemDescInput.val(data); // Update desc value
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
                let item = ui.item.label.toUpperCase(); // Make sure the part_number field is uppercase
                $.getJSON('/core/itemcodedesc_request/',{item:item}, // send json request with part number in request url
                    function(data) {
                        $itemDescInput.val(data); // Update desc value
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
                $animation.toggle();
                let results = $.ui.autocomplete.filter(availableItemDesc, request.term);
                response(results.slice(0,300));
            },
            change: function( event, ui ) { // Autofill desc when change event happens to the part_number field 
                $itemPartNumInput.val("");
                var item = ui.item.label.toUpperCase();
                $.getJSON('/core/itemcode_request/',{item:item}, // send json request with desc in request url
                    function(data) {
                        $itemPartNumInput.val(data); // Update partnumber value
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
                $animation.toggle();
                var item = ui.item.label.toUpperCase();
                $.getJSON('/core/itemcode_request/',{item:item}, // send json request with description in request url
                    function(data) {
                        $itemPartNumInput.val(data); // Update part_number value
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