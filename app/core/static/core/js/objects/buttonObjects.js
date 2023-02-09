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
            let itemCodes = [];
            $('td input:checked').each(function() {
                itemCodes.push($(this).attr("name"));
            });
            // https://stackoverflow.com/questions/4505871/good-way-to-serialize-a-list-javascript-ajax
            let encodedItemCodes = btoa(JSON.stringify(itemCodes));
            let dummyList = ["No_Item_Codes"];
            let encodedDummyList = btoa(JSON.stringify(dummyList));
            // https://stackoverflow.com/questions/503093/how-do-i-redirect-to-another-webpage
            let baseURL = window.location.href.split('core')[0];
            window.location.replace(baseURL + "core/countlist/add/"+encodedItemCodes+'/'+encodedDummyList)
        });
    };
};

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
                window.location.replace(baseURL + "core/displayfinishedcounts/"+encoded_list)
            }
        });
    };
};