export function getAllBOMFields(restriction){
    let allBOMFields;
    let jsonURL = `/core/getBOMfields/?restriction=${restriction}`;
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
    let jsonURL = `/core/iteminforequest/?item=${encodedLookupValue}&lookupType=${lookupType}`;
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
}

export function getLocation(lookupValue, lookupType){
    let locationData;
    let encodedLookupValue = btoa(JSON.stringify(lookupValue));
    let jsonURL = `/core/itemlocationrequest/?item=${encodedLookupValue}&lookupType=${lookupType}`;
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
    let maxBlendInfo;
    console.log(`/core/getmaxproduciblequantity/${encodedItemLookupValue}?lookupType=${lookupType}&componentRestriction=${encodedComponentItemLookupValue}`)
    $.ajax({
        url: `/core/getmaxproduciblequantity/${encodedItemLookupValue}?lookupType=${lookupType}&componentRestriction=${encodedComponentItemLookupValue}`,
        async: false,
        dataType: 'json',
        success: function(data) {
            maxBlendInfo = data;
        }
    });
    console.log(maxBlendInfo);
    return maxBlendInfo;
} 