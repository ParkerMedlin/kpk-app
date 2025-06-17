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

export function getNewBlendInstructionInfo(encodedItemCode) {
    let blendInstructionInfo;
    $.ajax({
        url: `/core/get-new-blend-instruction-info/?encodedItemCode=${encodedItemCode}`,
        async: false,
        dataType: 'json',
        success: function(data) {
            blendInstructionInfo = data;
        }
    });
    return blendInstructionInfo;
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

export function getContainersFromCount(countRecordId, recordType) {
    let containers;
    // console.log(`getting containers for ${countRecordId} of recordtype ${recordType}`);
    $.ajax({
        url: `/core/get-json-containers-from-count?countRecordId=${countRecordId}&recordType=${recordType}`,
        async: false,
        dataType: 'json',
        success: function(data) {
            containers = data;
        }
    });
    // console.log(`inserting html for ${containers}`);
    return containers;
}

export function getLotDetails(lotId) {
    let lotData;
    $.ajax({
        url: `/core/get-json-lot-details/${lotId}`,
        async: false,
        dataType: 'json',
        success: function(data) {
            lotData = data;
        }
    }).fail(function() {
        console.log("Failed to retrieve lot details. Check the lot ID and try again.");
    });
    return lotData;
}

export async function requestBlendSheetPrint(itemCode, lotNumber, lotQuantity) {
    const url = '/print_blend_sheet/'; // Or use Django's {% url 'print_blend_sheet' %} if generated in template
    const payload = {
        item_code: itemCode,
        lot_number: lotNumber,
        lot_quantity: lotQuantity
    };

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // Add CSRF token header if not using @csrf_exempt and handling CSRF in JS
                // 'X-CSRFToken': getCookie('csrftoken') // Example: function to get CSRF token
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ message: response.statusText }));
            console.error('Error printing blend sheet:', errorData.message);
            alert(`Error printing blend sheet: ${errorData.message}`);
            return { success: false, message: errorData.message };
        }

        const result = await response.json();
        // Assuming the service returns a success status and message
        if (result.status === 'success') {
            console.log('Blend sheet print request successful:', result.message);
            alert(result.message || 'Print request sent successfully!');
            return { success: true, data: result };
        } else {
            console.error('Print request failed:', result.message);
            alert(`Print request failed: ${result.message}`);
            return { success: false, message: result.message };
        }
    } catch (error) {
        console.error('Network or other error in requestBlendSheetPrint:', error);
        alert(`An error occurred while sending the print request: ${error.message}`);
        return { success: false, message: error.message };
    }
}

// Helper function to get CSRF token if needed
// function getCookie(name) {
//     let cookieValue = null;
//     if (document.cookie && document.cookie !== '') {
//         const cookies = document.cookie.split(';');
//         for (let i = 0; i < cookies.length; i++) {
//             const cookie = cookies[i].trim();
//             if (cookie.substring(0, name.length + 1) === (name + '=')) {
//                 cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
//                 break;
//             }
//         }
//     }
//     return cookieValue;
// }

export function getActiveFormulaChangeAlerts() {
    let alertsResponse;
    const jsonURL = '/core/active-formula-change-alerts/';
    $.ajax({
        url: jsonURL,
        async: false, // Consistent with other functions in this file
        dataType: 'json',
        success: function(data) {
            alertsResponse = data; // The view returns {'alerts_data': [...], 'other_optional_keys': ...}
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error("Failed to retrieve active formula change alerts.");
            console.error("URL: " + jsonURL);
            console.error("Status: " + textStatus + ", Error: " + errorThrown);
            alertsResponse = { error: "Failed to retrieve data", details: errorThrown }; // Return an error object
        }
    });
    return alertsResponse; // This will contain the full response object or an error object
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

export async function addLotNumRecord(formData, redirectPage, duplicates) {
    const url = `/core/add-lot-num-record/?redirect-page=${redirectPage}&duplicates=${duplicates}`;
    formData.append('addNewLotNumRecord', 'true');

    try {
        const response = await fetch(url, {
            method: 'POST',
            body: formData,
        });

        const result = await response.json();

        if (!response.ok) {
            console.error('Failed to add lot number record:', result.message);
            return { success: false, message: result.message };
        }

        return { success: true, data: result };
    } catch (error) {
        console.error('Network or other error:', error);
        return { success: false, message: error.toString() };
    }
}