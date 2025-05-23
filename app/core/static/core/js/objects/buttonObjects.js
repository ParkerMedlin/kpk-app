import { getItemCodesForCheckedBoxes, getCountRecordIDsForCheckedBoxes } from '../uiFunctions/uiFunctions.js'
import { sendImageToServer } from '../requestFunctions/printFunctions.js'
import { getBlendLabelFields, getMostRecentLotRecords, requestBlendSheetPrint } from '../requestFunctions/requestFunctions.js'
import { addLineToSchedule } from '../requestFunctions/updateFunctions.js'

export class CreateCountListButton {
    constructor() {
        try {
            this.setUpCountListButton();
        } catch(err) {
            console.error(err.message);
        }
    };

    setUpCountListButton() {
        $('#create_list').click(function(e) {
            e.preventDefault();
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
            let requestType = 'create'
            // console.log(`/core/count-list/add?itemsToAdd=${encodedItemCodes}&encodedPkList=${encodedDummyList}&recordType=${recordType}`)
            let requestURL = (`/core/count-list/add?itemsToAdd=${encodedItemCodes}&recordType=${recordType}`);
            $.ajax({
                url: requestURL,
                type: 'GET',
                success: function(response) {
                    console.log("Request successful:", response);
                    alert("Count list generated. Check count links page.")
                    // You can add additional logic here if needed
                },
                error: function(xhr, status, error) {
                    console.error("Request failed:", status, error);
                }
            });
        });
    };
};

export class BatchEditCountRecordsButton {
    constructor(thisEditConfirmCountRecordModal) {
        try {
            this.setUpBatchEditButton(thisEditConfirmCountRecordModal);
        } catch(err) {
            console.error(err.message);
        };
    };

