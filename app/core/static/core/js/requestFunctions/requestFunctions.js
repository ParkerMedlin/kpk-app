export function getAllBOMFields(restriction){
    let allBOMFields;
    let jsonURL = `/core/get-BOM-fields/?restriction=${restriction}`;
    $.ajax({
        url: jsonURL,
        async: false,
        dataType: 'json',
        success: function(data) {
            allBOMFields = data;
        }
    }).fail(function() {
        console.log("BOM request not fulfilled.");
    });
    return allBOMFields;
};

export function getItemInfo(lookupValue, lookupType){
    let itemData;
    let encodedLookupValue = btoa(JSON.stringify(lookupValue));
    let jsonURL = `/core/item-info-request/?item=${encodedLookupValue}&lookup-type=${lookupType}`;
    $.ajax({
        url: jsonURL,
        async: false,
        dataType: 'json',
        success: function(data) {
            itemData = data;
        }
    }).fail(function() {
        console.log("Search terms are invalid or results are not found");
        $("#warningParagraph").show();
        $("#itemQtyContainer").hide();
    }).always(function() {
        $('.animation').toggle();
        $('#id_item_code').removeClass('loading');
        $('#id_item_description').removeClass('loading');
    });
    return itemData;
};

export function getLocation(lookupValue, lookupType){
    let locationData;
    let encodedLookupValue = btoa(JSON.stringify(lookupValue));
    let jsonURL = `/core/item-location-request/?item=${encodedLookupValue}&lookup-type=${lookupType}`;
    $.ajax({
        url: jsonURL,
        async: false,
        dataType: 'json',
        success: function(data) {
            locationData = data;
        }
    }).fail(function() {
        console.log("Item not found. Check search terms and try again.");
        $('#id_location').text("Item not found. Check search terms and try again.");
        $('#id_quantity').text("Item not found. Check search terms and try again.");
    }).always(function() {
        $('.animation').toggle();
        $('#id_item_code').removeClass('loading');
        $('#id_item_description').removeClass('loading');
    });
    return locationData;
};

export function getMaxProducibleQuantity(itemLookupValue, componentItemLookupValue, lookupType){
    let encodedItemLookupValue = btoa(JSON.stringify(itemLookupValue));
    let encodedComponentItemLookupValue = btoa(JSON.stringify(componentItemLookupValue));
    let maxProducibleQuantity;
    $.ajax({
        url: `/core/get-max-producible-quantity/${encodedItemLookupValue}?lookup-type=${lookupType}&component-restriction=${encodedComponentItemLookupValue}`,
        async: false,
        dataType: 'json',
        success: function(data) {
            maxProducibleQuantity = data;
        }
    });
    return maxProducibleQuantity;
};

export function getBlendSheet(lotNumber) {
    let blendSheet;
    $.ajax({
        url: `/core/get-blend-sheet/${lotNumber}`,
        async: false,
        dataType: 'json',
        success: function(data) {
            blendSheet = data;
        }
    });
    return blendSheet;
};