try {
    $( function() {
        let availableItemCodes;
        let availableItemDesc;
        let $itemItemCodeInput = $("#id_item_code");
        let $itemDescriptionInput = $("#id_item_description");
        let $animation = $(".animation");

        $.getJSON('/core/getBOMfields/', function(data) {
            blendBOMFields = data;
            }).then(function(blendBOMFields) {
                availableItemCodes = blendBOMFields['item_codes'];
                availableItemDesc = blendBOMFields['item_descriptions'];
        });

        // ===============  Item Number Search  ===============
        $itemItemCodeInput.autocomplete({ // Sets up a dropdown for the part number field 
            minLength: 2,
            autoFocus: true,
            source: function (request, response) {
                let results = $.ui.autocomplete.filter(availableItemCodes, request.term);
                response(results.slice(0,10));
            },
            change: function( event, ui ) { // Autofill desc when change event happens to the item_code field 
                $itemDescriptionInput.val("");
                $('#id_quantity').text("");
                $animation.toggle();
                $itemItemCodeInput.addClass('loading');
                $itemDescriptionInput.addClass('loading');
                var item = ui.item.label.toUpperCase() // Make sure the item_code field is uppercase
                $.getJSON('iteminfo_request/',{item:item}, // send json request with part number in request url
                    function(data) {
                        console.log("change")
                        console.log(data)
                        $itemDescriptionInput.val(data.reqItemDesc); // Update desc value
                        $('#id_quantity').text(parseFloat(data.reqQty) + " " + data.standardUOM);
                        return;
                })
                    .fail(function() { // err handle
                        console.log("Part Number field is blank or not found");
                        $('#id_item_description').text("uhhh");
                        $('#id_quantity').text("Part Number field is blank or not found");
                    })
                    .always(function() {
                        $animation.toggle();
                        $itemItemCodeInput.removeClass('loading');
                        $itemDescriptionInput.removeClass('loading');
                    })
            },
            select: function( event , ui ) { // Autofill desc when select event happens to the item_code field 
                $itemDescriptionInput.val("");
                $('#id_quantity').text("");
                $animation.toggle();
                $itemItemCodeInput.addClass('loading');
                $itemDescriptionInput.addClass('loading');
                var item = ui.item.label.toUpperCase() // Make sure the item_code field is uppercase
                $.getJSON('iteminfo_request/',{item:item}, // send json request with part number in request url
                    function(data) {
                        console.log("select")
                        console.log(data)
                        $itemDescriptionInput.val(data.reqItemDesc); // Update desc value
                        $('#id_quantity').text(parseFloat(data.reqQty) + " " + data.standardUOM);
                        return;
                    })
                    .fail(function() { // err handle
                        console.log("Part Number field is blank or not found");
                        $('#id_item_description').text("uhhh");
                        $('#id_quantity').text("Part Number field is blank or not found");
                    })
                    .always(function() {
                        $animation.toggle();
                        $itemItemCodeInput.removeClass('loading');
                        $itemDescriptionInput.removeClass('loading');
                    })
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
            change: function( event, ui ) { // Autofill desc when change event happens to the item_code field 
                $itemItemCodeInput.val("");
                $itemItemCodeInput.addClass('loading');
                $itemDescriptionInput.addClass('loading');
                $('#id_quantity').text("");
                $animation.toggle();
                try { var item = ui.item.label;
                } catch {
                    var item = $itemDescriptionInput.val();
                }
                $.getJSON('iteminfo_fromdesc_request/',{item:item}, // send json request with description in request url
                    function(data) {
                        try {
                        console.log("change")
                        console.log(data)
                        $itemItemCodeInput.val(data.reqItemCode); // Update part number value
                        $('#id_quantity').text(parseFloat(data.reqQty) + " " + data.standardUOM);
                        return;
                        } catch {
                            console.log("Description field is blank or not found1");
                            $animation.toggle();
                            $itemItemCodeInput.removeClass('loading');
                            $itemDescriptionInput.removeClass('loading');
                            $('#id_quantity').text("Item not found");
                        }
                })
                .fail(function() { // err handle
                    console.log("Description field is blank or not found2");
                    $('#id_quantity').text("Item not found");
                })
                .always(function() {
                    $animation.toggle();
                    $itemItemCodeInput.removeClass('loading');
                    $itemDescriptionInput.removeClass('loading');
                })
            },
            select: function( event , ui ) { // Autofill desc when select event happens to the item_code field 
                $itemItemCodeInput.val("");
                $('#id_quantity').text("");
                $animation.toggle();
                $itemItemCodeInput.addClass('loading');
                $itemDescriptionInput.addClass('loading');
                var item = ui.item.label
                $.getJSON('iteminfo_fromdesc_request/',{item:item}, // send json request with description in request url
                    function(data) {
                        console.log("change")
                        console.log(data)
                        $itemItemCodeInput.val(data.reqItemCode); // Update part number value
                        $('#id_quantity').text(parseFloat(data.reqQty) + " " + data.standardUOM);
                        return;
                    })
                    .fail(function() { // err handle
                        console.log("Part Number field is blank or not found");
                        $('#id_item_description').text("uhhh");
                        $('#id_quantity').text("Part Number field is blank or not found");
                    })
                    .always(function() {
                        $animation.toggle();
                        $itemItemCodeInput.removeClass('loading');
                        $itemDescriptionInput.removeClass('loading');
                    })
            },
        });
    });
} catch (pnError) {
    console.log(pnError)
};