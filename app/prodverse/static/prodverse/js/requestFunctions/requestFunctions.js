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

export function getBlendLabelFields(encodedItemCode, lotNumber) {
    let itemCode = atob(encodedItemCode);
    let itemInfo = getItemInfo(itemCode, 'itemCode')
    if (!lotNumber) {
        lotNumber = getOldestNonZeroLotNumberOrNewestZeroLotNumber(encodedItemCode);
    } 
    itemInfo.lotNumber = lotNumber;

    return itemInfo;
}

export function getOldestNonZeroLotNumberOrNewestZeroLotNumber(encodedItemCode) {
    let lotNumber;
    $.ajax({
        url: `/core/get-json-lot-number/?encodedItemCode=${encodedItemCode}`,
        async: false,
        dataType: 'json',
        success: function(data) {
            lotNumber = data.lot_number;
        }
    });
    return lotNumber;
}