    setUpBatchEditButton(thisEditConfirmCountRecordModal) {
        $('#batchEditButton').click(function(e) {
            let itemIDs = getCountRecordIDsForCheckedBoxes();
            $("#editCountRecordsModalButtonLink").prop("dataitemid", itemIDs);
            $("#editCountRecordsModalButtonLink").attr("dataitemid", itemIDs);
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

// export class DateChangeButton {
//     constructor() {
//         try {
//             this.setUpDateChangeButton();
//         } catch(err) {
//             console.error(err.message);
//         }
//     };
//     setUpDateChangeButton() {
//         $('#changeDatesButton').click(function() {
//             console.log("poop")
//             let today = new Date();
//             let year = today.getFullYear();
//             let month = String(today.getMonth() + 1).padStart(2, '0');
//             let day = String(today.getDate()).padStart(2, '0');
//             let formattedDate = year + '-' + month + '-' + day;
//             console.log(formattedDate);

//             // Select input fields with name containing "counted_date" and set their value to today's date
//             let dateInputFields = document.querySelectorAll('input[name*="counted_date"]');
//             for (var i = 0; i < dateInputFields.length; i++) {
//                 dateInputFields[i].value = formattedDate;
//             }
//             $('#changeDatesButton').hide();
//         });
//     };
// };

export class GHSLotNumberButton {
    constructor() {
        try {
            this.setUpGHSLotNumberButtons();
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
    constructor(button, closeAfterPrint) {
        try {
            this.setUpEventListener(button, closeAfterPrint);
        } catch(err) {
            console.error(err.message);
        }
    };
    
    setUpEventListener(button, closeAfterPrint) {
        button.addEventListener('click', function(e) {
            let labelContainer = document.querySelector("#labelContainer")
            let scale = 300 / 96; // Convert from 96 DPI (default) to 300 DPI
            let canvasOptions = {
                scale: scale
            };
            let labelLimit = $("#labelQuantity").val();
            let button = e.currentTarget;
            if (labelLimit > 30) {
                window.alert("Too many labels. Can only print 30 or fewer at a time.")
            } else {
                labelContainer.style.transform = "rotate(90deg)";
                labelContainer.style.border = "";
                html2canvas(labelContainer, canvasOptions).then(canvas => {
                    let labelQuantity = $("#labelQuantity").val();
                    canvas.toBlob(function(labelBlob) {
                        let formData = new FormData();
                        formData.append('labelBlob', labelBlob, 'label.png'); // 'filename.png' is the filename
                        formData.append('labelQuantity', labelQuantity);
                        sendImageToServer(formData);
                        }, 'image/jpeg');
                });
                labelContainer.style.transform = "";
                labelContainer.style.border = "1px solid black";
                if (closeAfterPrint) {
                    let blendLabelDialog = document.querySelector("#blendLabelDialog");
                    if (blendLabelDialog) {
                        blendLabelDialog.close();
                    }
                }
                window.alert("Label(s) sent to printer.");
            }
        });
    };
}
export class CreateBlendLabelButton {
    constructor(button) {
        try {
            this.setUpEventListener(button);
        } catch(err) {
            console.error(err.message);
        }
    };
    
    setUpEventListener(button) {
        button.addEventListener('click', function(e) {
            populateLotNumberDropdown(e.currentTarget.getAttribute("data-encoded-item-code"))
            let blendInformation = getBlendLabelFields(e.currentTarget.getAttribute("data-encoded-item-code"), e.currentTarget.getAttribute("data-lot-number"));
            $("#blend-label-item-code").text(blendInformation.item_code);
            $("#blend-label-item-description").text(blendInformation.item_description);
            $("#blend-label-lot-number").text(blendInformation.lotNumber);
            let itemProtection;
            $("#blend-label-uv-img").hide();
            $("#blend-label-freeze-img").hide();
            $("#blend-label-blank-freeze-img").hide();
            $("#blend-label-blank-uv-img").hide();
            if (blendInformation.uv_protection == 'yes' && blendInformation.freeze_protection == 'yes'){
                itemProtection = "UV and Freeze Protection Required";
                let uvImg = $('#blend-label-uv-img');
                uvImg.appendTo('#uvProtectionContainer');
                uvImg.show();
                let freezeImg = $('#blend-label-freeze-img');
                freezeImg.appendTo('#freezeProtectionContainer');
                freezeImg.show();
            } else if (blendInformation.uv_protection == 'no' && blendInformation.freeze_protection == 'yes'){
                itemProtection = "Freeze Protection Required";
                let freezeImg = $('#blend-label-freeze-img');
                freezeImg.appendTo('#freezeProtectionContainer');
                freezeImg.show();
                let blankUVImg = $('#blend-label-blank-uv-img');
                blankUVImg.appendTo('#uvProtectionContainer');
                blankUVImg.show();
            } else if (blendInformation.uv_protection == 'yes' && blendInformation.freeze_protection == 'no'){
                itemProtection = "UV Protection Required";
                let uvImg = $('#blend-label-uv-img');
                uvImg.appendTo('#uvProtectionContainer');
                uvImg.show();
                let blankFreezeImg = $('#blend-label-blank-freeze-img');
                blankFreezeImg.appendTo('#freezeProtectionContainer');
                blankFreezeImg.show();
            } else {
                itemProtection = "No Protection Required";
                let blankUVImg = $('#blend-label-blank-uv-img');
                blankUVImg.appendTo('#uvProtectionContainer');
                blankUVImg.show();
                let blankFreezeImg = $('#blend-label-blank-freeze-img');
                blankFreezeImg.appendTo('#freezeProtectionContainer');
                blankFreezeImg.show();
            };
            $("#blend-label-protection").text(itemProtection);



            function populateLotNumberDropdown(encodedItemCode) {
                let dropdown = $("#label-lot-number-dropdown");
                dropdown.empty(); // Clear existing options
                let lotNumbers = getMostRecentLotRecords(encodedItemCode);
        
                for (let key in lotNumbers) {
                    let option = document.createElement("option");
                    option.text = `${key} (${lotNumbers[key]} gal on hand)`;
                    option.value = key;
                    dropdown.append(option);
                }
            }
        });
    }
}


export class BlendComponentFilterButton {
    constructor(button) {
        try {
            this.setUpEventListener(button);
        } catch(err) {
            console.error(err.message);
        }
    };
    setUpEventListener(button) {
        button.addEventListener('click', function(e) {
            if (!e.currentTarget.checked) {
                let componentsInUse;
                $.ajax({
                    url: '/core/get-components-in-use-soon/',
                    async: false,
                    dataType: 'json',
                    success: function(data) {
                        componentsInUse = data['componentList'];
                    }
                });
                componentsInUse.forEach(function(component) {
                    $("tr:contains('" + component + "')").hide();
                });
            } else {
                let componentsInUse;
                $.ajax({
                    url: '/core/get-components-in-use-soon/',
                    async: false,
                    dataType: 'json',
                    success: function(data) {
                        componentsInUse = data['componentList'];
                    }
                });
                componentsInUse.forEach(function(component) {
                    $("tr:contains('" + component + "')").show();
                });
            };
        });
    }
}

export class AddScheduleStopperButton {
    constructor(button, desk) {
        try {
            this.setUpEventListener(button, desk);
        } catch(err) {
            console.error(err.message);
        }
    };
    setUpEventListener(button, desk) {
        button.addEventListener('click', function(e) {
            const table = document.getElementById('deskScheduleTable').getElementsByTagName('tbody')[0];
            let highestOrderValue = 0;
            let scheduleNoteCount = 0;

            // Count existing schedule notes
            document.querySelectorAll('tr').forEach(row => {
                const lotCell = row.querySelector('.lot-number-cell');
                if (lotCell && lotCell.textContent.includes('schedulenote')) {
                    scheduleNoteCount++;
                }
            });
            console.log('Schedule note count:', scheduleNoteCount);

            // Get highest order value
            document.querySelectorAll('.orderCell').forEach(cell => {
                const cellValue = parseInt(cell.textContent.trim(), 10);
                if (!isNaN(cellValue) && cellValue > highestOrderValue) {
                    highestOrderValue = cellValue;
                }
            });

            let note;
            note = prompt("Please enter a note for the new schedule line:", "Schedule Note");
            if (note === null || note.trim() === '') {
                note = '';
            }

            const newScheduleNoteNumber = scheduleNoteCount + 1;
            const lot = `schedulenote${newScheduleNoteNumber}`;
            console.log('Adding schedule note:', {
                note: note,
                lot: lot,
                desk: desk,
                order: highestOrderValue + 1
            });
            
            addLineToSchedule(desk, note, lot).then(() => {
                setTimeout(() => {
                    console.log('Reloading page after 3 second delay');
                }, 3000);
                window.location.reload();
            });
        });
    }
}

export class TableSorterButton {
    constructor(tableId, columnName) {
        try {
            this.table = document.getElementById(tableId);
            this.columnIndex = this.getColumnIndex(columnName);
            this.sortState = { asc: true };
            this.button = this.createSortButton();
        } catch(err) {
            console.error(err.message);
        }
    }
  
    getColumnIndex(name) {
      const headers = this.table.querySelectorAll('th');
      return Array.from(headers).findIndex(th => th.textContent.trim() === name)+1;
    }
  
    createSortButton() {
        const button = document.createElement('button');
        button.id = 'sortByShortButton';
        button.textContent = 'Sort by Short';
        button.setAttribute('aria-label', 'Sort table by Short column');
        button.addEventListener('click', () => this.sort());
        button.addEventListener('keydown', e => e.key === 'Enter' && this.sort());
        this.table.parentNode.insertBefore(button, this.table);
        return button;
    }

    sort() {
        this.button.setAttribute('aria-busy', 'true');
        this.button.disabled = true;

        const rows = Array.from(this.table.querySelectorAll('tbody tr'));
        const sortedRows = this.sortRows(rows);

        const fragment = document.createDocumentFragment();
        sortedRows.forEach(row => fragment.appendChild(row));

        this.table.tBodies[0].appendChild(fragment);
        this.updateSortState();

        this.button.removeAttribute('aria-busy');
        this.button.disabled = false;

        Array.from(this.table.querySelectorAll('tbody tr')).forEach((row, index) => {
            // Update order cell for all rows, making it 0-indexed
            row.querySelector('td:first-child').textContent = index;
        });
        let deskScheduleDict = {};
        let thisRow;

        $('#deskScheduleTable tbody tr').each(function() {
            thisRow = $(this);
            let orderNumber = $(this).find('td:eq(0)').text();
            let lotNumber = $(this).find('td:eq(4)').attr("lot-number");
            // Skip rows with an empty value in the second cell.
            if (lotNumber.trim() !== '') {
                // console.log(`Preparing to send to server: Lot ${lotNumber}, Order ${orderNumber}`);
                deskScheduleDict[lotNumber] = orderNumber;
            }
        });
        if (thisRow.hasClass('Desk_1')) {
            deskScheduleDict["desk"] = "Desk_1";
        } else if (thisRow.hasClass('Desk_2')) {
            deskScheduleDict["desk"] = "Desk_2";
        }
        let jsonString = JSON.stringify(deskScheduleDict);
        let encodedDeskScheduleOrder = btoa(jsonString);
        let scheduleUpdateResult;
        $.ajax({
            url: `/core/update-desk-order?encodedDeskScheduleOrder=${encodedDeskScheduleOrder}`,
            async: false,
            dataType: 'json',
            success: function(data) {
                scheduleUpdateResult = data;
            // scheduleUpdateResult.results.forEach(result => {
                // console.log({
                //     'lot': result.lot,
                //     'new_order': result.new_order,
                //     'desk': result.desk
                // });
            // });
            }
        });
    }

    sortRows(rows) {
        const cachedValues = rows.map(row => {
          const val = this.getCellValue(row);
          const isNumber = /^\d+(\.\d+)?$/.test(val);
          const isDate = /^\d{1,2}\/\d{1,2}\/\d{4}$/.test(val);
          const type = isNumber ? 'number' : (isDate ? 'date' : 'string');
          const sortValue = parseFloat(val);
                            // (isDate ? new Date(val.split('/').reverse().join('-')) : val);          
          return { row, original: val, type, sortValue };
        });
      
        cachedValues.sort((a, b) => {
          if (a.type !== b.type) {
            const typePriority = { number: 0, date: 1, string: 2 };
            return typePriority[a.type] - typePriority[b.type];
          }
      
          if (a.type === 'number' || a.type === 'date') {
            const result = a.sortValue - b.sortValue;
            // console.log(`Comparing ${a.original} to ${b.original}: ${result}`);
            return this.sortState.asc ? result : -result;
          }
          return this.sortState.asc ? a.original.localeCompare(b.original) : b.original.localeCompare(a.original);
        });
      
        return cachedValues.map(item => item.row);
      }
  
    getCellValue(row) {
        console.log(row.cells[this.columnIndex]?.getAttribute('data-hour-short') ?? '');
        return row.cells[this.columnIndex]?.getAttribute('data-hour-short') ?? '';
    }
  
    updateSortState() {
      this.sortState.asc = !this.sortState.asc;
      this.button.textContent = `Sort by Short (${this.sortState.asc ? 'Asc' : 'Desc'})`;
    }
  }


export class RecordNumberButton {
    constructor(button) {
        try {
            this.createRecordNumberButton(button);
        } catch(err) {
            console.error(err.message);
        }
    }

    createRecordNumberButton(button){
        button.addEventListener('click', () => {
            let recordsSubString = '&records=' + document.getElementById('recordsPerPage').value;
            let newUrl = window.location.href.split('&records=')[0] + recordsSubString;
            window.location.href = newUrl;
        });

        // let recordsSubString = '&records=' + document.getElementById('recordsPerPage').value;
        // let newUrl = window.location.href.split('&records=')[0] + recordsSubString;
        // window.location.href = newUrl;
        // window.location.reload();
    }

}

export class AddAutomatedBlendcountButton {
    constructor(button) {
        try {
            this.setupEventListener(button);
            console.log('AddAutomatedBlendcountButton set up');
        } catch(err) {
            console.error(err.message);
        }
    }

    setupEventListener(button) {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            const loadingElement = document.getElementById('blendcomponentcount-loading');
            button.style.display = 'none';
            loadingElement.style.display = 'inline-block';
            
            $.ajax({
                url: '/core/create-automated-countlist?recordType=blend',
                type: 'GET',
                success: function(response) {
                    console.log("Response: ", response);
                    console.log(response);
                    let resultElement;
                    if ('no action needed' in response) {
                        resultElement = document.getElementById('blendcount-no-action');
                    } else if ('success' in response) {
                        resultElement = document.getElementById('blendcount-success');
                    }
                    loadingElement.style.display = 'none';
                    resultElement.style.display = 'inline-block';
                    setTimeout(() => {
                        $(resultElement).fadeOut(1000, function() {});
                    }, 3000);
                },
                error: function(xhr, status, error) {
                    console.error("Request failed:", status, error);
                    let resultElement = document.getElementById('blendcount-failure')
                    loadingElement.style.display = 'none';
                    setTimeout(() => {
                        $(resultElement).fadeOut(1000, function() {
                            button.style.display = 'inline-block';
                        });
                    }, 3000);

                }
            });
            
        });
    };

}

export class AddAutomatedBlendcomponentcountButton {
    constructor(button) {
        try {
            this.setupEventListener(button);
            console.log('AddAutomatedBlendcomponentcountButton set up');
        } catch(err) {
            console.error(err.message);
        }
    }
    setupEventListener(button) {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            const loadingElement = document.getElementById('blendcomponentcount-loading');
            button.style.display = 'none';
            loadingElement.style.display = 'inline-block';
            
            $.ajax({
                url: '/core/create-automated-countlist?recordType=blendcomponent',
                type: 'GET',
                success: function(response) {
                    console.log("Response: ", response);
                    console.log(response);
                    let resultElement;
                    if ('no action needed' in response) {
                        resultElement = document.getElementById('blendcomponentcount-no-action');
                    } else if ('success' in response) {
                        resultElement = document.getElementById('blendcomponentcount-success');
                    }
                    loadingElement.style.display = 'none';
                    resultElement.style.display = 'inline-block';
                    setTimeout(() => {
                        $(resultElement).fadeOut(1000, function() {});
                    }, 3000);
                },
                error: function(xhr, status, error) {
                    console.error("Request failed:", status, error);
                    let resultElement = document.getElementById('blendcomponentcount-failure')
                    loadingElement.style.display = 'none';
                    setTimeout(() => {
                        $(resultElement).fadeOut(1000, function() {
                            button.style.display = 'inline-block';
                        });
                    }, 3000);

                }
            });
        });
    }

    // setupEventListener(button) {
    //     button.addEventListener('click', (event) => {
    //         event.preventDefault();
    //         $.ajax({
    //             url: '/core/create-automated-countlist?recordType=blendcomponent',
    //             type: 'GET',
    //             success: function(response) {
    //                 console.log("Response: ", response);
    //             },
    //             error: function(xhr, status, error) {
    //                 console.error("Request failed:", status, error);
    //             }
    //         });
    //     });
    // };

}

export class EditLotNumButton {
    constructor(button) {
        try {
            this.setupEventListeners(button);
        } catch(err) {
            console.error(err.message);
        }
    }
    setupEventListeners(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const lotId = button.getAttribute('data-lot-id');
            console.log(`id is ${lotId}`);
            
            // Get lot details from server
            $.ajax({
                url: `/core/get-json-lot-details/${lotId}/`,
                type: 'GET',
                dataType: 'json',
                success: function(response) {
                    const lotDetails = response;
                    $('#id_editLotNumModal-item_code').val(lotDetails.item_code);
                    $('#id_editLotNumModal-item_description').val(lotDetails.item_description);
                    $('#id_editLotNumModal-lot_number').val(lotDetails.lot_number);
                    $('#id_editLotNumModal-lot_quantity').val(lotDetails.lot_quantity);
                    $('#id_editLotNumModal-date_created').val(lotDetails.date_created);
                    
                    if (lotDetails.run_date) {
                        $('#id_editLotNumModal-run_date').val(lotDetails.run_date);
                    }

                    $('#editLotNumForm').attr('action', '');
                    // Set up form submission via AJAX
                    $('#editLotNumForm').off('submit').on('submit', function(e) {
                        e.preventDefault();
                        const formData = $(this).serialize();
                        
                        $.ajax({
                            url: `/core/update-lot-num-record/${lotId}`,
                            type: 'POST',
                            data: formData,
                            dataType: 'json',
                            success: function(response) {
                                alert("Lot number updated successfully:", response);
                                location.reload();
                            },
                            error: function(xhr, status, error) {
                                console.error("Form submission failed:", status, error);
                                alert("Failed to update lot details. Please try again.");
                            }
                        });
                    });
                    // $('#editLotNumForm').attr('action', `/core/update-lot-num-record/${lotId}`);

                    $('#id_editLotNumModal-line').val(lotDetails.line);
                    $('#id_editLotNumModal-desk').val(lotDetails.desk);

                },
                error: function(xhr, status, error) {
                    console.error("Request failed:", status, error);
                    alert("Failed to load lot details. Please try again.");
                }
            });
        });
    }
}

