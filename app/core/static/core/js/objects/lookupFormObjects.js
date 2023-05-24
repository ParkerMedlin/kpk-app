import { getLocation, getAllBOMFields, getItemInfo, getMaxProducibleQuantity } from '../requestFunctions/requestFunctions.js'
import { indicateLoading } from '../uiFunctions/uiFunctions.js'


export class LocationLookupForm {
    constructor() {
        try{
            this.setUpAutoFill();
            console.log("Instance of class LocationLookupForm created.");
        } catch(err) {
            console.error(err.message);
        }
    }

    BOMFields = getAllBOMFields('chem-dye-frag');

    setFields(locationData){
        $("#id_item_code").val(locationData.itemCode);
        $("#id_item_description").val(locationData.itemDescription);
        $('#id_location').text(locationData.generalLocation + ", " + locationData.specificLocation);
        $('#id_quantity').text(locationData.qtyOnHand + " " + locationData.standardUOM + " on hand.");
    };

    setUpAutoFill() {
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $("#id_item_code").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 2,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_codes, request.term);
                        response(results.slice(0,10));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemCode");
                        let itemCode;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemCode = $("#id_item_code").val();
                        } else {
                            itemCode = ui.item.label.toUpperCase();
                        }
                        let locationData = getLocation(itemCode, "itemCode");
                        console.log(locationData);
                        setFields(locationData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let locationData = getLocation(itemCode, "itemCode");
                        setFields(locationData);
                    },
                });
        
                //   ===============  Description Search  ===============
                $("#id_item_description").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 3,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_descriptions, request.term);
                        response(results.slice(0,300));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemDescription");
                        let itemDesc;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemDesc = $("#id_item_description").val();
                        } else {
                            itemDesc = ui.item.label.toUpperCase();
                        }
                        let locationData = getLocation(itemDesc, "itemDescription");
                        setFields(locationData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let locationData = getLocation(itemDesc, "itemDescription");
                        setFields(locationData);
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        };
        
        $("#id_item_code").focus(function(){
            $(".animation").hide();
        }); 
        $("#id_item_description").focus(function(){
            $(".animation").hide();
        });
    };
}

export class LotNumberLookupForm {
    constructor() {
        try{
            this.setUpAutofill();
            console.log("Instance of class LotNumberLookupForm created.");
        } catch(err) {
            console.error(err.message);
        }
    }

    BOMFields = getAllBOMFields('blends-only');    

    setSearchButtonLink(itemData) {
        $("#lotNumSearchLink").attr("href", `/core/create-report/Lot-Numbers/${itemData.item_code}`);
    }

    setFields(itemData){
        $("#id_item_code").val(itemData.item_code);
        $("#id_item_description").val(itemData.item_description);
    };

    setUpAutofill() {
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        let setSearchButtonLink = this.setSearchButtonLink;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $("#id_item_code").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 2,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_codes, request.term);
                        response(results.slice(0,10));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemCode");
                        let itemCode;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemCode = $("#id_item_code").val();
                        } else {
                            itemCode = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                        setSearchButtonLink(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                        setSearchButtonLink(itemData);
                    },
                });
                //   ===============  Description Search  ===============
                $("#id_item_description").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 3,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_descriptions, request.term);
                        response(results.slice(0,300));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemDescription");
                        let itemDesc;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemDesc = $("#id_item_description").val();
                        } else {
                            itemDesc = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                        setSearchButtonLink(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                        setSearchButtonLink(itemData);
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        };
        $('#id_item_code').focus(function(){
            $('.animation').hide();
            $("#warningParagraph").hide();
            $("#lotNumSearchLink").show();
        }); 
        $("#id_item_description").focus(function(){
            $('.animation').hide();
            $("#warningParagraph").hide();
            $("#lotNumSearchLink").show();
        });
    }
}

export class ItemQuantityLookupForm {
    constructor() {
        try {
            this.setUpAutofill();
            console.log("Instance of class ItemQuantityLookupForm created.");
        } catch(err) {
            console.error(err.message);
        }
    };

    BOMFields = getAllBOMFields();
    itemQuantityDiv = $("#item_quantity");

    setItemQuantityDiv(itemData) {
        let qtyOnHand = Math.round(itemData.qtyOnHand, 0)
        $("#item_quantity").text(`${qtyOnHand} ${itemData.standardUOM}`)
    };
    
    setFields(itemData){
        $("#id_item_code").val(itemData.item_code);
        $("#id_item_description").val(itemData.item_description);
    };

