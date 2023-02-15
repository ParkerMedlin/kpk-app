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
}