export class EditItemLocationButton {
    constructor(button) {
        try {
            this.setupEventListeners(button);
        } catch(err) {
            console.error(err.message);
        }
    }
    setupEventListeners(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const itemLocationId = button.getAttribute('data-item-location-id');
            console.log(`id is ${itemLocationId}`);
            
            // Get lot details from server
            $.ajax({
                url: `get-json-item-location/${itemLocationId}/`,
                type: 'GET',
                dataType: 'json',
                success: function(response) {
                    const itemLocationDetails = response;
                    console.log(itemLocationDetails);

                    $('#id_editItemLocationModal-item_code').val(itemLocationDetails.item_code);
                    $('#id_editItemLocationModal-item_description').val(itemLocationDetails.item_description);
                    $('#id_editItemLocationModal-unit').val(itemLocationDetails.unit);
                    $('#id_editItemLocationModal-storage_type').val(itemLocationDetails.storage_type);
                    $('#id_editItemLocationModal-zone').val(itemLocationDetails.zone);
                    $('#id_editItemLocationModal-bin').val(itemLocationDetails.bin);
                    $('#id_editItemLocationModal-item_type').val(itemLocationDetails.item_type);

                    $('#editItemLocationForm').attr('action', '');
                    // Set up form submission via AJAX
                    $('#editItemLocationForm').off('submit').on('submit', function(e) {
                        e.preventDefault();
                        const formData = $(this).serialize();
                        
                        $.ajax({
                            url: `/core/update-item-location/${itemLocationId}/`,
                            type: 'POST',
                            data: formData,
                            dataType: 'json',
                            success: function(responsey) {
                                alert("Item location updated", responsey);
                                location.reload();
                            },
                            error: function(xhr, status, error) {
                                console.error("Form submission failed:", status, error);
                                alert("Failed to update lot details. Please try again.");
                            }
                        });
                    });

                },
                error: function(xhr, status, error) {
                    console.error("Request failed:", status, error);
                    alert("Failed to load lot details. Please try again.");
                }
            });
        });
    }
}



