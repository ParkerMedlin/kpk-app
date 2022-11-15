try {
    $( function() {
        let availableItemCodes;
        let availableItemDesc;
        let $itemPartNumInput = $("#id_part_number");
        let $itemDescInput = $("#id_description");
        let $animation = $(".animation");

        $.getJSON('/core/getblendBOMfields/', function(data) {
            blendBOMFields = data;
            }).then(function(blendBOMFields) {
                availableItemCodes = blendBOMFields['itemcodes'];
                availableItemDesc = blendBOMFields['itemcodedescs'];
        });

        // ===============  Item Number Search  ===============
        $itemPartNumInput.autocomplete({ // Sets up a dropdown for the part number field 
            minLength: 2,
            autoFocus: true,
            source: function (request, response) {
                let results = $.ui.autocomplete.filter(availableItemCodes, request.term);
                response(results.slice(0,10));
            },
            change: function( event, ui ) { // Autofill desc when change event happens to the part_number field 
                $itemDescInput.val("");
                $('#id_quantity').text("");
                $animation.toggle();
                $itemPartNumInput.addClass('loading');
                $itemDescInput.addClass('loading');
                var item = ui.item.label.toUpperCase() // Make sure the part_number field is uppercase
                $.getJSON('iteminfo_request/',{item:item}, // send json request with part number in request url
                    function(data) {
                        console.log("change")
                        console.log(data)
                        $itemDescInput.val(data.reqItemDesc); // Update desc value
                        $('#id_quantity').text(parseFloat(data.reqQty) + " " + data.standardUOM);
                        return;
                })
                    .fail(function() { // err handle
                        console.log("Part Number field is blank or not found");
                        $('#id_description').text("uhhh");
                        $('#id_quantity').text("Part Number field is blank or not found");
                    })
                    .always(function() {
                        $animation.toggle();
                        $itemPartNumInput.removeClass('loading');
                        $itemDescInput.removeClass('loading');
                    })
            },
            select: function( event , ui ) { // Autofill desc when select event happens to the part_number field 
                $itemDescInput.val("");
                $('#id_quantity').text("");
                $animation.toggle();
                $itemPartNumInput.addClass('loading');
                $itemDescInput.addClass('loading');
                var item = ui.item.label.toUpperCase() // Make sure the part_number field is uppercase
                $.getJSON('iteminfo_request/',{item:item}, // send json request with part number in request url
                    function(data) {
                        console.log("select")
                        console.log(data)
                        $itemDescInput.val(data.reqItemDesc); // Update desc value
                        $('#id_quantity').text(parseFloat(data.reqQty) + " " + data.standardUOM);
                        return;
                    })
                    .fail(function() { // err handle
                        console.log("Part Number field is blank or not found");
                        $('#id_description').text("uhhh");
                        $('#id_quantity').text("Part Number field is blank or not found");
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
                $('#id_quantity').text("");
                $animation.toggle();
                try { var item = ui.item.label;
                } catch {
                    var item = $itemDescInput.val();
                }
                $.getJSON('iteminfo_fromdesc_request/',{item:item}, // send json request with description in request url
                    function(data) {
                        try {
                        console.log("change")
                        console.log(data)
                        $itemPartNumInput.val(data.reqItemCode); // Update part number value
                        $('#id_quantity').text(parseFloat(data.reqQty) + " " + data.standardUOM);
                        return;
                        } catch {
                            console.log("Description field is blank or not found1");
                            $animation.toggle();
                            $itemPartNumInput.removeClass('loading');
                            $itemDescInput.removeClass('loading');
                            $('#id_quantity').text("Item not found");
                        }
                })
                .fail(function() { // err handle
                    console.log("Description field is blank or not found2");
                    $('#id_quantity').text("Item not found");
                })
                .always(function() {
                    $animation.toggle();
                    $itemPartNumInput.removeClass('loading');
                    $itemDescInput.removeClass('loading');
                })
            },
            select: function( event , ui ) { // Autofill desc when select event happens to the part_number field 
                $itemPartNumInput.val("");
                $('#id_quantity').text("");
                $animation.toggle();
                $itemPartNumInput.addClass('loading');
                $itemDescInput.addClass('loading');
                var item = ui.item.label
                $.getJSON('iteminfo_fromdesc_request/',{item:item}, // send json request with description in request url
                    function(data) {
                        console.log("change")
                        console.log(data)
                        $itemPartNumInput.val(data.reqItemCode); // Update part number value
                        $('#id_quantity').text(parseFloat(data.reqQty) + " " + data.standardUOM);
                        return;
                    })
                    .fail(function() { // err handle
                        console.log("Part Number field is blank or not found");
                        $('#id_description').text("uhhh");
                        $('#id_quantity').text("Part Number field is blank or not found");
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