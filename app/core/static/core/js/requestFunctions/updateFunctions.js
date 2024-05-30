export function updateCountCollection(thisPk,newCollectionId) {
    let results;
    $.ajax({
        url: `/core/update-count-collection-link?thisPk=${thisPk}&newCollectionId=${newCollectionId}`,
        async: false,
        dataType: 'json',
        success: function(data) {
            results = data;
        }
    });
    return results;
};


export function updateBlendInstructionsOrder(){
    let blendInstructionsDict = {};
    let urlParameters = new URLSearchParams(window.location.search);
    let itemCode = urlParameters.get('itemCode');
    let instructionsOrderDict = {};
    $('#blendInstructionTable tbody tr').each(function() {
        if (!($(this).attr('id') === 'addNewInstructionRow')) {
            //geting the order number and id
            let orderNumber =  $(this).find("td").eq(0).find('input').val();
            let itemID = $(this).find('td:eq(0)').attr("data-item-id");
            instructionsOrderDict[itemID] = orderNumber;
        };
    });
    let jsonString = JSON.stringify(instructionsOrderDict);
    let encodedInstructionsOrder = btoa(jsonString);
    let orderUpdateResult;
    $.ajax({
        url: `/core/update-instructions-order?encodedInstructionsOrder=${encodedInstructionsOrder}`,
        async: false,
        dataType: 'json',
        success: function(data) {
            orderUpdateResult = data;
        }
    });
};

export function logContainerLabelPrint(encodedItemCode) {
    let logUpdateResult;
    $.ajax({
        url: `/core/log-container-label-print?encodedItemCode=${encodedItemCode}`,
        async: false,
        dataType: 'json',
        success: function(data) {
            logUpdateResult = data;
        }
    });
};

export function clearCompletedBlends(blendAreas) {
    blendAreas.forEach(blendArea => {
        $.ajax({
            url: `/core/clear-entered-blends/?blend-area=${blendArea}`,
            async: false,
            dataType: 'json',
            success: function(data) {
                console.log(`Cleared blends for area: ${blendArea}`, data);
            }
        });
    });
};


export function updateCountList() {
    let data = $("#countListForm").serialize();
    let url = window.location.href;
    let encodedPKList = url.substring(url.indexOf('display/') + 8, url.indexOf('?'));
    let urlParams = new URLSearchParams(window.location.search);
    let recordType = urlParams.get('recordType');
    $.ajax({
        url: `/core/update-countlist/${encodedPKList}/${recordType}`,
        type: 'POST',
        data: data,
        success: function(response) {
            console.log(response);
        },
        error: function(error) {
            console.error(error);
        }
    });
};