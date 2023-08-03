import { getMaxProducibleQuantity, getBlendSheet, getBlendSheetTemplate, getBlendCrewInitials } from '../requestFunctions/requestFunctions.js'

export class CountListPage {
    constructor() {
        try {
            this.setupVarianceCalculation();
            this.setupDiscardButtons();
            this.setupFieldattributes();
            this.convertCheckBoxesToSwitches();
            console.log("Instance of class CountListPage created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    setupVarianceCalculation(){
        $('input[id*=counted_quantity]').blur(function(){
            let expected_quantity = $(this).parent().prev('td').children().first().val();
            let counted_quantity = $(this).val();
            let variance = counted_quantity - expected_quantity;
            let formNumber = $(this).prop('name').replace('-counted_quantity', '');
            $(this).parent().next('td').next('td').children().prop('value', variance.toFixed(4));
            $(this).parent().next('td').next('td').next('td').children().children().prop( "checked", true );
            $(this).addClass('entered')
                if ($(this).hasClass('missingCount')) {
                    $(this).removeClass('missingCount');
                };
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
            $(this).attr('readonly', true)
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
        
        $('#saveCountsButton').on('click', function(e){
            missedaCount = false;
            $('input[id*="counted_quantity"]').each(function(e) {
                if (!($(this).hasClass('entered'))) {
                    $(this).addClass('missingCount');
                    missedaCount = true;
                }
                $(this).on('focus', function() {
                    $(this).addClass('entered')
                });
            });   
            if (missedaCount) {
                e.preventDefault();
                alert("Please fill in the missing counts.");
            };
        });

        $('input[id*="-item_description"]').each(function(){
            let thisFormNumber = $(this).attr("id").slice(3,10);
            if (thisFormNumber.slice(6,7) == "-"){
                thisFormNumber = thisFormNumber.slice(0,6);
            };
            if ($(this).val().includes("BLEND")) {
                $(`#id_${thisFormNumber}-count_type`).val("blend");
            } else {$(`#id_${thisFormNumber}-count_type`).val("component");

            };
            
        });

        // Prevent the enter key from submitting the form
        $('table').keypress(function(event){
            if (event.which == '13') {
                event.preventDefault();
            };
        });   
    };

    convertCheckBoxesToSwitches(){
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach((checkbox) => {
            // Create the <div> element
            const div = document.createElement('div');
            div.classList.add('form-check', 'form-switch');
            // Clone the checkbox and add it to the <div>
            const clonedCheckbox = checkbox.cloneNode();
            clonedCheckbox.classList.add('form-check-input', 'text-center');
            div.appendChild(clonedCheckbox);
            checkbox.parentNode.replaceChild(div, checkbox);
        });
    };

    setUpEventListeners(){
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach((checkbox) => {
            checkbox.addEventListener("click", function(){
                // console.log(e.currentTarget);
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
            ${itemData.limiting_factor_UOM} on hand now --
            ${Math.round(itemData.limiting_factor_OH_minus_other_orders)}  ${itemData.limiting_factor_UOM} available after all other usage is taken into account.`
            );
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
        $("#processPreparation").text(blendSheet.process_preparation)
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

}

export class BlendSheetTemplatePage {
    constructor() {
        try {
            this.populateBlendSheetTemplateContainer();
            this.setupEventListeners();
            console.log("Instance of class BlendSheetTemplatePage created.");
        } catch(err) {
            console.error(err.message);
            console.log("Error", err.stack);
            console.log("Error", err.name);
            console.log("Error", err.message);
        };
    };

    populateBlendSheetTemplateContainer() {
        let urlParameters = new URLSearchParams(window.location.search);
        let itemCode = urlParameters.get('itemCode');
        const blendSheetTemplate = getBlendSheetTemplate(itemCode);
        this.createBlendSheetHeader(blendSheetTemplate);
        this.generateIngredientsTable(blendSheetTemplate);
        this.generateStepsTable(blendSheetTemplate);
    };

    createBlendSheetHeader(blendSheetTemplate){
        const blendSheetHeader = $("#blendSheetHeader");
        $("#itemCode").text(blendSheetTemplate.item_code);
        $("#itemDescription").text(blendSheetTemplate.item_description);
        $("#referenceNumber").val(blendSheetTemplate.formula_reference_no);
        $("#lastEditDate").text(blendSheetTemplate.last_edit_date);
        $("#preparedBy").val(blendSheetTemplate.prepared_by);
        $("#preparedDate").val(blendSheetTemplate.prepared_date);
        $("#lbsPerGallon").val(blendSheetTemplate.lbs_per_gallon);
        $("#batchQuantity").val(blendSheetTemplate.batch_quantity);
        $("#batchWeight").text(blendSheetTemplate.total_weight);
        $("#processPreparation").val(blendSheetTemplate.process_preparation)
    };

    generateIngredientsTable(blendSheetTemplate) {
        const ingredientsTbody = $("#blendSheetIngredientsTbody");
        for (const key in blendSheetTemplate.ingredients) {
            const ingredientData = blendSheetTemplate.ingredients[key];
            const ingredientRow = $("<tr>").addClass("ingredientsRow");
            const itemCodeCell = $("<td>").text(blendSheetTemplate.ingredients[key]["item_code"]);
            ingredientRow.append(itemCodeCell);

            const quantityRatioCell = $('<td class="text-center">');
            const quantityRatioInput = document.createElement("input");

            quantityRatioInput.setAttribute("id", `${key}_item_code`);
            quantityRatioInput.setAttribute("category", "ingredients");
            quantityRatioInput.setAttribute("number", key);
            quantityRatioInput.setAttribute("key", "quantity_ratio");
            quantityRatioInput.setAttribute("class", "quantityRatioInput")
            quantityRatioInput.value = (blendSheetTemplate.ingredients[key]["quantity_ratio"]*100).toFixed(4);
            quantityRatioCell.append(quantityRatioInput);
            quantityRatioCell.append("&nbsp;%");
            ingredientRow.append(quantityRatioCell);

            const itemDescriptionCell = $("<td>").text(blendSheetTemplate.ingredients[key]["item_description"]);
            ingredientRow.append(itemDescriptionCell);

            // const itemQtyNeededCell = $("<td>").text(blendSheetTemplate.ingredients[key]["qty_needed"]);
            // ingredientRow.append(itemQtyNeededCell);

            const itemQtyNeededCell = document.createElement("td");
            itemQtyNeededCell.setAttribute("id", `${key}_qty_needed`);
            itemQtyNeededCell.setAttribute("category", "ingredients");
            itemQtyNeededCell.setAttribute("number", key);
            itemQtyNeededCell.setAttribute("key", "qty_needed");
            itemQtyNeededCell.textContent = blendSheetTemplate.ingredients[key]["qty_needed"];
            itemQtyNeededCell.setAttribute("class", "text-center");
            ingredientRow.append(itemQtyNeededCell);

            const itemUnitCell = $(`<td class=${blendSheetTemplate.ingredients[key]["unit"]}>`).text(blendSheetTemplate.ingredients[key]["unit"]);
            ingredientRow.append(itemUnitCell);

            // create the qty_added input and td
            // const qtyUsedCell = $("<td>").addClass("text-center");
            // ingredientRow.append(qtyUsedCell);

            // create the chem_lot_number td
            // const chemLotNumberCell = $("<td>").addClass("text-center");
            // ingredientRow.append(chemLotNumberCell);

            // create the checked_by select and td
            // const checkedByCell = $("<td>").addClass("text-center");
            // const checkedBySelect = document.createElement("select");
            // checkedBySelect.setAttribute("id", `${key}_checked_by`);
            // checkedBySelect.setAttribute("category", "ingredients");
            // checkedBySelect.setAttribute("number", key);
            // checkedBySelect.setAttribute("key", "checked_by");
            // checkedBySelect.value = blendSheetTemplate.ingredients[key]["checked_by"];
            // checkedByCell.append(checkedBySelect);
            // ingredientRow.append(checkedByCell);

            // create the double_checked_by select and td
            // const doubleCheckedByCell = $("<td>").addClass("text-center");
            // const doubleCheckedBySelect = document.createElement("select");
            // doubleCheckedBySelect.setAttribute("id", `${key}_double_checked_by`);
            // doubleCheckedBySelect.setAttribute("category", "ingredients");
            // doubleCheckedBySelect.setAttribute("number", key);
            // doubleCheckedBySelect.setAttribute("key", "double_checked_by");
            // doubleCheckedBySelect.value = blendSheetTemplate.ingredients[key]["double_checked_by"];
            // doubleCheckedByCell.append(doubleCheckedBySelect);
            // ingredientRow.append(doubleCheckedByCell);

            // create the cell for the calculation method toggle
            // `${key}_`

            const switchCell = $('<td class="text-center switchCell">');
            const switchDiv = $(`<div class="form-check form-switch"></div>`);
            const calcMethodSwitch = document.createElement("input") 
            calcMethodSwitch.setAttribute("type", "checkbox"); 
            calcMethodSwitch.setAttribute("class", "form-check-input calc_method_switch");
            calcMethodSwitch.setAttribute("id", `${key}_calculation_method`);
            calcMethodSwitch.setAttribute("category", "ingredients");
            calcMethodSwitch.setAttribute("number", key); 
            calcMethodSwitch.setAttribute("key", "calculation_method");
            calcMethodSwitch.setAttribute("currentValue", blendSheetTemplate.ingredients[key]["calculation_method"]);
            switchDiv.append(calcMethodSwitch);

            switchCell.append("% of Weight&nbsp;");
            switchCell.append(switchDiv);
            switchCell.append("&nbsp;% of Volume");

            ingredientRow.append(switchCell);

            ingredientsTbody.append(ingredientRow);

        };

        this.calculateRatioTotal();    

    };

    calculateRatioTotal() {
        const quantityRatioInputs = document.querySelectorAll(".quantityRatioInput");
        let ratioTotal = 0;
        quantityRatioInputs.forEach(inputElement => {
            ratioTotal += parseFloat(inputElement.value);
        });

        $("#percentageTotalText").text(ratioTotal.toFixed(4).toString() + " %");
    }

    generateStepsTable(blendSheetTemplate) {
        const stepsTbody = $("#blendSheetStepsTbody");
        const allIngredientItemCodes = [];

        // Iterate through each step and extract item_code values
        for (const stepKey in blendSheetTemplate.ingredients) {
            if (blendSheetTemplate.ingredients.hasOwnProperty(stepKey)) {
                const step = blendSheetTemplate.ingredients[stepKey];
                if (step.item_code) {
                    allIngredientItemCodes.push(step.item_code);
                }
            }
        };

        for (const key in blendSheetTemplate.steps) {
            const stepRow = $("<tr>").addClass("stepsRow");
            const stepNumberCell = $("<td>").text(blendSheetTemplate.steps[key]["number"]).addClass("text-center");
            stepRow.append(stepNumberCell);
            
            // Create step description td and input
            const stepDescriptionCell = $("<td>");
            const stepDescriptionInput = document.createElement("input");
            stepDescriptionInput.setAttribute("id", `${key}_notes`);
            stepDescriptionInput.setAttribute("category", "steps");
            stepDescriptionInput.setAttribute("number", key);
            stepDescriptionInput.setAttribute("key", "notes");
            stepDescriptionInput.value = blendSheetTemplate.steps[key]["description"];
            stepDescriptionCell.append(stepDescriptionInput);
            stepRow.append(stepDescriptionCell);

            const stepUnitCell = $(`<td class=${blendSheetTemplate.steps[key]["unit"]}>`)
                .text(blendSheetTemplate.steps[key]["unit"])
                .attr("category", "steps")
                .attr("number", key)
                .attr("key", "unit");
            stepRow.append(stepUnitCell);


            const stepItemCodeCell = $('<td class="text-center">');
            const stepItemCodeSelect = document.createElement("select");
            stepItemCodeSelect.setAttribute("id", `${key}_item_code`);
            stepItemCodeSelect.setAttribute("category", "steps");
            stepItemCodeSelect.setAttribute("number", key);
            stepItemCodeSelect.setAttribute("key", "item_code");
            stepItemCodeSelect.setAttribute("class", "step_item_code");
            stepItemCodeCell.append(stepItemCodeSelect)
            stepRow.append(stepItemCodeCell);

            // create and append step notes and start/endtime cells
            const stepNotesCell = $("<td>");
            stepRow.append(stepNotesCell);
            const stepStartTimeCell = $("<td>");
            stepRow.append(stepStartTimeCell);
            const stepEndTimeCell = $("<td>");
            stepRow.append(stepEndTimeCell);

            stepsTbody.append(stepRow);
        }

        const selectElements = document.querySelectorAll(".step_item_code");

        selectElements.forEach(selectElement => {
            const blankOption = document.createElement("option");
            selectElement.append(blankOption);
            allIngredientItemCodes.forEach(itemCode => {
                const optionElement = document.createElement("option");
                optionElement.value = itemCode;
                optionElement.textContent = itemCode;
                selectElement.append(optionElement);
            });
            const thisCategory = selectElement.getAttribute("category");
            const thisNumber = selectElement.getAttribute("number");
            const thisKey = selectElement.getAttribute("key");
            const targetValue = blendSheetTemplate[thisCategory][thisNumber][thisKey];
            for (let i = 0; i < selectElement.options.length; i++) {
                const option = selectElement.options[i];
                if (option.value === targetValue) {
                  option.selected = true;
                  break; // Once we find the desired option, we can exit the loop
                }
            }
        });  

    };

    updateServerState(targetElementArray) {
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

        const csrftoken = getCookie('csrftoken');
        let urlParameters = new URLSearchParams(window.location.search);
        let itemCode = urlParameters.get('itemCode');
        const blendSheetTemplate = getBlendSheetTemplate(itemCode);

        targetElementArray.forEach(targetElement => {
            const thisCategory = targetElement.getAttribute("category");
            const thisNumber = targetElement.getAttribute("number");
            const thisKey = targetElement.getAttribute("key");
            let thisValue = targetElement.textContent;
            if (targetElement.tagName === "SELECT") {
                const selectedOption  = targetElement.options[targetElement.selectedIndex];
                thisValue = selectedOption.textContent;
            }
            if (targetElement.tagName === "INPUT") {
                if (targetElement.classList.contains("quantityRatioInput")) {
                    thisValue = parseFloat(targetElement.value) / 100;
                } else if (targetElement.classList.contains("calc_method_switch")) {
                    thisValue = targetElement.getAttribute("currentValue");
                }else {
                    thisValue = targetElement.value;
                }
                
            }
            console.log(targetElement);
            console.log(thisValue);
            blendSheetTemplate[thisCategory][thisNumber][thisKey] = thisValue;
        });

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
            data: JSON.stringify(blendSheetTemplate),
            success: function() {
                console.log("Updated server state");
                console.log(blendSheetTemplate);
            },
            error: function(error) {
                console.error(error);
            }
        });
    };

    setupEventListeners() {
        const updateServerState = this.updateServerState
        let urlParameters = new URLSearchParams(window.location.search);
        let itemCode = urlParameters.get('itemCode');
        const blendSheetTemplateToSearch = getBlendSheetTemplate(itemCode);
        
        $("select").change(function(e){
            const targetElementArray  = [];
            const thisCategory = e.currentTarget.getAttribute("category");
            const thisNumber = e.currentTarget.getAttribute("number");
            const thisKey = e.currentTarget.getAttribute("key");
            targetElementArray.push(e.currentTarget);

            if (e.currentTarget.classList.contains('step_item_code')){
                let unit;
                const itemCodeToSearch = e.currentTarget.value;
                for (const ingredientKey in blendSheetTemplateToSearch.ingredients) {
                    if (blendSheetTemplateToSearch.ingredients.hasOwnProperty(ingredientKey)) {
                        const ingredient = blendSheetTemplateToSearch.ingredients[ingredientKey];
                        if (ingredient.item_code === itemCodeToSearch) {
                        unit = ingredient.unit;
                        break; // Exit the loop once the ingredient is found
                        }
                    }
                }

                const thisUnitElement = document.querySelector(`td[category="${thisCategory}"][number="${thisNumber}"][key="unit"]`);
                thisUnitElement.setAttribute("class", unit);
                thisUnitElement.textContent = unit;
                targetElementArray.push(thisUnitElement);
            }

            updateServerState(targetElementArray);
        });
        

        $("input").change(function(e){
            const targetElementArray  = [];
            const thisCategory = e.currentTarget.getAttribute("category");
            const thisNumber = e.currentTarget.getAttribute("number");
            const thisKey = e.currentTarget.getAttribute("key");
            const blendSheetTemplate = getBlendSheetTemplate(itemCode);
            const thisIngredient = blendSheetTemplate[thisCategory][thisNumber];
            console.log(thisIngredient["unit"])

            // Specific handling of the situation when a calculation method switch is toggled.
            if (e.currentTarget.classList.contains("calc_method_switch")){
                const currentValue = e.currentTarget.getAttribute("currentValue");
                const thisIngredientQtyCell = $(`#${thisNumber}_qty_needed`);
                if (currentValue === "percent_of_weight") {
                    e.currentTarget.setAttribute("currentValue", "percent_of_volume");
                    let newQtyNeeded = 0;
                    if (thisIngredient["unit"] === "gal") {
                        newQtyNeeded = parseFloat(thisIngredient["quantity_ratio"])*parseFloat(blendSheetTemplate['batch_quantity']);
                    } 
                    // 
                    else if (thisIngredient["unit"] === "grams") {
                        newQtyNeeded = parseFloat(thisIngredient["quantity_ratio"])*parseFloat(blendSheetTemplate['batch_quantity']);

                        newQtyNeeded = newQtyNeeded

                    }
                    thisIngredientQtyCell.text(newQtyNeeded);
                } else if (currentValue === "percent_of_volume"){
                    e.currentTarget.setAttribute("currentValue", "percent_of_weight");
                    if (thisIngredient["unit"] === "lbs") {
                        let newQtyNeeded = parseFloat(thisIngredient["quantity_ratio"])*parseFloat(blendSheetTemplate['batch_quantity']);
                        thisIngredientQtyCell.text(newQtyNeeded);
                    }
                }
                targetElementArray.push(thisIngredientQtyCell);
            };
            targetElementArray.push(e.currentTarget);
            updateServerState(targetElementArray);
        });

        const calculateRatioTotal = this.calculateRatioTotal;
        $(".quantityRatioInput").change(function(e){
            calculateRatioTotal();
        });
        $(".quantityRatioInput").click(function(e){
            calculateRatioTotal();
        });

    };

}