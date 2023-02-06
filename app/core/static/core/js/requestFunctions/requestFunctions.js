export function getAllItemCodeAndDesc(){
    let allBOMFields;
    let jsonURL = '/core/getBOMfields/?restriction=chem-dye-frag';
    $.ajax({
        url: jsonURL;
        async: false;
        dataType: 'json',
        success: function(data) {
            allBOMFields = data;
        }
    }).fail(function() { // err handle
        console.log("BOM request not fulfilled.");
    });
    return allBOMFields;
};

export function getItemInfo(lookupValue, lookupType){
    let itemData;
    let jsonURL = `/core/item_info_request/?item=${lookupValue}&lookupType=${lookupType}`;
    console.log(jsonURL);
    $.ajax({
        url: jsonURL,
        async: false,
        dataType: 'json',
        success: function(data) {
            itemData = data;
        }
    }).fail(function() { // err handle
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
    let jsonURL = `/core/item_location_request/?item=${lookupValue}&lookupType=${lookupType}`;
    $.ajax({
        url: jsonURL,
        async: false,
        dataType: 'json',
        success: function(data) {
            locationData = data;
        }
    }).fail(function() { // err handle
        console.log("Item not found. Check search terms and try again.");
        $itemLocation.text("Item not found. Check search terms and try again.");
        $itemQty.text("Item not found. Check search terms and try again.");
    }).always(function() {
        $animation.toggle();
        $itemCodeInput.removeClass('loading');
        $itemDescriptionInput.removeClass('loading');
    });
    return locationData;
};