export class AddMissingItemLocationsButton {
    constructor(button) {
        try {
            this.setupEventListener(button);
        } catch(err) {
            console.error(err.message);
        }
    }

    setupEventListener(button) {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            
            // Ask user to confirm before proceeding
            const confirmResult = confirm("Are you sure you want to add missing item locations? This will create location records for items that don't have them.");
            
            if (confirmResult) {
                // Show loading indicator or disable button while processing
                button.disabled = true;
                button.textContent = "Processing...";
                
                const itemTypeFilter = document.getElementById('itemTypeFilter');
                let itemType = '';
                
                if (itemTypeFilter && itemTypeFilter.value) {
                    itemType = itemTypeFilter.value;
                }
                
                // Build the URL with the item-type parameter if a type is selected
                let requestUrl = '/core/add-missing-item-locations/';
                if (itemType) {
                    requestUrl += `?item-type=${encodeURIComponent(itemType)}`;
                }

                console.log(requestUrl)
                

                // Send AJAX request to add missing item locations
                $.ajax({
                    url: requestUrl,
                    type: 'GET',
                    dataType: 'json',
                    success: function(response) {
                        // Alert the user of the response
                        alert(`${response.status}: ${response.message}`);
                        
                        // Re-enable button and restore text
                        button.disabled = false;
                        button.textContent = "Add Missing Item Locations";
                        
                        // Optionally refresh the page to show updated data
                        if (response.status === "Success") {
                            location.reload();
                        }
                    },
                    error: function(xhr, status, error) {
                        console.error("Request failed:", status, error);
                        alert("Failed to add missing item locations. Please try again.");
                        
                        // Re-enable button and restore text
                        button.disabled = false;
                        button.textContent = "Add Missing Item Locations";
                    }
                });
            }
        });
    }
}

