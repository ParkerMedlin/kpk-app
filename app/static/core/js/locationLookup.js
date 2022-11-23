try {
    $( function() {
        //var caching
        let availableItemCodes;
        let availableItemDesc;
        let $itemPartNumInput = $("#id_part_number");
        let $itemDescInput = $("#id_description");
        let $idLocation = $('#id_location');
        let $idQty = $('#id_quantity')
        let $animation = $(".animation");

        $.getJSON('/core/getblendBOMfields/', function(data) {
            blendBOMFields = data;
            }).then(function(blendBOMFields) {
                availableItemCodes = blendBOMFields['itemcodes'];
                availableItemDesc = blendBOMFields['itemcodedescs'];
        });

        // ===============  Item Number Search  ==============
        $itemPartNumInput.autocomplete({ // Sets up a dropdown for the part number field 
            minLength: 2,
            autoFocus: true,
            source: function (request, response) {
                let results = $.ui.autocomplete.filter(availableItemCodes, request.term);
                response(results.slice(0,10));
            },
            change: function( event, ui ) { // Autofill desc when change event happens to the part_number field 
                $itemDescInput.val("");
                $idLocation.text("");
                $idQty.text("");
                $animation.toggle();
                $itemPartNumInput.addClass('loading');
                $itemDescInput.addClass('loading');
                var item = ui.item.label.toUpperCase(); // Make sure the part_number field is uppercase
                $.getJSON('/core/chemloc_request_itemcode/',{item:item}, // send json request with part number in request url
                    function(data) {
                        console.log("change");
                        console.log(data);
                        $itemDescInput.val(data.description); // Update desc value
                        $idLocation.text(data.general_location + ", " + data.specific_location);
                        $idQty.text(data.qtyonhand + " " + data.standard_uom + " on hand.");
                        return;
                })
                    .fail(function() { // err handle
                        console.log("Part Number field is blank or not found.");
                        $idLocation.text("Part Number field is blank or not found.");
                    })
                    .always(function() {
                        $animation.toggle();
                        $itemPartNumInput.removeClass('loading');
                        $itemDescInput.removeClass('loading');
                    })
            },
            select: function( event , ui ) { // Autofill desc when select event happens to the part_number field 
                $itemDescInput.val("");
                $idLocation.text("");
                $idQty.text("");
                $animation.toggle();
                $itemPartNumInput.addClass('loading');
                $itemDescInput.addClass('loading');
                var item = ui.item.label.toUpperCase() // Make sure the part_number field is uppercase
                $.getJSON('/core/chemloc_request_itemcode/',{item:item}, // send json request with part number in request url
                    function(data) {
                        console.log("select")
                        console.log(data)
                        $itemDescInput.val(data.description); // Update desc value
                        $idLocation.text(data.general_location + ", " + data.specific_location);
                        $idQty.text(data.qtyonhand + " " + data.standard_uom + " on hand.");
                        return;
                    })
                    .fail(function() { // err handle
                        console.log("Part Number field is blank or not found.");
                        $idLocation.text("Part Number field is blank or not found.");
                    })
                    .always(function() {
                        $animation.toggle();
                        $itemPartNumInput.removeClass('loading');
                        $itemDescInput.removeClass('loading');
                    })
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
            change: function( event, ui ) { // Autofill desc when change event happens to the part_number field 
                $itemPartNumInput.val("");
                $itemPartNumInput.addClass('loading');
                $itemDescInput.addClass('loading');
                $idLocation.text("");
                $idQty.text("");
                $animation.toggle();
                let item = $itemDescInput.val();
                $.getJSON('/core/chemloc_request_desc/',{item:item}, // send json request with description in request url
                    function(data) {
                        try {
                        console.log("change")
                        console.log(data)
                        $itemPartNumInput.val(data.itemcode); // Update part number value
                        $idLocation.text(data.general_location + ", " + data.specific_location);
                        $idQty.text(data.qtyonhand + " " + data.standard_uom + " on hand.");
                        return;
                        } catch {
                            $animation.toggle();
                            $itemPartNumInput.removeClass('loading');
                            $itemDescInput.removeClass('loading');
                            $idLocation.text(data.general_location + ", " + data.specific_location);
                            $idQty.text(data.qtyonhand + " " + data.standard_uom + " on hand.");
                        }
                })
                .fail(function() { // err handle
                    console.log("Description field is blank or not found.");
                    $idLocation.text("Item not found");
                    $idQty.text("Item not found");
                })
                .always(function() {
                    $animation.toggle();
                    $itemPartNumInput.removeClass('loading');
                    $itemDescInput.removeClass('loading');
                })
            },
            select: function( event , ui ) { // Autofill desc when select event happens to the part_number field 
                $itemPartNumInput.val("");
                $idLocation.text("");
                $idQty.text("");
                $animation.toggle();
                $itemPartNumInput.addClass('loading');
                $itemDescInput.addClass('loading');
                var item = ui.item.label
                $.getJSON('/core/chemloc_request_desc/',{item:item}, // send json request with description in request url
                    function(data) {
                        console.log("change")
                        console.log(data)
                        $itemPartNumInput.val(data.itemcode); // Update part number value
                        $idLocation.text(data.general_location + ", " + data.specific_location);
                        console.log(data.qtyonhand + " " + data.standard_uom + " on hand.");
                        $idQty.text(data.qtyonhand + " " + data.standard_uom + " on hand.");
                        return;
                    })
                    .fail(function() { // err handle
                        console.log("Description field is blank or not found.");
                        $idLocation.text("Item not found");
                        $idQty.text("Item not found");
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