import { getMaxProducibleQuantity, getBlendSheet, getBlendSheetTemplate, getURLParameter, getNewBlendInstructionInfo, getBlendCrewInitials, getItemInfo } from '../requestFunctions/requestFunctions.js'
import { updateCountCollection } from '../requestFunctions/updateFunctions.js'
import { updateBlendInstructionsOrder, logContainerLabelPrint } from '../requestFunctions/updateFunctions.js'
import { ItemReferenceFieldPair } from './lookupFormObjects.js'

export class CountListPage {
    constructor() {
        try {
            this.setupVarianceCalculation();
            this.setupDiscardButtons();
            this.setupFieldattributes();
            this.setUpEventListeners();
            this.updateCheckBoxCellColors();
            this.setupLabelLinks();
            console.log("Instance of class CountListPage created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    setupVarianceCalculation(){
        function calculateVariance(eventTarget) {
            let expected_quantity = eventTarget.parent().prev('td').children().first().val();
            let counted_quantity = eventTarget.val();
            let variance = counted_quantity - expected_quantity;
            let formNumber = eventTarget.prop('name').replace('-counted_quantity', '');
            eventTarget.parent().next('td').next('td').children().prop('value', variance.toFixed(4));
            eventTarget.parent().next('td').next('td').next('td').children().children().prop( "checked", true );
        }
        $('input[id*=counted_quantity]').blur(function(){
            calculateVariance($(this));
        });
        $('input[id*=counted_quantity]').focus(function(){
            calculateVariance($(this));
        });
        $('input[id*=counted_quantity]').keyup(function(){
            calculateVariance($(this));
        });
    };

    setupDiscardButtons() {
        let fullEncodedList = $("#encodedListDiv").attr("encoded-list");
        let thisRowIdEncoded;
        let thisRowID;
        let urlParameters = new URLSearchParams(window.location.search);
        let recordType = urlParameters.get('recordType');
        let redirectPage;
        if (window.location.href.includes("count-list")) {
            redirectPage = "count-list";
        } else if (window.location.href.includes("count-records")) {
            redirectPage = "count-records";
        };
        $('.discardButtonCell').each(function(){
            thisRowID = $(this).prev().children().first().attr("value");
            thisRowIdEncoded = btoa(thisRowID)
            
            $(this).children().first().attr("href", `/core/delete-count-record?redirectPage=${redirectPage}&listToDelete=${thisRowIdEncoded}&fullList=${fullEncodedList}&recordType=${recordType}`)
        });
        $("#discardAllButton").attr('href', `/core/delete-count-record?redirectPage=count-records&listToDelete=${fullEncodedList}&fullList=${fullEncodedList}&recordType=${recordType}`)
    };

    setupFieldattributes() {
        let missedaCount = true;
        $('.tbl-cell-counted_date, .tbl-cell-variance, .tbl-cell-counted, .tbl-cell-count_type').addClass('noPrint');
        $('input[type="number"]').each(function(){
            $(this).attr("value", parseFloat(($(this).attr("value"))).toFixed(4));
        });
        $('input[name*="counted_quantity"]').each(function(){
            $(this).attr("value", Math.round($(this).attr("value")));
        });
        $('input[type=hidden]').each(function() {
            $(this).parent('td').attr('style', "display:none;");
        });
        $('input').each(function() {
            $(this).attr('tabindex', '-1');
            if (!$(this).id=='id_item_code' && $(this).id=='id_item_description') {
                $(this).attr('readonly', true);
            }
        });
        $('.discardButton').each(function() {
            $(this).attr('tabindex', '-1');
        });
        $('input[id*="counted_quantity"]').each(function() {
            $(this).attr('tabindex', '0');
            $(this).removeAttr('readonly');
            //$(this).on('focus', function() {
            //});
        });
        $('input[id*="counted_date"]').each(function() {
            $(this).removeAttr('readonly');
        });
        $('#id_countListModal_item_code').removeAttr('readonly');
        $('#id_countListModal_item_description').removeAttr('readonly');
        
        // THIS USED TO PREVENT SAVING UNLESS EVERY FIELD HAD BEEN TOUCHED BUT
        // IT REALLY ISNT NECESSARY SO I'M COMMENTING IT OUT
        // $('#saveCountsButton').on('click', function(e){
        //     missedaCount = false;
        //     $('input[id*="counted_quantity"]').each(function(e) {
        //         if (!($(this).hasClass('entered'))) {
        //             $(this).addClass('missingCount');
        //             missedaCount = true;
        //         }
        //         $(this).on('focus', function() {
        //             $(this).addClass('entered')
        //         });
        //     });   
        //     if (missedaCount) {
        //         e.preventDefault();
        //         alert("Please fill in the missing counts.");
        //     };
        // });

        $('input[id*="-item_description"]').each(function(){
            let thisFormNumber = $(this).attr("id").slice(3,10);
            if (thisFormNumber.slice(6,7) == "-"){
                thisFormNumber = thisFormNumber.slice(0,6);
            };
            if ($(this).val().includes("BLEND")) {
                $(`#id_${thisFormNumber}-count_type`).val("blend");
            } else {$(`#id_${thisFormNumber}-count_type`).val("component")};
        });

        // Prevent the enter key from submitting the form
        $('table').keypress(function(event){
            if (event.which == '13') {
                event.preventDefault();
            };
        }); 
        
        const commentFields = document.querySelectorAll('textarea');
        commentFields.forEach((field) => {
            field.setAttribute("rows", "1");
            field.setAttribute("cols", "10");
        });


    };

    // convertCheckBoxesToSwitches(){
    //     const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    //     checkboxes.forEach((checkbox) => {
    //         // Create the <div> element
    //         const div = document.createElement('div');
    //         div.classList.add('form-check', 'form-switch');
    //         // Clone the checkbox and add it to the <div>
    //         const clonedCheckbox = checkbox.cloneNode();
    //         clonedCheckbox.classList.add('form-check-input', 'text-center');
    //         div.appendChild(clonedCheckbox);
    //         checkbox.parentNode.replaceChild(div, checkbox);
    //     });
    // };

    updateCheckBoxCellColors() {
        console.log("hello")
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

    setUpEventListeners() {
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
                    let itemInformation;
                    let itemcode = $(this).attr('itemcode');
                    let encodedItemcode = btoa(itemcode);
                    $.ajax({
                        url: '/core/item-info-request?lookup-type=itemCode&item=' + encodedItemcode,
                        async: false,
                        dataType: 'json',
                        success: function(data) {
                            itemInformation = data;
                        }
                    });
                    let correspondingID = $(this).attr('correspondingrecordid');
                    console.log(itemInformation.qtyOnHand)
                    $(`td[data-countrecord-id="${correspondingID}"]`).find("input[name*='expected_quantity']").val(parseFloat(itemInformation.qtyOnHand).toFixed(4));
                }
            });
        });

        const updateCheckBoxCellColors = this.updateCheckBoxCellColors

        $('.tbl-cell-counted').each(function(){
            $(this).click(function(){
                updateCheckBoxCellColors();
            })
        }) 

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
            this.setupDragnDrop();
            console.log("Instance of class DeskSchedulePage created.");
        } catch(err) {
            console.error(err.message);
        };
    };


    setupDragnDrop(){
        // this function posts the current order on the page to the database
        function updateScheduleOrder(){
            let deskScheduleDict = {};
            if (window.location.href.includes("Desk_1")){
                deskScheduleDict["desk"] = "Desk_1";
            } else if (window.location.href.includes("Desk_2")) {
                deskScheduleDict["desk"] = "Desk_2";
            };
            $('#deskScheduleTable tbody tr').each(function() {
                let orderNumber = $(this).find('td:eq(0)').text();
                let lotNumber = $(this).find('td:eq(3)').text();
                // Skip rows with an empty value in the second cell.
                if (lotNumber.trim() !== '') {
                    deskScheduleDict[lotNumber] = orderNumber;
                }
            });
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

};

export class ItemsToCountPage {
    constructor() {
        try {
            this.setupEventListeners();
            console.log("Instance of class DeskSchedulePage created.");
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
            let urlParameters = new URLSearchParams(window.location.search);
            let recordType = urlParameters.get('recordType');
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

export class BlendSheetPage {
    constructor() {
        try {
            this.populateBlendSheetContainer();
            this.setupEventListeners();
            console.log("Instance of class BlendSheetPage created.");
        } catch(err) {
            console.error(err.message);
        };
    };


    populateBlendSheetContainer() {
        let urlParameters = new URLSearchParams(window.location.search);
        let lotNumber = urlParameters.get('lotNumber');
        const blendSheet = getBlendSheet(lotNumber);
        this.createBlendSheetHeader(blendSheet);
        this.generateIngredientsTable(blendSheet);
        this.generateStepsTable(blendSheet);
    };

    createBlendSheetHeader(blendSheet){
        const blendSheetHeader = $("#blendSheetHeader");
        $("#itemCode").text(blendSheet.item_code);
        $("#itemDescription").text(blendSheet.item_description);
        $("#referenceNumber").text(blendSheet.formula_reference_no);
        $("#lastEditDate").text(blendSheet.last_edit_date);
        $("#preparedBy").text(blendSheet.prepared_by + "--");
        $("#preparedDate").text(blendSheet.prepared_date);
        $("#lbsPerGallon").text(blendSheet.lbs_per_gallon);
        $("#batchQuantity").text(blendSheet.batch_quantity);
        $("#batchWeight").text(blendSheet.batch_quantity * blendSheet.lbs_per_gallon);
        $("#lotNumber").text(blendSheet.lot_number);
        $("#processPreparation").text(blendSheet.process_preparation);
    };

    generateIngredientsTable(blendSheet) {
        const ingredientsTbody = $("#blendSheetIngredientsTbody");
        for (const key in blendSheet.ingredients) {
            const ingredientData = blendSheet.ingredients[key];
            const ingredientRow = $("<tr>").addClass("ingredientsRow");
            const itemCodeCell = $("<td>").text(blendSheet.ingredients[key]["item_code"]);
            ingredientRow.append(itemCodeCell);
            const quantityRatioCell = $("<td>").text((blendSheet.ingredients[key]["quantity_ratio"]*100).toFixed(4)+'%');
            ingredientRow.append(quantityRatioCell);
            const itemDescriptionCell = $("<td>").text(blendSheet.ingredients[key]["item_description"]);
            ingredientRow.append(itemDescriptionCell);
            const itemQtyNeededCell = $("<td>").text(blendSheet.ingredients[key]["qty_needed"]);
            ingredientRow.append(itemQtyNeededCell);
            const itemUnitCell = $(`<td class=${blendSheet.ingredients[key]["unit"]}>`).text(blendSheet.ingredients[key]["unit"]);
            ingredientRow.append(itemUnitCell);

            // create the qty_added input and td
            const qtyUsedCell = $("<td>").addClass("text-center");
            const qtyUsedInput = document.createElement("input");
            qtyUsedInput.setAttribute("id", `${key}_qty_added`);
            qtyUsedInput.setAttribute("category", "ingredients");
            qtyUsedInput.setAttribute("number", key);
            qtyUsedInput.setAttribute("key", "qty_added");
            qtyUsedInput.value = blendSheet.ingredients[key]["qty_added"];
            qtyUsedCell.append(qtyUsedInput);
            ingredientRow.append(qtyUsedCell);

            // create the chem_lot_number input and td
            const chemLotNumberCell = $("<td>").addClass("text-center");
            const chemLotNumberInput = document.createElement("input");
            chemLotNumberInput.setAttribute("id", `${key}_chem_lot_number`);
            chemLotNumberInput.setAttribute("category", "ingredients");
            chemLotNumberInput.setAttribute("number", key);
            chemLotNumberInput.setAttribute("key", "chem_lot_number");
            chemLotNumberInput.value = blendSheet.ingredients[key]["chem_lot_number"];
            chemLotNumberCell.append(chemLotNumberInput);
            ingredientRow.append(chemLotNumberCell);

            // create the checked_by select and td
            const checkedByCell = $("<td>").addClass("text-center");
            const checkedBySelect = document.createElement("select");
            checkedBySelect.setAttribute("id", `${key}_checked_by`);
            checkedBySelect.setAttribute("category", "ingredients");
            checkedBySelect.setAttribute("number", key);
            checkedBySelect.setAttribute("key", "checked_by");
            checkedBySelect.value = blendSheet.ingredients[key]["checked_by"];
            checkedByCell.append(checkedBySelect);
            ingredientRow.append(checkedByCell);

            // create the double_checked_by select and td
            const doubleCheckedByCell = $("<td>").addClass("text-center");
            const doubleCheckedBySelect = document.createElement("select");
            doubleCheckedBySelect.setAttribute("id", `${key}_double_checked_by`);
            doubleCheckedBySelect.setAttribute("category", "ingredients");
            doubleCheckedBySelect.setAttribute("number", key);
            doubleCheckedBySelect.setAttribute("key", "double_checked_by");
            doubleCheckedBySelect.value = blendSheet.ingredients[key]["double_checked_by"];
            doubleCheckedByCell.append(doubleCheckedBySelect);
            ingredientRow.append(doubleCheckedByCell);

            ingredientsTbody.append(ingredientRow);

        };
        this.setupCheckedByFields(blendSheet)
    };

    setupCheckedByFields(blendSheet) {
        // Make sure the second Joe C's initials are changed to JCjr
        let initialsList = getBlendCrewInitials();
        let found = false;
        for (let i = 0; i < initialsList.length; i++) {
            if (initialsList[i] === "JC" && !found) {
                initialsList[i] = "JCjr";
                found = true;
            };
        };

        // 
        const selectElements = $("[id*=checked_by")
        selectElements.each(function() {
            const firstOption = $("<option>");
            firstOption.val("");
            $(this).append(firstOption);
            initialsList.forEach(item => {
                const option = $("<option>");
                option.val(item); // Set the value attribute directly
                option.text(item);
                $(this).append(option);
            });
            const thisCategory = $(this).attr("category");
            const thisNumber = $(this).attr("number");
            const thisKey = $(this).attr("key");
            const targetValue = blendSheet[thisCategory][thisNumber][thisKey];
            for (let i = 0; i < this.options.length; i++) {
                const option = this.options[i];
                if (option.value === targetValue) {
                  option.selected = true;
                  break; // Once we find the desired option, we can exit the loop
                }
              }
        });
    }
    
    // $(this).val(`option text=[${blendSheet[thisCategory][thisNumber][thisKey]}]`);

    generateStepsTable(blendSheet) {
        const stepsTbody = $("#blendSheetStepsTbody");

        for (const key in blendSheet.steps) {
            const stepRow = $("<tr>").addClass("stepsRow");
            const stepNumberCell = $("<td>").text(blendSheet.steps[key]["number"]).addClass("text-center");
            stepRow.append(stepNumberCell);
            const stepDescriptionCell = $("<td>").text(blendSheet.steps[key]["description"]);
            stepRow.append(stepDescriptionCell);
            const stepUnitCell = $(`<td class=${blendSheet.steps[key]["unit"]}>`).text(blendSheet.steps[key]["unit"]);
            stepRow.append(stepUnitCell);
            const stepItemCodeCell = $("<td>").text(blendSheet.steps[key]["item_code"]);
            stepRow.append(stepItemCodeCell);

            // create the notes input and td
            const stepNotesCell = $("<td>").addClass("text-center");
            const stepNotesInput = document.createElement("input");
            stepNotesInput.setAttribute("id", `${key}_notes`);
            stepNotesInput.setAttribute("category", "steps");
            stepNotesInput.setAttribute("number", key);
            stepNotesInput.setAttribute("key", "notes");
            stepNotesInput.value = blendSheet.steps[key]["notes"];
            stepNotesCell.append(stepNotesInput);
            stepRow.append(stepNotesCell);

            // create the start_time input and td
            const stepStartTimeCell = $("<td>").addClass("text-center");
            const stepStartTimeInput = document.createElement("input");
            stepStartTimeInput.setAttribute("id", `${key}_start_time`);
            stepStartTimeInput.setAttribute("category", "steps");
            stepStartTimeInput.setAttribute("number", key);
            stepStartTimeInput.setAttribute("key", "start_time");
            stepStartTimeInput.setAttribute("type", "time");
            stepStartTimeInput.value = blendSheet.steps[key]["start_time"];
            stepStartTimeCell.append(stepStartTimeInput);
            stepRow.append(stepStartTimeCell);

            // create the end_time input and td
            const stepEndTimeCell = $("<td>").addClass("text-center");
            const stepEndTimeInput = document.createElement("input");
            stepEndTimeInput.setAttribute("id", `${key}_end_time`);
            stepEndTimeInput.setAttribute("category", "steps");
            stepEndTimeInput.setAttribute("number", key);
            stepEndTimeInput.setAttribute("key", "end_time");
            stepEndTimeInput.setAttribute("type", "time");
            stepEndTimeInput.value = blendSheet.steps[key]["end_time"];
            stepEndTimeCell.append(stepEndTimeInput);
            stepRow.append(stepEndTimeCell);

            stepsTbody.append(stepRow);
        }
    };

    

    updateServerState(targetElement) {
        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie != '') {
                let cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    let cookie = jQuery.trim(cookies[i]);
                    // Does this cookie string begin with the name we want?
                    if (cookie.substring(0, name.length + 1) == (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    };
                };
            };
            return cookieValue;
        };

        function getFormattedDate() {
            const today = new Date();
            const month = String(today.getMonth() + 1).padStart(2, "0");
            const day = String(today.getDate()).padStart(2, "0");
            const year = today.getFullYear();
          
            return `${month}/${day}/${year}`;
          }

        const csrftoken = getCookie('csrftoken');
        let urlParameters = new URLSearchParams(window.location.search);
        let lotNumber = urlParameters.get('lotNumber');
        const blendSheet = getBlendSheet(lotNumber);
        const thisCategory = targetElement.getAttribute("category");
        const thisNumber = targetElement.getAttribute("number");
        const thisKey = targetElement.getAttribute("key");
        const thisValue = targetElement.value;
        blendSheet[thisCategory][thisNumber][thisKey] = thisValue;
        blendSheet['last_edit_date'] = getFormattedDate();

        function csrfSafeMethod(method) {
            // these HTTP methods do not require CSRF protection
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        };

        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                };
            }
        });

        $.ajax({
            type: "POST",
            url: window.location.pathname,
            data: JSON.stringify(blendSheet),
            success: function() {
                console.log("Updated server state");
            },
            error: function(error) {
                console.error(error);
            }
        });
    };

    setupEventListeners() {
        const updateServerState = this.updateServerState
        $("select").change(function(e){
            updateServerState(e.currentTarget);
        });
        $("input").change(function(e){
            updateServerState(e.currentTarget);
        });
    };

};

export class CountCollectionLinksPage {
    constructor() {
        try {
            this.setupEventListeners();
            console.log("Instance of class CountCollectionLinksPage created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    setupEventListeners() {
        document.querySelectorAll(".collectionIdInput").forEach(inputElement => {
            inputElement.addEventListener("click",function(){
                const thisButton = $(`button[collectionlinkitemid=${inputElement.getAttribute("collectionlinkitemid")}]`);
                thisButton.show();
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
        
    }
    
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
        $("#label-container-type-dropdown").click(function(e) {
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
                if (standardUOM == "GAL") {
                    $("#net-gallons").text((netWeight * shipWeight).toFixed(2) + " gal");
                } else if (standardUOM == "LB" || standardUOM == "LBS") {
                    $("#net-gallons").text((netWeight / shipWeight).toFixed(2) + " gal");
                };
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
                    $("#containerTypeRow").show();
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