export class ToteClassificationEditButton {
    constructor(buttons) {
        if (buttons instanceof Element) {
            this.setUpEventListener(buttons);
        } else if (buttons instanceof NodeList || Array.isArray(buttons)) {
            buttons.forEach(button => this.setUpEventListener(button));
        }
    }
    
    setUpEventListener(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get the row data
            const row = this.closest('tr');
            const itemCode = row.cells[0].textContent;
            const currentClassification = row.cells[1].textContent;
            
            // Create an input for editing
            const newClassification = prompt("Edit tote classification:", currentClassification);
            
            // If user cancels or enters empty value, do nothing
            if (newClassification === null || newClassification.trim() === '') {
                return;
            }
            
            // Send update request to the server
            $.ajax({
                url: `/core/api/tote-classifications/${encodeURIComponent(itemCode)}/update/`,
                type: 'POST',
                data: JSON.stringify({
                    tote_classification: newClassification
                }),
                contentType: 'application/json',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                success: function(response) {
                    // Update the row with new data
                    row.cells[1].textContent = newClassification;
                    alert("Tote classification updated successfully");
                },
                error: function(xhr, status, error) {
                    console.error("Update failed:", xhr.responseText);
                    alert("Failed to update tote classification. Please try again.");
                }
            });
        });
    }
}

