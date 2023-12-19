import { getItemCodesForCheckedBoxes, getCountRecordIDsForCheckedBoxes } from '../uiFunctions/uiFunctions.js'
import { BrowserPrint } from '../thirdPartyLibraries/BrowserPrint-3.1.250.js'
import { html2canvas } from '../thirdPartyLibraries/html2canvas-1.14.js'

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
            let dummyList = ["No_Item_Codes"];  // This is here to indicate that we are not in fact reloading the rest of a
                                                // non-existent list. Necessary because we use this same function on both the
                                                // upcoming_counts page and the count_list page.
            let encodedDummyList = btoa(JSON.stringify(dummyList));
            // https://stackoverflow.com/questions/503093/how-do-i-redirect-to-another-webpage
            let baseURL = window.location.href.split('core')[0];
            let urlParameters = new URLSearchParams(window.location.search);
            let recordType = urlParameters.get('recordType');
            // console.log(`/core/count-list/add?itemsToAdd=${encodedItemCodes}&encodedPkList=${encodedDummyList}&recordType=${recordType}`)
            window.location.replace(`/core/count-list/add?itemsToAdd=${encodedItemCodes}&encodedPkList=${encodedDummyList}&recordType=${recordType}`)
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
            let itemIDs = getCountRecordIDsForCheckedBoxes();
            e.currentTarget.setAttribute("dataitemid", itemIDs);
            if (!itemIDs.length) {
                alert("Please check at least one row to delete.");
            } else {
                thisDeleteCountRecordModal.setModalButtons(e);
            }
        });
    };
}