    setUpAutofill() {
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        let setItemQuantityDiv = this.setItemQuantityDiv;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $("#id_item_code").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 2,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_codes, request.term);
                        response(results.slice(0,10));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemCode");
                        let itemCode;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemCode = $("#id_item_code").val();
                        } else {
                            itemCode = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                        setItemQuantityDiv(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                        setItemQuantityDiv(itemData);
                    },
                });
                //   ===============  Description Search  ===============
                $("#id_item_description").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 3,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_descriptions, request.term);
                        response(results.slice(0,300));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemDescription");
                        let itemDesc;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemDesc = $("#id_item_description").val();
                        } else {
                            itemDesc = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                        setItemQuantityDiv(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                        setItemQuantityDiv(itemData);
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        };
        $('#id_item_code').focus(function(){
            $('.animation').hide();
            $("#warningParagraph").hide();
        }); 
        $("#id_item_description").focus(function(){
            $('.animation').hide();
            $("#warningParagraph").hide();
        });
    };

}

export class MaxProducibleQuantityForm {
    constructor() {
        try {
            this.setUpAutofill();
            console.log("Instance of class MaxBlendCapacityForm created.");
        } catch(err) {
            console.error(err.message);
        }
    };

    setFields(itemData){
        $("#id_item_code").val(itemData.item_code);
        $("#id_item_description").val(itemData.item_description);
    }

    setMaxProducibleQuantityDiv(itemData){
        $("#max_producible_quantity").text(`${itemData.max_producible_quantity} gallons`);
        $("#max_producible_quantity").css('font-weight', 'bold');
        $("#limiting_factor").text(`${itemData.limiting_factor_item_code}: ${itemData.limiting_factor_item_description}`);
        $("#limiting_factor_onhand").text(
            `${Math.round(itemData.limiting_factor_quantity_onhand, 0)}
            ${itemData.limiting_factor_UOM} on hand now --
            ${Math.round(itemData.limiting_factor_OH_minus_other_orders)}  ${itemData.limiting_factor_UOM} available after all other usage is taken into account.`
            );
        $("#next_shipment").text(`${itemData.next_shipment_date}`);
        console.log(itemData.consumption_detail);
        console.log(itemData.consumption_detail[itemData.limiting_factor_item_code])
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
        // $("#limiting_factor_usage_tbody").append(`<tr><td>${itemData.component_consumption}</td></tr>`)
        $("#blendCapacityContainer").show();

    }

    setUpAutofill() {
        let BOMFields = getAllBOMFields();
        let setFields = this.setFields;
        let setMaxProducibleQuantityDiv = this.setMaxProducibleQuantityDiv;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $("#id_item_code").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 2,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_codes, request.term);
                        response(results.slice(0,10));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        document.getElementById("limiting_factor_usage_tbody").innerHTML = '';
                        indicateLoading("itemCode");
                        let itemCode;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemCode = $("#id_item_code").val();
                        } else {
                            itemCode = ui.item.label.toUpperCase();
                        }
                        let itemData = getMaxProducibleQuantity(itemCode, "NoComponentItemFilter", "itemCode");
                        setFields(itemData);
                        setMaxProducibleQuantityDiv(itemData);
                        $('.animation').hide();
                        $("#warningParagraph").hide();
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        document.getElementById("limiting_factor_usage_tbody").innerHTML = '';
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getMaxProducibleQuantity(itemCode, "NoComponentItemFilter", "itemCode");
                        setFields(itemData);
                        setMaxProducibleQuantityDiv(itemData);
                        $('.animation').hide();
                        $("#warningParagraph").hide();
                    },
                });
                //   ===============  Description Search  ===============
                $("#id_item_description").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 3,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_descriptions, request.term);
                        response(results.slice(0,300));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        document.getElementById("limiting_factor_usage_tbody").innerHTML = '';
                        indicateLoading("itemDescription");
                        let itemDesc;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemDesc = $("#id_item_description").val();
                        } else {
                            itemDesc = ui.item.label.toUpperCase();
                        }
                        let itemData = getMaxProducibleQuantity(itemDesc, "NoComponentItemFilter", "itemCode");
                        setFields(itemData);
                        setMaxProducibleQuantityDiv(itemData);
                        $('.animation').hide();
                        $("#warningParagraph").hide();
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        document.getElementById("limiting_factor_usage_tbody").innerHTML = '';
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getMaxProducibleQuantity(itemDesc, "NoComponentItemFilter", "itemCode");
                        setFields(itemData);
                        setMaxProducibleQuantityDiv(itemData);
                        $('.animation').hide();
                        $("#warningParagraph").hide();
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        };
        $('#id_item_code').focus(function(){
            $('.animation').hide();
            $("#warningParagraph").hide();
        }); 
        $("#id_item_description").focus(function(){
            $('.animation').hide();
            $("#warningParagraph").hide();
        });
    };


}