export class ToteClassificationDeleteButton {
    constructor(buttons) {
        if (buttons instanceof Element) {
            this.setUpEventListener(buttons);
        } else if (buttons instanceof NodeList || Array.isArray(buttons)) {
            buttons.forEach(button => this.setUpEventListener(button));
        }
    }
    
    setUpEventListener(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get the row data
            const row = this.closest('tr');
            const itemCode = row.cells[0].textContent;
            
            // Confirm deletion
            if (!confirm(`Are you sure you want to delete the classification for ${itemCode}?`)) {
                return;
            }
            
            // Send delete request to the server
            $.ajax({
                url: `/core/api/tote-classifications/${encodeURIComponent(itemCode)}/delete/`,
                type: 'DELETE',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                success: function(response) {
                    // Remove the row from the table
                    row.remove();
                    alert("Tote classification deleted successfully");
                },
                error: function(xhr, status, error) {
                    console.error("Delete failed:", xhr.responseText);
                    alert("Failed to delete tote classification. Please try again.");
                }
            });
        });
    }
}

export class PrintBlendSheetButton {
    constructor(buttonElement) {
        if (!buttonElement) {
            console.error("Button element not provided for PrintBlendSheetButton.");
            return;
        }
        this.button = buttonElement;
        this.itemCodeInput = document.getElementById('item-code-input'); // Adjust ID as needed
        this.lotNumberInput = document.getElementById('lot-number-input'); // Adjust ID as needed
        this.lotQuantityInput = document.getElementById('lot-quantity-input'); // Adjust ID as needed

        this.setUpEventListener();
    }

