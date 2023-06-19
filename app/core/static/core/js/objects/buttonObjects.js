import { getItemCodesForCheckedBoxes } from '../uiFunctions/uiFunctions.js'

export class CreateCountListButton {
    constructor() {
        try {
            this.setUpCountListButton();
            console.log("Instance of class CreateCountListButton created.");
        } catch(err) {
            console.error(err.message);
        }
    };
    setUpCountListButton() {
        $('#create_list').click(function() {
            let itemCodes = getItemCodesForCheckedBoxes();
            // https://stackoverflow.com/questions/4505871/good-way-to-serialize-a-list-javascript-ajax
            let encodedItemCodes = btoa(JSON.stringify(itemCodes));
            let dummyList = ["No_Item_Codes"];
            let encodedDummyList = btoa(JSON.stringify(dummyList));
            // https://stackoverflow.com/questions/503093/how-do-i-redirect-to-another-webpage
            let baseURL = window.location.href.split('core')[0];
            window.location.replace(baseURL + "core/count-list/add/"+encodedItemCodes+'/'+encodedDummyList)
        });
    };
};

export class BatchDeleteCountRecordsButton {
    constructor(thisDeleteCountRecordModal) {
        try {
            this.setUpBatchDeleteButton(thisDeleteCountRecordModal);
            console.log("Instance of class BatchDeleteCountRecordsButton created.");
        } catch(err) {
            console.error(err.message);
        }
    }

    setUpBatchDeleteButton(thisDeleteCountRecordModal) {
        $('#batchDeleteButton').click(function(e) {
            let itemCodes = getItemCodesForCheckedBoxes();
            e.currentTarget.setAttribute("dataitemid", itemCodes);
            if (!itemCodes.length) {
                alert("Please check at least one row to delete.");
            } else {
                thisDeleteCountRecordModal.setModalButtons(e);
            }
        });
    };
}

export class BatchEditCountRecordsButton {
    constructor(thisDeleteCountRecordModal) {
        try {
            this.setUpBatchEditButton(thisDeleteCountRecordModal);
            console.log("Instance of class BatchEditCountRecordsButton created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    setUpBatchEditButton(thisEditConfirmCountRecordModal) {
        $('#batchEditButton').click(function(e) {
            let itemCodes = getItemCodesForCheckedBoxes();
            e.currentTarget.setAttribute("dataitemid", itemCodes);
            if (!itemCodes.length) {
                alert("Please check at least one row to edit.")
            } else {
                thisEditConfirmCountRecordModal.setModalButtons(e);
            }
        });
    };
}

export class CreateCountsReportButton {
    constructor() {
        try {
            this.setUpCountsReportButton();
            console.log("Instance of class CreateCountsReportButton created.");
        } catch(err) {
            console.error(err.message);
        }
    };
    setUpCountsReportButton() {
        $('#createReportButton').click(function() {
            let item_codes = getItemCodesForCheckedBoxes();
            if (item_codes.length === 0) {
                alert("Please check at least one row to include in the report.")
            } else {
                // https://stackoverflow.com/questions/4505871/good-way-to-serialize-a-list-javascript-ajax
                let encoded_list = btoa(JSON.stringify(item_codes));
                console.log(encoded_list)
                let baseURL = window.location.href.split('core')[0];
                // https://stackoverflow.com/questions/503093/how-do-i-redirect-to-another-webpage
                window.location.replace(baseURL + "core/display-finished-counts/"+encoded_list)
            }
        });
    };
};