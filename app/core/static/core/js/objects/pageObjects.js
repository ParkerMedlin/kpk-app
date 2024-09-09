import { getMaxProducibleQuantity, getBlendSheet, getBlendSheetTemplate, getURLParameter, getNewBlendInstructionInfo, getBlendCrewInitials, getItemInfo } from '../requestFunctions/requestFunctions.js'
import { updateCountCollection } from '../requestFunctions/updateFunctions.js'
import { updateBlendInstructionsOrder, logContainerLabelPrint } from '../requestFunctions/updateFunctions.js'
import { ItemReferenceFieldPair } from './lookupFormObjects.js'

export class CountListPage {
    constructor(thisCountListWebSocket) {
        try {
            this.setUpEventListeners(thisCountListWebSocket);
            this.updateCheckBoxCellColors();
            this.setupLabelLinks();
            console.log("Instance of class CountListPage created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    updateCheckBoxCellColors() {
        const countedCells = $('.tbl-cell-counted');
        countedCells.each(function() {
            const checkbox = $(this).find('input[type="checkbox"]');
            if (checkbox.is(':checked')) {
                $(this).removeClass('uncheckedcountedcell').addClass('checkedcountedcell');
            } else {
                $(this).removeClass('checkedcountedcell').addClass('uncheckedcountedcell');
            }
        });
    }

    setupLabelLinks() {
        const links = $(".partialContainerLabelLink");
        links.each(function() {
            $(this).click(function() {
                document.getElementById("blendLabelDialog").showModal();
                let thisItemCode = $(this).attr('data-itemcode');
                let encodedItemcode = btoa(thisItemCode);
                let itemInformation;
                $.ajax({
                    url: '/core/item-info-request?lookup-type=itemCode&item=' + encodedItemcode,
                    async: false,
                    dataType: 'json',
                    success: function(data) {
                        itemInformation = data;
                    }
                });
                let thisItemDescription = itemInformation.item_description;
                $("#inventory-label-item-code").text(thisItemCode);
                $("#inventory-label-item-description").text(thisItemDescription);
            });
        });
    }

    setUpEventListeners(thisCountListWebSocket) {
        function updateDate(eventTarget){
            let correspondingID = eventTarget.attr('correspondingrecordid');
            const today = new Date();
            const formattedDate = today.toISOString().split('T')[0];
            $(`td[data-countrecord-id="${correspondingID}"]`).find("input[name*='counted_date']").val(formattedDate);
        };

        function calculateVariance(eventTarget) {
            let dataCountRecordId = eventTarget.attr('data-countrecord-id');
            let expectedQuantity = $(`span[data-countrecord-id="${dataCountRecordId}"].expected-quantity-span`).text().trim();
            let countedQuantity = parseFloat(eventTarget.val());
            if (isNaN(countedQuantity) || countedQuantity === null || countedQuantity === '') {
                countedQuantity = 0.0;
            }
            let variance = countedQuantity - expectedQuantity;
            $(`tr td[data-countrecord-id="${dataCountRecordId}"].tbl-cell-variance`).text(variance.toFixed(2));
        };

        function handleCountRecordChange(event, thisCountListWebSocket, changeType) {
            const dataCountRecordId = event.attr('data-countrecord-id');
            updateDate(event);
            if (changeType === "counted-quantity-update") {
                calculateVariance(event);
            };
            const recordId = event.attr("data-countrecord-id");
            const recordType = getURLParameter("recordType");
            const recordData = {
                'counted_quantity': $(`input[data-countrecord-id="${dataCountRecordId}"].counted_quantity`).val(),
                'expected_quantity': $(`span[data-countrecord-id="${dataCountRecordId}"].expected-quantity-span`).text().trim(),
                'variance': $(`td[data-countrecord-id="${dataCountRecordId}"].tbl-cell-variance`).text(),
                'counted_date': $(`td[data-countrecord-id="${dataCountRecordId}"].tbl-cell-counted_date`).text(),
                'counted': $(`input[data-countrecord-id="${dataCountRecordId}"].counted-input`).prop("checked"),
                'comment': $(`textarea[data-countrecord-id="${dataCountRecordId}"].comment`).val() || '',
                'location': $(`select[data-countrecord-id="${dataCountRecordId}"].location-selector`).val(),
                'record_type': recordType
            }
            thisCountListWebSocket.updateCount(recordId, recordType, recordData);
        }

        $('input.counted_quantity').keyup(function(){
            handleCountRecordChange($(this), thisCountListWebSocket, "counted-quantity-update");
        });
        $('select.location-selector').change(function(){
            handleCountRecordChange($(this), thisCountListWebSocket, "location-update");
        });
        $('textarea.comment').on('input', function(){
            handleCountRecordChange($(this), thisCountListWebSocket, "comment-update");
        });
        $('input.counted-input').change(function(){
            handleCountRecordChange($(this), thisCountListWebSocket, "counted-approval-update");
        });

        $('tr').click(function() {
            const countedDateCell = $(this).find('td.tbl-cell-counted_date');
            const today = new Date();
            const formattedDate = today.toISOString().split('T')[0];
            if (countedDateCell.length > 0) {
                countedDateCell.text(formattedDate);
            }
        });

        

        //dynamically resize commentfields when they are clicked/tapped
        const commentFields = document.querySelectorAll('textarea');
        commentFields.forEach((field) => {
            field.addEventListener("focus", function(){
                field.setAttribute("rows", "10");
                field.setAttribute("cols", "40");
            });
            field.addEventListener("blur", function(){
                field.setAttribute("rows", "1");
                field.setAttribute("cols", "10");
            });
        });

        // update the quantity of the selected item
        $('.qtyrefreshbutton').each(function(){
            $(this).click(function(){
                // Show an alert to confirm the action
                let shouldProceed = window.confirm("Are you sure you want to update this quantity?\nThis action CANNOT be undone.");
                // If the user confirms
                if (shouldProceed) {
                    const recordId = $(this).attr("data-countrecord-id");
                    const recordType = getURLParameter("recordType");
                    thisCountListWebSocket.refreshOnHand(recordId, recordType);
                }
            });
        });

        // update the checkbox color when the checkbox is clicked
        const updateCheckBoxCellColors = this.updateCheckBoxCellColors
        $('.counted-input').each(function(){
            $(this).change(function(){
                updateCheckBoxCellColors();
            })
        }) 

        // let listId = $('table#countsTable').attr('data-countlist-id');
        $('.discardButton').each(function(){
            $(this).click(function(){
                if (confirm("Are you sure you want to delete this record?")) {
                    const recordId = $(this).attr("data-countrecord-id");
                    const listId = $(this).attr("data-countlist-id");
                    const recordType = getURLParameter("recordType");
                    thisCountListWebSocket.deleteCount(recordId, recordType, listId);
                } else {
                    // Exit the function if the user cancels
                    return;
                } 
            });
        });

    };
};

export class MaxProducibleQuantityPage {
    constructor() {
        try {
            const urlParameters = new URLSearchParams(window.location.search);
            const itemCode = atob(urlParameters.get('itemCode'));
            const itemData = getMaxProducibleQuantity(itemCode, "NoComponentItemFilter", "itemCode");
            this.setMaxProducibleQuantityDiv(itemData)
            console.log("Instance of class MaxBlendCapacityForm created.");
        } catch(err) {
            console.error(err.message);
        }
    };

    setMaxProducibleQuantityDiv(itemData){
        $("#itemCodeAndDescription").text(`${itemData.item_code} ${itemData.item_description}:`);
        $("#max_producible_quantity").text(`${itemData.max_producible_quantity} gallons`);
        $("#max_producible_quantity").css('font-weight', 'bold');
        $("#limiting_factor").text(`${itemData.limiting_factor_item_code}: ${itemData.limiting_factor_item_description}`);
        $("#limiting_factor_onhand").text(
            `${Math.round(itemData.limiting_factor_quantity_onhand, 0)}
            ${itemData.limiting_factor_UOM} on hand now.
            ${Math.round(itemData.limiting_factor_OH_minus_other_orders)}  ${itemData.limiting_factor_UOM} available after all other usage is taken into account.`
            );
        if (itemData.limiting_factor_OH_minus_other_orders < 0) {
            $("#limiting_factor_onhand").css('color', 'red').css('font-weight', 'bold');
        }
        $("#next_shipment").text(`${itemData.next_shipment_date}`);
        if (Object.keys(itemData.consumption_detail[itemData.limiting_factor_item_code]).length > 1){
            $("#limiting_factor_usage_table_container").show()
            for (const key in itemData.consumption_detail[itemData.limiting_factor_item_code]) {
                let thisRow = document.getElementById("limiting_factor_usage_tbody").insertRow();
                let blendItemCodeCell = thisRow.insertCell(0);
                let blendDescriptionCell = thisRow.insertCell(1);
                blendDescriptionCell.innerHTML = itemData.consumption_detail[itemData.limiting_factor_item_code][key]['blend_item_description'];
                let blendQuantityCell = thisRow.insertCell(2);
                blendQuantityCell.innerHTML = (Math.round(itemData.consumption_detail[itemData.limiting_factor_item_code][key]['blend_total_qty_needed'])).toString() + ' gallons';
                let blendShortTimeCell = thisRow.insertCell(3);
                blendShortTimeCell.innerHTML = parseFloat(itemData.consumption_detail[itemData.limiting_factor_item_code][key]['blend_first_shortage']).toFixed(2).toString() + ' hours';
                let componentQuantityCell = thisRow.insertCell(4);
                componentQuantityCell.innerHTML = (Math.round(itemData.consumption_detail[itemData.limiting_factor_item_code][key]['component_usage'])).toString() + ' ' + itemData.limiting_factor_UOM;
                componentQuantityCell.style['text-align'] = 'right';
                if (key == 'total_component_usage'){
                    blendItemCodeCell.innerHTML = "TOTAL USAGE FOR OTHER ORDERS"
                    thisRow.style.backgroundColor = 'lightgray';
                    thisRow.style.fontWeight = 'bold';
                    blendDescriptionCell.innerHTML = '';
                    blendQuantityCell.innerHTML = '';
                    blendShortTimeCell.innerHTML = '';
                    componentQuantityCell.innerHTML = (Math.round(itemData.consumption_detail[itemData.limiting_factor_item_code]['total_component_usage']).toString() + ' ' + itemData.limiting_factor_UOM);
                } else {
                    blendItemCodeCell.innerHTML = key;
                }
            }
        };
        $("#component_quantity_header").text(`${itemData.limiting_factor_item_code} Qty Used`)
        $("#next_shipment_header").text(`Next Shipment of ${itemData.limiting_factor_item_code}:`)
        $("#blendCapacityContainer").show();
    }

};

export class BaseTemplatePage {
    constructor() {
        try {
            this.changeNavColor();
            this.checkRefreshStatus();
            this.setUpConnectionStatusCheck();
            console.log("Instance of class BaseTemplatePage created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    checkRefreshStatus(){
        let rStat;
        $.ajax({
            url: '/core/get-refresh-status/',
            async: false,
            dataType: 'json',
            success: function(data) {
                rStat = data;
            }
        });
        if (rStat.status == "down") {
            $("#refreshWarningLink").show();
        };
    };

    changeNavColor() {
        if (location.href.includes('localhost')){
            $("#theNavBar").removeClass('bg-primary');
            $("#theNavBar").prop('style', 'background-color:#ffa500;');
        };
    };

    setUpConnectionStatusCheck(){
        window.addEventListener('load', function() {
        var offlineBanner = document.getElementById('networkStatusBar');
        var myForm = document.querySelector('form');
        if (myForm){
            function updateOnlineStatus() {
                if(navigator.onLine) {
                  offlineBanner.style.display = 'none';
                  myForm.querySelector('button[type="submit"]').disabled = false;
                } else {
                  offlineBanner.style.display = 'block';
                  myForm.querySelector('button[type="submit"]').disabled = true;
                }
              }
              
              window.addEventListener('online', updateOnlineStatus);
              window.addEventListener('offline', updateOnlineStatus);
              
              updateOnlineStatus();
        };
        
      });
    };
      
};

export class DeskSchedulePage {
    constructor() {
        try {
            if (!window.location.href.includes("all")){
                this.setupDragnDrop();
            };
            this.setupEventListeners();
            this.addHxLotNumbers();
            console.log("Instance of class DeskSchedulePage created.");
        } catch(err) {
            console.error(err.message);
        };
    };


    setupDragnDrop(){
        // this function posts the current order on the page to the database
        function updateScheduleOrder(desk){
            let deskScheduleDict = {};
            let thisRow;
            $('#deskScheduleTable tbody tr').each(function() {
                thisRow = $(this);
                let orderNumber = $(this).find('td:eq(0)').text();
                let lotNumber = $(this).find('td:eq(4)').text();
                // Skip rows with an empty value in the second cell.
                if (lotNumber.trim() !== '') {
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
                }
            });
        };

        $(function () {
            // .sortable is a jquery function that makes your table
            // element drag-n-droppable.
            // Currently can't highlight text in the table cells.
            $("#deskScheduleTable").sortable({
                items: '.tableBodyRow',
                cursor: 'move',
                axis: 'y',
                dropOnEmpty: false,
                start: function (e, ui) {
                    ui.item.addClass("selected");
                },
                stop: function (e, ui) {
                    ui.item.removeClass("selected");
                    $(this).find("tr").each(function(index) {
                        if (index > 0) {
                            $(this).find("td").eq(0).html(index); // Set Order column cell = index value
                        }
                    });
                    updateScheduleOrder();
                }
            });
        });
    };

    setupEventListeners() {
        $(".tankSelect").change(function() {
            let lotNumber = $(this).parent().parent().find('td:eq(4)').text();
            let encodedLotNumber = btoa(lotNumber)
            let tank = $(this).val();
            let encodedTank = btoa(tank);
            let blendArea = new URL(window.location.href).searchParams.get("blend-area");
            let tankUpdateResult;
            $.ajax({
                url: `/core/update-scheduled-blend-tank?encodedLotNumber=${encodedLotNumber}&encodedTank=${encodedTank}&blendArea=${blendArea}`,
                async: false,
                dataType: 'json',
                success: function(data) {
                    tankUpdateResult = data;
                }
            });
            console.log(tankUpdateResult)
        });
    };
    addHxLotNumbers() {
        
    };

};

export class ItemsToCountPage {
    constructor() {
        try {
            this.setupEventListeners();
            console.log("Instance of class ItemsToCountPage created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    setupEventListeners(){
        // Event listener to show the dropdown and submit button
        $(".editIcon").click(function(e) {
            let thisItemId = $(this).attr("data-itemid");
            let thisItemCode = $(this).attr("data-itemcode");
            let thisAuditGroup = $(this).attr("data-auditgroup");
            $('#confirmChangeAuditGroup').attr("data-itemid", thisItemId);
            $('#confirmChangeAuditGroup').attr("data-auditgroup", thisAuditGroup);
            $("#itemCodeHeader").text(`Change Audit Group for ${thisItemCode}`);
            document.getElementById('changeAuditGroupDialog').showModal();
        });

        // Event listener to show the dialog when the custom option is selected
        $('.auditGroupDropdown').on('change', function(e) {
            const newAuditGroup = document.getElementById('customAuditGroupInput').value;
            const selectedValue = this.value;
            $('#confirmChangeAuditGroup').attr("data-auditgroup", selectedValue);
        });

        // Event listener for the custom group input
        $('#customAuditGroupInput').on('keyup', function() {
            $('#confirmChangeAuditGroup').attr("data-auditgroup", $(this).val());
        });

        // Clear the dropdown filter when user clicks into the input filter field
        $("#id_filter_criteria").on("focus", function(){
            // const selectElement = document.getElementById("auditGroupLinks");
            // selectElement.selectedIndex = 0;
            $("#auditGroupLinks").val("");
            
        });

        // Event listener for the "Confirm" button
        $('#confirmChangeAuditGroup').click(function(){
            let newAuditGroup = $(this).attr("data-auditgroup");
            let recordType = getURLParameter('recordType');
            let itemID = $(this).attr("data-itemid");
            let changeGroupURL = `/prodverse/add-item-to-new-group?redirectPage=items-to-count&auditGroup=${newAuditGroup}&recordType=${recordType}&itemID=${itemID}`;
            if (newAuditGroup.trim() !== '') { // make sure the audit group isn't blank
                window.location.replace(changeGroupURL);
            } else {
                alert('Please enter a valid audit group value.');
            };
        });

        // Event listener for the "Cancel" button
        $('#cancelChangeAuditGroup').on('click', function() {
            document.getElementById('changeAuditGroupDialog').close();
            $("#itemCodeHeader").text("");
        });
    }

};

export class CountCollectionLinksPage {
    constructor(thisCountCollectionWebSocket) {
        try {
            this.setupEventListeners(thisCountCollectionWebSocket);
            this.setupDragnDrop();
            console.log("Instance of class CountCollectionLinksPage created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    setupEventListeners(thisCountCollectionWebSocket) {
        document.querySelectorAll(".collectionNameElement").forEach(inputElement => {
            inputElement.addEventListener("keyup",function(){
                console.log("event happend")
                const collectionId = inputElement.getAttribute("collectionlinkitemid");
                const newName = inputElement.value;
                thisCountCollectionWebSocket.updateCollection(collectionId, newName);
            });
        });
        document.querySelectorAll(".collectionIdButton").forEach(buttonElement => {
            buttonElement.addEventListener("click",function(){
                const thisCollectionItemId = buttonElement.getAttribute("collectionlinkitemid");
                const thisCollectionIdInput = $(`input[collectionlinkitemid=${thisCollectionItemId}]`);
                // console.log(thisCollectionItemId);
                // console.log(thisCollectionIdInput.val());
                let result = updateCountCollection(thisCollectionItemId, thisCollectionIdInput.val());
                console.log(result);
                buttonElement.setAttribute("style", "display:none;");
            });
        });
        document.querySelectorAll(".deleteCountLinkButton").forEach(deleteButton => {
            deleteButton.addEventListener("click",function(){
                const collectionId = deleteButton.getAttribute("collectionlinkitemid");
                thisCountCollectionWebSocket.deleteCollection(collectionId);
            });
        });

        const observer = new MutationObserver(function(mutationsList) {
            for (let mutation of mutationsList) {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach(addedNode => {
                        if (addedNode.nodeType === 1 && addedNode.matches('.tableBodyRow')) {
                            const deleteButton = addedNode.querySelector('.deleteCountLinkButton');
                            if (deleteButton) {
                                deleteButton.addEventListener("click", function() {
                                    const collectionId = deleteButton.getAttribute("collectionlinkitemid");
                                    thisCountCollectionWebSocket.deleteCollection(collectionId);
                                });
                            }
                        }
                    });
                }
            }
        });

        observer.observe(document.querySelector('#countCollectionLinkTable tbody'), { childList: true });

    }

    setupDragnDrop(){
        // this function posts the current order on the page to the database
        function updateCollectionLinkOrder(){
            let collectionLinkDict = {};
            $('#countCollectionLinkTable tbody tr').each(function() {
                let orderNumber = $(this).find('td:eq(0)').text();
                let collectionID = $(this).find('td:eq(1)').attr('data-collection-id');
                // Skip rows with an empty value in the second cell.
                if (collectionID.trim() !== '') {
                    collectionLinkDict[collectionID] = orderNumber;
                }
            });
            let jsonString = JSON.stringify(collectionLinkDict);
            let encodedCollectionLinkOrder = btoa(jsonString);
            let orderUpdateResult;
            $.ajax({
                url: `/core/update-collection-link-order?encodedCollectionLinkOrder=${encodedCollectionLinkOrder}`,
                async: false,
                dataType: 'json',
                success: function(data) {
                    orderUpdateResult = data;
                }
            });
            console.log(orderUpdateResult);
        };

        $(function () {
            // .sortable is a jquery function that makes your table
            // element drag-n-droppable.
            // Currently can't highlight text in the table cells.
            $("#countCollectionLinkTable").sortable({
                items: '.tableBodyRow',
                cursor: 'move',
                axis: 'y',
                dropOnEmpty: false,
                start: function (e, ui) {
                    ui.item.addClass("selected");
                },
                stop: function (e, ui) {
                    ui.item.removeClass("selected");
                    $(this).find("tr").each(function(index) {
                        if (index > 0) {
                            $(this).find("td").eq(0).html(index); // Set Order column cell = index value
                        }
                    });
                    updateCollectionLinkOrder();
                }
            });
        });
    };
    
};

export class CountReportPage {
    constructor() {
        try {
            this.setupEventListeners();
            console.log("Instance of class CountReportPage created.");
        } catch(err) {
            console.error(err.message);
            console.log("Error", err.stack);
            console.log("Error", err.name);
            console.log("Error", err.message);
        };
    };
};

export class BlendInstructionEditorPage {
    constructor() {
        try {
            this.setupDragnDrop();
            this.setupEventListeners();
            this.setReadOnlyFields();
            this.setupFormMonitoring();
            console.log("Instance of class BlendInstructionEditorPage created.");
        } catch(err) {
            console.error(err.message);
        };
    };


    setupDragnDrop(){
        $(function () {
            // .sortable is a jquery function that makes your table
            // element drag-n-droppable.
            // Currently can't highlight text in the table cells.
            $("#blendInstructionTable").sortable({
                items: '.tableBodyRow',
                cursor: 'move',
                axis: 'y',
                dropOnEmpty: false,
                start: function (e, ui) {
                    ui.item.addClass("selected");
                },
                stop: function (e, ui) {
                    ui.item.removeClass("selected");
                    $(this).find("tr").each(function(index) {
                        if (index > 0 && !($(this).attr('id') === 'addNewInstructionRow')) {
                            $(this).find("td").eq(0).find('input').val(index); // Set Order column cell = index value
                        }
                    });
                    updateBlendInstructionsOrder();
                }
            });
        });
    };

    setupEventListeners(){
        document.getElementById("addNewInstructionButton").addEventListener('click', function(e){
            e.preventDefault();
            const encodedItemCode = getURLParameter("itemCode");
            const newBlendInstructionInfo = getNewBlendInstructionInfo(encodedItemCode);
            console.log(newBlendInstructionInfo)

            // Get the formset's total forms input element and obtain the form count
            let totalForms = document.querySelector('input[name="form-TOTAL_FORMS"]');
            let formNum = parseInt(totalForms.value);
            
            // // Get the last form in the formset, which is the second to last row in the 
            // // table due to the row containing the Add New button.
            let table = document.getElementById("blendInstructionTable");
            let rows = table.tBodies[0].children;
            let secondToLastRow = rows[rows.length - 2];
            let newRow = secondToLastRow.cloneNode(true);

            // // Update the new form's input elements to use the new form count
            newRow.querySelectorAll('input, select, textarea').forEach(function(input) {
                input.name = input.name.replace('-' + (formNum - 1) + '-', '-' + formNum + '-');
                input.id = input.id.replace('-' + (formNum - 1) + '-', '-' + formNum + '-');
            });
            newRow.querySelectorAll('td').forEach(function(tdCell) {
                tdCell.setAttribute('data-item-id', newBlendInstructionInfo.next_id) 
            })
            
            newRow.querySelector('input[name*="step_number"]').value = formNum + 1;
            newRow.querySelector('input[name*="step_description"]').value = "";
            newRow.querySelector('input[name*="component_item_code"]').value = "";
            newRow.querySelector('input[name*="id"]').value = newBlendInstructionInfo.next_id;
            newRow.querySelector('.deleteBtn').setAttribute('data-item-id', newBlendInstructionInfo.next_id)


            let lastRow = table.tBodies[0].lastElementChild;

            // Insert the new form before the "Add New" button row
            lastRow.parentNode.insertBefore(newRow, document.getElementById('addNewInstructionRow'));

            // Increment the form count
            totalForms.value = formNum + 1;

            // console.log();
        })
    }

    setReadOnlyFields() {
        $('input[name*="step_number"]').prop('readonly', true); 
        $('input[name*="step_number"]').css('pointer-events', 'none');
    }

    setupFormMonitoring(){
        let formIsDirty = false;
        document.querySelector('form').addEventListener('input', function () {
            formIsDirty = true;
        });

        document.querySelector('#saveInstructionsButton').addEventListener('click', function () {
            formIsDirty = false;
        });

        window.addEventListener('beforeunload', function (e) {
            if (formIsDirty) {
                e.preventDefault();
                e.returnValue = '';
            }
        });
    }
};

export class PartialContainerLabelPage {
    constructor() {
        try {
            this.setupEventListeners();
            console.log("Instance of class PartialContainerLabelPage created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    setupEventListeners() {
        $("#label-container-type-dropdown").on('change', function(e) {
            $(".error-message").each(function(){
                $(this).remove();
            });
            $("#gross-weight, #label-container-type-dropdown, #inventory-label-container-type, #inventory-label-item-code").css({"color": "", "font-weight": ""});
            let selectedContainerWeight = this.value;
            let selectedContainerType = $("#label-container-type-dropdown option:selected").text()
            if (selectedContainerWeight == "CUSTOM") {
                $("#custom-tare-container").show();
                $("#inventory-label-container-weight").css("color", "red").css("font-weight", "bold").text("Enter container weight.");
                $("#inventory-label-container-type").css("color", "").css("font-weight", "").text(selectedContainerType);
            } else {
                $("#custom-tare-container").hide();
                $("#inventory-label-container-weight").css("color", "").css("font-weight", "").text(selectedContainerWeight);
                $("#inventory-label-container-type").css("color", "").css("font-weight", "").text(selectedContainerType);
            }
            if ($("#gross-weight").val()) {
                let grossWeight = $("#gross-weight").val();
                let tareWeight = $("#inventory-label-container-weight").text();
                netWeight = (grossWeight - tareWeight)
                $("#net-weight").text(netWeight + " lbs.");
                let itemCode = $("#inventory-label-item-code").text();
                updateVolume(netWeight, itemCode)
            }
        });

        $("#gross-weight").keyup(function(e) {
            $(".error-message").each(function(){
                $(this).remove();
            });
            $("#gross-weight, #label-container-type-dropdown, #inventory-label-container-type, #inventory-label-item-code").css({"color": "", "font-weight": ""});
            let grossWeight = this.value;
            let tareWeight = $("#inventory-label-container-weight").text();
            let itemCode = $("#inventory-label-item-code").text();
            if (!tareWeight) {
                $("#inventory-label-container-type").css("color", "red").css("font-weight", "bold").text("Please select container.");
            } else {
                // $("#inventory-label-container-type").css("color", "").text($("#label-container-type-dropdown option:selected").text());
                let netWeight = grossWeight - tareWeight
                $("#net-weight").text(netWeight + " lbs.");
                updateVolume(netWeight, itemCode);
            }
            
            // $("#net-weight").text(grossWeight);
        });

        $("#custom-tare-weight").keyup(function(e) {
            $(".error-message").each(function(){
                $(this).remove();
            });
            $("#gross-weight, #label-container-type-dropdown, #inventory-label-container-type, #inventory-label-item-code, #initialsField").css({"color": "", "font-weight": ""});
            let tareWeight = this.value;
            $("#inventory-label-container-weight").css("color", "").css("font-weight", "").text(tareWeight);
        });

        function updateVolume(netWeight, itemCode) {
            $(".error-message").each(function(){
                $(this).remove();
            });
            $("#gross-weight, #label-container-type-dropdown, #inventory-label-container-type, #inventory-label-item-code, #initialsField").css({"color": "", "font-weight": ""});
            let itemInfo = getItemInfo(itemCode, "itemCode");
            let shipWeight = itemInfo.shipweight;
            let standardUOM = itemInfo.standardUOM;

            if (!shipWeight) {
                $("#net-gallons").text("N/A");
            } else {
                $("#net-gallons").text((netWeight / shipWeight).toFixed(2) + " gal");
            }
           
        }
        $("#initialsField").css("text-transform", "uppercase");
        $("#initialsField").click(function(e) {
            $(".error-message").each(function(){
                $(this).remove();
            });
            $("#gross-weight, #label-container-type-dropdown, #inventory-label-container-type, #inventory-label-item-code, #initialsField").css({"color": "", "font-weight": ""});

        })
        
        $("#blendLabelPrintButton").click(function(e) {
            let hasError = false;
            let grossWeight = $("#gross-weight").val();
            let containerType = $("#inventory-label-container-type").text();
            let itemCode = $("#inventory-label-item-code").text();
            let initials = $("#initialsField").val();

            // Reset previous error states
            $(".error-message").remove();
            $("#gross-weight, #label-container-type-dropdown").css({"color": "", "font-weight": ""});

            if (!grossWeight) {
                $("#gross-weight").after('<div class="error-message" style="color: red; font-weight: bold;">Please enter weight.</div>');
                $("#gross-weight").css({"color": "red", "font-weight": "bold"});
                hasError = true;
            }

            if (!initials) {
                $("#initialsField").after('<div class="error-message" style="color: red; font-weight: bold;">Please initial.</div>');
                $("#initialsField").css({"color": "red", "font-weight": "bold"});
                hasError = true;
            }

            if (!containerType) { // Replace 'defaultOptionValue' with your actual default option value if any
                $("#inventory-label-container-type").after('<div class="error-message" style="color: red; font-weight: bold;">Please select container type.</div>');
                $("#inventory-label-container-type").css({"color": "red", "font-weight": "bold"});
                hasError = true;
            }

            if (!itemCode) { // Replace 'defaultOptionValue' with your actual default option value if any
                $("#inventory-label-item-code").after('<div class="error-message" style="color: red; font-weight: bold;">Please enter item code.</div>');
                $("#inventory-label-item-code").css({"color": "red", "font-weight": "bold"});
                hasError = true;
            }

            if (hasError) {
                e.preventDefault(); // Prevent form submission if there are errors
            } else {
                let encodedItemCode = btoa(itemCode);
                logContainerLabelPrint(encodedItemCode);
            }
            
        });
        // Place this code in a suitable location within your script, such as inside a constructor or initialization function

        // Select the target node
        let target = document.getElementById('inventory-label-item-description');

        // Create an observer instance
        let observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                let itemDescription = mutation.target.textContent;
                let itemCode = $("#inventory-label-item-code").text();
                let itemInfo = getItemInfo(itemCode, "itemCode");
                let shipWeight = itemInfo.shipweight;
                let standardUOM = itemInfo.standardUOM;
                if (itemDescription.startsWith("BLEND")) {
                    $("#label-container-select-row").hide();
                    $("#custom-tare-container").hide();
                    $("#custom-tare-container").hide();
                    $("#containerTypeRow").hide();
                    $("#containerWeightRow").hide();
                    $("#grossWeightRow").hide();
                    $("#netWeightRow").hide();
                    $("#inputHolderTable")
                    $("#net-gallons").html('<input type="text" id="net-gallons-input" name="net_gallons" value="" />');
                } else {
                    $("#label-container-select-row").show();
                    $("#custom-tare-container").show();
                    $("#custom-tare-container").show();
                    // $("#containerTypeRow").show();
                    $("#containerWeightRow").show();
                    $("#grossWeightRow").show();
                    $("#netWeightRow").show();
                    $("#net-gallons-input").remove();
                };
            });
        });

        // Configuration of the observer--????:
        var config = { characterData: true, childList: true, subtree: true };
        // Pass in the target node, as well as the observer options
        observer.observe(target, config);

        // Later, you can stop observing
        // observer.disconnect();

    };
};

export class MissingAuditGroupPage {
    constructor() {
        try {
            this.setupEventListeners();
            console.log("Instance of class MissingAuditGroupPage created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    setupEventListeners() {
        $(".discardButton").click(function(e) {
            e.preventDefault(); // Prevent the default event
            $(this).parent().parent().remove(); // Remove the grandparent element
        });
    };
};

export class ListToCountListPage {
    constructor() {
        try {
            this.setupEventListeners();
            console.log("Instance of class MissingAuditGroupPage created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    setupEventListeners() {
        $("#listField").keyup(function(e) {
            // Clear existing table content
            $("#itemTable tbody").empty();
            
            // Split the input by newlines
            var lines = $(this).val().split('\n');
            
            // Create table rows for each non-empty line
            lines.forEach(function(line) {
                if (line.trim() !== '') {
                    var newRow = $("<tr>");
                    var checkboxCell = $("<td>").append(
                        $("<input>")
                            .attr("type", "checkbox")
                            .prop("checked", true)
                    );
                    var contentCell = $("<td>").text(line.trim());
                    
                    newRow.append(checkboxCell).append(contentCell);
                    $("#itemTable tbody").append(newRow);
                }
            });
        });
    };
};