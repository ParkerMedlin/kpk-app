import { getMaxProducibleQuantity, getBlendSheet } from '../requestFunctions/requestFunctions.js'

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
            console.log(formNumber);
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
                console.log(e.currentTarget);
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
        console.log(itemData)
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
        console.log(rStat);
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
            console.log(deskScheduleDict);
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
            console.log(scheduleUpdateResult);
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
        this.generateIngredientsDivs(blendSheet);

        console.log(blendSheet);
    };

    createBlendSheetHeader(blendSheet){
        const blendSheetHeader = $("#blendSheetHeader");
        $("#itemCode").text(blendSheet.item_code + "--");
        $("#itemDescription").text(blendSheet.item_description);
        $("#referenceNumber").text(blendSheet.formula_reference_no);
        $("#lastEditDate").text(blendSheet.last_edit_date);
        $("#preparedBy").text(blendSheet.prepared_by + "--");
        $("#preparedDate").text(blendSheet.prepared_date);
        $("#lbsPerGallon").text(blendSheet.lbs_per_gallon);
        $("#batchQuantity").text(blendSheet.batch_quantity);
        $("#batchWeight").text(blendSheet.batch_quantity * blendSheet.lbs_per_gallon);
        $("#lotNumber").text(blendSheet.lot_number);
    };

    generateIngredientsDivs(blendSheet) {
        const ingredientsContainer = $("#ingredientsContainer");

        for (const key in blendSheet.ingredients) {
            const ingredientData = blendSheet.ingredients[key];
            const ingredientDiv = $("<div>").addClass("ingredientsRow");

            for (const property in ingredientData) {
                const propertyValue = ingredientData[property];
                const ingredientInfo = $("<p>").text(`${property}: ${propertyValue}`);
                ingredientDiv.append(ingredientInfo);
            }

            ingredientsContainer.append(ingredientDiv);
        }
    };

    updateServerState() {
        const csrftoken = this.getCookie('csrftoken');
        const state = {
            checkboxes: {},
            signature1: $("#signature1").val(),
            signature2: $("#signature2").val(),
            textarea: $(".commentary textarea").val(),
        };
        $(".larger-checkbox").each(function() {
            state.checkboxes[$(this).attr("id")] = $(this).is(":checked") ? true : false;
        });
                
        function csrfSafeMethod(method) {
            // these HTTP methods do not require CSRF protection
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        };

        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                }
            }
        });

        $.ajax({
            type: "POST",
            url: window.location.pathname,
            data: JSON.stringify(state, function(key, value) {
                return typeof value === "boolean" ? value.toString() : value}),
            success: function() {
                console.log("Updated server state");
                console.log(JSON.stringify(state, function(key, value) {
                    return typeof value === "boolean" ? value.toString() : value;
                }));
            },
            error: function(error) {
                console.error(error);
            }
        });
    };

}