    setUpEventListener() {
        this.button.addEventListener('click', async () => {
            const itemCode = this.itemCodeInput ? this.itemCodeInput.value : null;
            const lotNumber = this.lotNumberInput ? this.lotNumberInput.value : null;
            const lotQuantity = this.lotQuantityInput ? this.lotQuantityInput.value : null;

            if (!itemCode || !lotNumber || !lotQuantity) {
                alert('Please ensure Item Code, Lot Number, and Lot Quantity are filled.');
                return;
            }
            
            // Optionally, disable the button to prevent multiple clicks
            this.button.disabled = true;
            this.button.textContent = 'Processing...';

            try {
                const result = await requestBlendSheetPrint(itemCode, lotNumber, lotQuantity);
                if (result.success) {
                    // Handle success (e.g., clear inputs, show a more persistent success message)
                    if (this.itemCodeInput) this.itemCodeInput.value = '';
                    if (this.lotNumberInput) this.lotNumberInput.value = '';
                    if (this.lotQuantityInput) this.lotQuantityInput.value = '';
                } else {
                    // Error already alerted by requestBlendSheetPrint, 
                    // but you can add more specific error handling here if needed.
                }
            } catch (error) {
                // This catch is mostly for unexpected errors not caught by requestBlendSheetPrint
                console.error("Error in PrintBlendSheetButton click handler:", error);
                alert("An unexpected error occurred.");
            } finally {
                // Re-enable the button
                this.button.disabled = false;
                this.button.textContent = 'Print Blend Sheet'; // Or its original text
            }
        });
    }
}