export class BatchEditCountRecordsButton {
    constructor(thisEditConfirmCountRecordModal) {
        try {
            this.setUpBatchEditButton(thisEditConfirmCountRecordModal);
            console.log("Instance of class BatchEditCountRecordsButton created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    setUpBatchEditButton(thisEditConfirmCountRecordModal) {
        $('#batchEditButton').click(function(e) {
            let itemIDs = getCountRecordIDsForCheckedBoxes();
            e.currentTarget.setAttribute("dataitemid", itemIDs);
            if (!itemIDs.length) {
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
            let itemIDs = getCountRecordIDsForCheckedBoxes();
            if (itemIDs.length === 0) {
                alert("Please check at least one row to include in the report.")
            } else {
                // https://stackoverflow.com/questions/4505871/good-way-to-serialize-a-list-javascript-ajax
                let encoded_list = btoa(JSON.stringify(itemIDs));
                console.log(encoded_list)
                let baseURL = window.location.href.split('core')[0];
                // https://stackoverflow.com/questions/503093/how-do-i-redirect-to-another-webpage
                let urlParameters = new URLSearchParams(window.location.search);
                let recordType = urlParameters.get('recordType');
                window.location.replace(baseURL + `core/display-count-report?encodedList=${encoded_list}&recordType=${recordType}`)
            }
        });
    };
};

export class RecountsButton {
    constructor() {
        try {
            this.setUpRecountsButton();
            console.log("Instance of class RecountsButton created.");
        } catch(err) {
            console.error(err.message);
        }
    };
    setUpRecountsButton() {
        $('#recountsButton').click(function() {
            let unCountedRows = document.getElementsByClassName("notCounted");
            for (let i = 0; i < unCountedRows.length; i++) {
                let row = unCountedRows[i];
                let checkbox = row.querySelector("input[type='checkbox']");
                checkbox.checked = true;
              }
        });
    };
};

export class DateChangeButton {
    constructor() {
        try {
            this.setUpDateChangeButton();
            console.log("Instance of class DateChangeButton created.");
        } catch(err) {
            console.error(err.message);
        }
    };
    setUpDateChangeButton() {
        $('#changeDatesButton').click(function() {
            console.log("poop")
            let today = new Date();
            let year = today.getFullYear();
            let month = String(today.getMonth() + 1).padStart(2, '0');
            let day = String(today.getDate()).padStart(2, '0');
            let formattedDate = year + '-' + month + '-' + day;
            console.log(formattedDate);

            // Select input fields with name containing "counted_date" and set their value to today's date
            let dateInputFields = document.querySelectorAll('input[name*="counted_date"]');
            for (var i = 0; i < dateInputFields.length; i++) {
                dateInputFields[i].value = formattedDate;
            }
            $('#changeDatesButton').hide();
        });
    };
};

export class GHSLotNumberButton {
    constructor() {
        try {
            this.setUpGHSLotNumberButtons();
            console.log("Instance of class GHSLotNumberButton created.");
        } catch(err) {
            console.error(err.message);
        }
    };

    setUpGHSLotNumberButtons() {
        const lotNumberButton  = document.querySelector("#lotNumberButton");
        lotNumberButton.addEventListener('click', function() {
            document.querySelectorAll('.lotNumberContainer').forEach(inputContainer => {
                if (inputContainer.style.display === "none") {
                    inputContainer.style.display = "block";
                    lotNumberButton.textContent = 'Hide Lot Number Fields';
                } else {
                    inputContainer.style.display = "none";
                    lotNumberButton.textContent = 'Show Lot Number Fields';
                }
            });
           
        });
    };
};

export class GHSSheetGenerator {
    constructor() {
        try {
            this.setUpGHSSheetGeneratorLinks();
            console.log("Instance of class GHSSheetGenerator created.");
        } catch(err) {
            console.error(err.message);
        }
    };
    
    setUpGHSSheetGeneratorLinks() {
        const GHSSheetGeneratorButtons = document.querySelectorAll('.GHSLink');
        GHSSheetGeneratorButtons.forEach(button => {
            let encodedItemCode;
            let lotNum;
            encodedItemCode = btoa(button.getAttribute("itemCode"));
            lotNum = button.getAttribute("lotNum");
            if (lotNum) {
                button.setAttribute("href", `/core/display-ghs-label/${encodedItemCode}?lotNumber=${lotNum}`);
            } else {
                button.setAttribute("href", `/core/display-ghs-label/${encodedItemCode}`);
            }
        });
    };
}

export class ZebraPrintButton {
    constructor(button) {
        try {
            this.setUpEventListener(button);
            this.initialTesting();
            console.log("Instance of class ZebraPrintButton created.");
        } catch(err) {
            console.error(err.message);
        }
    };
    
    

    setUpEventListener(button) {
        button.addEventListener('click', function() {
            let selected_device;
            
            function setup() {
                //Get the default device from the application as a first step. Discovery takes longer to complete.
                BrowserPrint.getDefaultDevice("printer", function(device)
                    {
                        //Add device to list of devices and to html select element
                        selected_device = device;
                        devices.push(device);
                        var html_select = document.getElementById("selected_device");
                        var option = document.createElement("option");
                        option.text = device.name;
                        html_select.add(option);
                        
                        //Discover any other devices available to the application
                        BrowserPrint.getLocalDevices(function(device_list){
                            for(var i = 0; i < device_list.length; i++)
                            {
                                //Add device to list of devices and to html select element
                                var device = device_list[i];
                                if(!selected_device || device.uid != selected_device.uid)
                                {
                                    devices.push(device);
                                    var option = document.createElement("option");
                                    option.text = device.name;
                                    option.value = device.uid;
                                    html_select.add(option);
                                }
                            }
                        }, function(){alert("Error getting local devices")},"printer");
                    }, function(error){
                        alert(error);
                    })
            }
            setup();

            function sendImage(imageUrl) {
                url = window.location.href.substring(0, window.location.href.lastIndexOf("/"));
                url = url + "/" + imageUrl;
                selected_device.convertAndSendFile(url, undefined, errorCallback);
            };

            html2canvas(document.querySelector("#labelContainer")).then(canvas => {
                let img = canvas.toDataURL("image/png");
                sendImage(img);
            });
        });
    };

}