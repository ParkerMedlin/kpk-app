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

export function getItemInfo(lookupValue, lookupType, restriction){
    let itemData;
    let encodedLookupValue = btoa(JSON.stringify(lookupValue));
    let jsonURL = `/core/item-info-request/?item=${encodedLookupValue}&lookup-type=${lookupType}&restriction=${restriction}`;
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

export function getBlendSheetTemplate(itemCode){
    let blendSheetTemplate;
    $.ajax({
        url: `/core/get-blend-sheet-template/?itemCode=${itemCode}`,
        async: false,
        dataType: 'json',
        success: function(data) {
            blendSheetTemplate = data;
        }
    });
    return blendSheetTemplate;
}

export function getBlendCrewInitials() {
    let initialsList;
    $.ajax({
        url: '/core/get-blend-crew-initials-list',
        async: false,
        dataType: 'json',
        success: function(data) {
            initialsList = data;
        }
    });
    return initialsList.initials;
}

export function getURLParameter(parameterName) {
    const urlParameters = new URLSearchParams(window.location.search);
    const result = urlParameters.get(parameterName);

    return result;
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

export function getMostRecentLotRecords(encodedItemCode) {
    let lotNumbers;
    $.ajax({
        url: `/core/get-json-most-recent-lot-records/?encodedItemCode=${encodedItemCode}`,
        async: false,
        dataType: 'json',
        success: function(data) {
            lotNumbers = data;
        }
    });
    return lotNumbers;
}

export function getBlendQuantitiesPerBill() {
    let blendQuantitiesPerBill;
    $.ajax({
        url: `/core/get-json-all-blend-qtyperbill/`,
        async: false,
        dataType: 'json',
        success: function(data) {
            blendQuantitiesPerBill = data;
        }
    });
    return blendQuantitiesPerBill;
}

export function getMatchingLotNumbers(encodedItemCode, prodLine, runDate) {
    let matchingLotNumbers;
    $.ajax({
        url: `/core/get-json-matching-lot-numbers?itemCode=${encodedItemCode}&prodLine=${prodLine}&runDate=${runDate}`,
        async: false,
        dataType: 'json',
        success: function(data) {
            matchingLotNumbers = data;
        }
    });
    return matchingLotNumbers;
}
export function getToteClassificationData() {
    let toteClassificationData;
    $.ajax({
        url: '/core/get-tote-classification-data/',
        async: false,
        dataType: 'json',
        success: function(data) {
            toteClassificationData = data;
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error("Failed to fetch tote classification data:", textStatus, errorThrown);
            // Optionally, you might want to return an empty object or throw the error
            // depending on how you want to handle failures upstream.
            toteClassificationData = {}; // Default to empty object on error
        }
    });
    return toteClassificationData;
}

export function getAllFoamFactors() {
    let foamFactorsResponse;
    const jsonURL = '/core/get-all-foam-factors/';
    $.ajax({
        url: jsonURL,
        async: false,
        dataType: 'json',
        success: function(data) {
            foamFactorsResponse = data;
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error("Failed to retrieve all foam factors.");
            console.error("URL: " + jsonURL);
            console.error("Status: " + textStatus + ", Error: " + errorThrown);
            foamFactorsResponse = { error: "Failed to retrieve data", details: errorThrown };
        }
    });
    return foamFactorsResponse;
}