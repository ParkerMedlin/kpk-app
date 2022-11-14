try {
            
    $( function autocompleteSetup() {    
        let availableItemCodes;
        let availableItemDesc;

        $.getJSON('/core/getblendBOMfields/', function(data) {
            blendBOMFields = data;
            }).then(function(blendBOMFields) {
                availableItemCodes = blendBOMFields['itemcodes'];
                availableItemDesc = blendBOMFields['itemcodedescs'];
        });

        let $partNumber = $("#id_part_number");
        let $itemDescription = $("#id_description");

        $partNumber.autocomplete({
            source: function (request, response) {
                let results = $.ui.autocomplete.filter(availableItemCodes, request.term);
                response(results.slice(0,10));
            },
            change: function( event, ui ) { // Autofill desc when change event happens to the part_number field 
                var item = $partNumber.val().toUpperCase() // Make sure the part_number field is uppercase
                $.getJSON('/core/itemcodedesc_request/',{item:item}, // send json request with part number in request url
                    function(data) {
                        $itemDescription.val(data); // Update desc value
                })
                    .fail(function() { // err handle
                        console.log("Part Number field is blank or not found");
                        $itemDescription.val("");
                    })
            },
            select: function( event , ui ) { // Autofill desc when select event happens to the part_number field 
                var item = $partNumber.val().toUpperCase() // Make sure the part_number field is uppercase
                $.getJSON('/core/itemcodedesc_request/',{item:item}, // send json request with part number in request url
                    function(data) {
                        $itemDescription.val(data); // Update desc value
                })
                    .fail(function() { // err handle
                        console.log("Part Number field is blank or not found");
                        $itemDescription.val("");
                    })
            },
        });
        
        $itemDescription.autocomplete({ // Sets up a dropdown for the description field 
            source: function (request, response) {
                console.log(availableItemDesc);
                console.log(request.term);
                let results = $.ui.autocomplete.filter(availableItemDesc, request.term);
                response(results.slice(0,300));
            },
            change: function( event, ui ) { // Autofill desc when change event happens to the part_number field 
                $partNumber.val("");
                var item = $itemDescription.val();
                $.getJSON('/core/itemcode_request/',{item:item}, // send json request with desc in request url
                    function(data) {
                        $partNumber.val(data); // Update partnumber value
                })
                    .fail(function() { // err handle
                        console.log("Part description field is blank or not found");
                        $partNumber.val("");
                    })
            },
            select: function( event , ui ) { // Autofill desc when select event happens to the part_number field 
                $partNumber.val("");
                var item = $itemDescription.val();
                $.getJSON('/core/itemcode_request/',{item:item}, // send json request with description in request url
                    function(data) {
                        $partNumber.val(data); // Update part_number value
                })
                    .fail(function() { // err handle
                        console.log("Part Number field is blank or not found");
                        $partNumber.val("");
                    })
            },
        });

        
    });
} catch (pnError) {
    console.log(pnError)
};