export class ReportCenterForm {
    constructor() {
        try{
            this.setUpAutofill();
            this.setUpEventListener();
            console.log("Instance of class ReportCenterForm created.");
        } catch(err) {
            console.error(err.message);
        }
    }

    BOMFields = getAllBOMFields();    

    setFields(itemData){
        $("#id_item_code").val(itemData.item_code);
        $("#id_item_description").val(itemData.item_description);
        $("#reportLink").prop("data-itemcode", itemData.item_code);
    };

    setUpAutofill() {
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        let setReportButtonLink = this.setReportButtonLink;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $("#id_item_code").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 2,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_codes, request.term);
                        response(results.slice(0,10));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemCode");
                        let itemCode;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemCode = $("#id_item_code").val();
                        } else {
                            itemCode = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemCode, "itemCode");
                        let reportType = $("#id_which_report").val().replaceAll(' ', '-');
                        setFields(itemData);
                        $("#reportLink").prop('href', `/core/create-report/${reportType}/${itemData.item_code}`);
                        $("#reportLink").show();
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        let reportType = $("#id_which_report").val().replaceAll(' ', '-');
                        setFields(itemData);
                        $("#reportLink").prop('href', `/core/create-report/${reportType}/${itemData.item_code}`);
                        $("#reportLink").show();
                    },
                });
                //   ===============  Description Search  ===============
                $("#id_item_description").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 3,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_descriptions, request.term);
                        response(results.slice(0,300));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemDescription");
                        let itemDescription;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemDescription = $("#id_item_description").val();
                        } else {
                            itemDescription = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemDescription, "itemDescription");
                        let reportType = $("#id_which_report").val().replaceAll(' ', '-');
                        setFields(itemData);
                        $("#reportLink").prop('href', `/core/create-report/${reportType}/${itemData.item_code}`);
                        $("#reportLink").show();
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDescription = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDescription, "itemDescription");
                        let reportType = $("#id_which_report").val().replaceAll(' ', '-');
                        setFields(itemData);
                        $("#reportLink").prop('href', `/core/create-report/${reportType}/${itemData.item_code}`);
                        $("#reportLink").show();
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        };
        $('#id_item_code').focus(function(){
            $('.animation').hide();
            $("#warningParagraph").hide();
        }); 
        $("#id_item_description").focus(function(){
            $('.animation').hide();
            $("#warningParagraph").hide();
        });
    }

    setUpEventListener() {
        $("#id_which_report").change(function() {
            let reportType = $("#id_which_report").val().replaceAll(' ', '-');
            if ($("#id_item_code").val()!="" && $("#id_item_description").val()!="" | reportType=="Startron-Runs"){
                $("#reportLink").show();
            };
            let itemCode = $("#id_item_code").val();
            if (reportType=="Startron-Runs") { 
                $("#itemCodeRow").prop("style", "display: none;");
                $("#itemDescriptionRow").prop("style", "display: none;");
                itemCode="n-a"
                $("#reportLink").show();
            }else if (reportType=="Max-Producible-Quantity"){
                let baseURL = window.location.href.split('core')[0];
                // https://stackoverflow.com/questions/503093/how-do-i-redirect-to-another-webpage
                window.location.replace(baseURL + "core/max-producible-quantity/")
            }else{
                $("#itemCodeRow").show();
                $("#itemDescriptionRow").show();
            };
            $("#reportLink").prop('href', `/core/create-report/${reportType}/${itemCode}`);
        });
    };
}

export class FilterForm {
    constructor() {
        try{
            this.setUpFiltering();
            console.log("Instance of class FilterForm created.");
        } catch(err) {
            console.error(err.message);
        }
    }

    setUpFiltering(){
        $(document).ready(function(){
            $("#id_filter_criteria").on("keyup", function() {
                var value = $(this).val().toLowerCase();
                $("#displayTable tr.filterableRow").filter(function() {
                    $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
                });
            });
        });
    }
}