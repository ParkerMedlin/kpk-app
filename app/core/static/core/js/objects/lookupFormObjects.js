import { getLocation, getAllBOMFields, getItemInfo } from '../requestFunctions/requestFunctions.js'
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

    BOMFields = getAllBOMFields('blendcomponent');

    setFields(locationData){
        $("#id_item_code").val(locationData.itemCode);
        $("#id_item_description").val(locationData.itemDescription);
        $('#id_location').text(locationData.zone  + ", " + locationData.bin);
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

    BOMFields = getAllBOMFields('blend');    

    setSearchButtonLink(itemData) {
        $("#lotNumSearchLink").attr("href", `/core/create-report/Lot-Numbers?itemCode=${btoa(itemData.item_code)}`);
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

    setItemProtectionDiv(itemData) {
        console.log(itemData);
        let protectionValue;
        switch (itemData.uv_protection) {
            case "no":
              switch (itemData.freeze_protection) {
                case "no":
                  return "none";
                case "yes":
                    protectionValue = "freeze only";
              }
              break;
            case "yes":
              switch (itemData.freeze_protection) {
                case "no":
                  return "uv only";
                case "yes":
                    protectionValue = "both";
              }
              break;
            default:
                protectionValue = "unknown";
          }
        $("#item_protection").text(protectionValue)
    }

    setFields(itemData) {
        $("#id_item_code").val(itemData.item_code);
        $("#id_item_description").val(itemData.item_description);
    };

    setUpAutofill() {
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        let setItemQuantityDiv = this.setItemQuantityDiv;
        let setItemProtectionDiv = this.setItemProtectionDiv;
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
                        if (itemData.item_description.toLowerCase().includes("blend")){
                            $("#itemProtectionContainer").show();
                            setItemProtectionDiv(itemData);
                        } else {
                            $("#itemProtectionContainer").hide();
                            $("#itemProtectionContainer").text("");
                        };
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                        setItemQuantityDiv(itemData);
                        if (itemData.item_description.toLowerCase().includes("blend")){
                            $("#itemProtectionContainer").show();
                            setItemProtectionDiv(itemData);
                        } else {
                            $("#itemProtectionContainer").hide();
                            $("#itemProtectionContainer").text("");
                        };
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
                        if (itemData.item_description.toLowerCase().includes("blend")){
                            $("#itemProtectionContainer").show();
                            setItemProtectionDiv(itemData);
                        } else {
                            $("#itemProtectionContainer").hide();
                            $("#itemProtectionContainer").text("");
                        };
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                        setItemQuantityDiv(itemData);
                        if (itemData.item_description.toLowerCase().includes("blend")){
                            $("#itemProtectionContainer").show();
                            setItemProtectionDiv(itemData);
                        } else {
                            $("#itemProtectionContainer").hide();
                            $("#itemProtectionContainer").text("");
                        };
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

};

export class BlendComponentLabelInfoLookupForm {
    constructor() {
        try {
            this.setUpAutofill();
            console.log("Instance of class BlendComponentLabelInfoLookupForm created.");
        } catch(err) {
            console.error(err.message);
        }
    };

    BOMFields = getAllBOMFields('blendcomponent');

    setFields(itemData) {
        $(".error-message").each(function(){
            $(this).remove();
        });
        $("#gross-weight, #label-container-type-dropdown, #inventory-label-container-type, #inventory-label-item-code").css({"color": "", "font-weight": ""});
        $("#id_item_code").val(itemData.item_code);
        $("#id_item_description").val(itemData.item_description);
        $("#inventory-label-item-code").text(itemData.item_code);
        $("#inventory-label-item-description").text(itemData.item_description);
        $("#gross-weight").val("");
        $("#net-weight").text("");
        $("#net-gallons").text("");
        $("#inventory-label-container-type").text("");
        $("#inventory-label-container-weight").text("");
    };

    setUpAutofill() {
        let BOMFields = this.BOMFields;
        console.log(BOMFields);
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
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
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
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        };
        $('#id_item_code').focus(function(){
            $('.animation').hide();
        }); 
        $("#id_item_description").focus(function(){
            $('.animation').hide();
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
        $("#reportLink").prop("data-itemcode", btoa(itemData.item_code));
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
                        let itemQuantity = $("#id_item_quantity").val();
                        let startTime = $("#id_start_time").val();
                        $("#reportLink").prop('href', `/core/create-report/${reportType}?itemCode=${btoa(itemData.item_code)}&itemQuantity=${itemQuantity}&startTime=${startTime}`);
                        $("#reportLink").show();
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        let reportType = $("#id_which_report").val().replaceAll(' ', '-');
                        setFields(itemData);
                        let itemQuantity = $("#id_item_quantity").val();
                        let startTime = $("#id_start_time").val();
                        $("#reportLink").prop('href', `/core/create-report/${reportType}?itemCode=${btoa(itemData.item_code)}&itemQuantity=${itemQuantity}&startTime=${startTime}`);
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
                        let itemQuantity = $("#id_item_quantity").val();
                        let startTime = $("#id_start_time").val();
                        $("#reportLink").prop('href', `/core/create-report/${reportType}?itemCode=${btoa(itemData.item_code)}&itemQuantity=${itemQuantity}&startTime=${startTime}`);
                        $("#reportLink").show();
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDescription = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDescription, "itemDescription");
                        let reportType = $("#id_which_report").val().replaceAll(' ', '-');
                        setFields(itemData);
                        let itemQuantity = $("#id_item_quantity").val();
                        let startTime = $("#id_start_time").val();
                        $("#reportLink").prop('href', `/core/create-report/${reportType}?itemCode=${btoa(itemData.item_code)}&itemQuantity=${itemQuantity}&startTime=${startTime}`);
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
            console.log(reportType);
            if ($("#id_item_code").val()!="" && $("#id_item_description").val()!="" || reportType=="Startron-Runs"){
                $("#reportLink").show();
            };
            let itemCode = $("#id_item_code").val();
            if (reportType=="Startron-Runs") {
                $("#itemCodeRow").prop("style", "display: none;");
                $("#itemDescriptionRow").prop("style", "display: none;");
                itemCode="n-a"
                $("#reportLink").show();
            } else if (reportType=="Blend-What-If" || reportType=="Item-Component-What-If") {
                $("#itemQuantityRow").show();
                $("#startTimeRow").show();
                $("#reportLink").show();
            } else {
                $("#itemCodeRow").show();
                $("#itemDescriptionRow").show();
                $("#itemQuantityRow").prop("style", "display: none;");
                $("#startTimeRow").prop("style", "display: none;");
            };
            let itemQuantity = $("#id_item_quantity").val();
            let startTime = $("#id_start_time").val();
            $("#reportLink").prop('href', `/core/create-report/${reportType}?itemCode=${btoa(itemCode)}&itemQuantity=${itemQuantity}&startTime=${startTime}`);
        });
        $("#id_item_quantity").change(function() {
            let reportType = $("#id_which_report").val().replaceAll(' ', '-');
            let itemCode = $("#id_item_code").val();
            let itemQuantity = $("#id_item_quantity").val();
            let startTime = $("#id_start_time").val();
            $("#reportLink").prop('href', `/core/create-report/${reportType}?itemCode=${btoa(itemCode)}&itemQuantity=${itemQuantity}&startTime=${startTime}`);
        });
        $("#id_start_time").change(function() {
            let reportType = $("#id_which_report").val().replaceAll(' ', '-');
            let itemCode = $("#id_item_code").val();
            let itemQuantity = $("#id_item_quantity").val();
            let startTime = $("#id_start_time").val();
            $("#reportLink").prop('href', `/core/create-report/${reportType}?itemCode=${btoa(itemCode)}&itemQuantity=${itemQuantity}&startTime=${startTime}`);
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
    };

    setUpFiltering(){
        $("#id_filter_criteria").on("keyup", function() {
            let value = $(this).val().toLowerCase();
            $("#displayTable tr.filterableRow").each(function() {
                const row = $(this);
                const isMatch = row.text().toLowerCase().replace(' ','').includes(value);
                // Toggle display based on whether the value is in the row's text
                row.toggle(isMatch);
        
                // Add or remove the class "chosen" based on visibility
                if (isMatch) {
                    row.addClass("chosen");
                } else {
                    row.removeClass("chosen");
                }
            });
        });
    };
}

export class BlendShortagesFilterForm {
    constructor() {
        try{
            this.setUpFiltering();
            console.log("Instance of class BlendShortagesFilterForm created.");
        } catch(err) {
            console.error(err.message);
        }
    };

    setUpFiltering(){
        $("#id_filter_criteria").on("keyup", function() {
            let value = $(this).val().toLowerCase();
            $("#displayTable tr.filterableRow span").each(function() {
                const row = $(this).closest('tr');
                const isMatch = row.text().toLowerCase().replace(/\s+/g, '').includes(value);
                // Toggle display based on whether the value is in the row's text
                row.toggle(isMatch);
                // Add or remove the class "chosen" based on visibility
                if (isMatch) {
                    row.addClass("chosen");
                } else {
                    row.removeClass("chosen");
                }
            });
        });
    };
}

export class DropDownFilter {   
    constructor() {
        try{
            this.setUpDropDownFiltering();
            console.log("Instance of class DropDownFilter created.");
        } catch(err) {
            console.error(err.message);
        }
    };

    setUpDropDownFiltering(){
        $("#auditGroupLinks").on("click", function() {
            let value = $(this).val().toLowerCase();
            $("#displayTable tr.filterableRow").each(function() {
                const row = $(this);
                const isMatch = row.text().toLowerCase().includes(value);
                
                // Toggle display based on whether the value is in the row's text
                row.toggle(isMatch);
        
                // Add or remove the class "chosen" based on visibility
                if (isMatch) {
                    row.addClass("chosen");
                } else {
                    row.removeClass("chosen");
                }
            });
        });
    };
}

export class ItemReferenceFieldPair {
    constructor(itemCodeInputField, itemDescriptionInputField) {
        try{
            this.setUpAutofill(itemCodeInputField, itemDescriptionInputField)
            console.log("Instance of class ItemReferencePair created.");
        } catch(err) {
            console.error(err.message);
        }
    };

    setFields(itemData, itemCodeInputField, itemDescriptionInputField) {
        $(itemCodeInputField).val(itemData.item_code);
        $(itemDescriptionInputField).val(itemData.item_description);
    };

    setUpAutofill(itemCodeInputField, itemDescriptionInputField) {
        let BOMFields = getAllBOMFields();
        console.log(BOMFields)
        let setFields = this.setFields;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $(itemCodeInputField).autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemCode = $(itemCodeInputField).val();
                        } else {
                            itemCode = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData, itemCodeInputField, itemDescriptionInputField);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData, itemCodeInputField, itemDescriptionInputField);
                    },
                });
                //   ===============  Description Search  ===============
                $(itemDescriptionInputField).autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemDesc = $(itemDescriptionInputField).val();
                        } else {
                            itemDesc = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData, itemCodeInputField, itemDescriptionInputField);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData, itemCodeInputField, itemDescriptionInputField);
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        };
        $(itemCodeInputField).focus(function(){
            $('.animation').hide();
            $("#warningParagraph").hide();
        }); 
        $(itemDescriptionInputField).focus(function(){
            $('.animation').hide();
            $("#warningParagraph").hide();
        });
    };
}

export class GHSLookupForm {
    constructor(itemCodeInputField, itemDescriptionInputField, restriction) {
        try{
            this.setUpAutofill(itemCodeInputField, itemDescriptionInputField, restriction)
            console.log("Instance of class ItemReferencePair created.");
        } catch(err) {
            console.error(err.message);
        }
    };

    setFields(itemData, itemCodeInputField, itemDescriptionInputField) {
        $(itemCodeInputField).val(itemData.item_code);
        $(itemDescriptionInputField).val(itemData.item_description);
        let encodedItemCode = btoa($(itemCodeInputField).val());
        $("#GHSgenButton").attr("href", `/core/display-ghs-label/${encodedItemCode}`);
    };

    setUpAutofill(itemCodeInputField, itemDescriptionInputField, restriction) {
        let BOMFields = getAllBOMFields(restriction);
        let setFields = this.setFields;
        try {
            
            $( function() {
                // ===============  Item Number Search  ==============
                $(itemCodeInputField).autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 2,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_codes, request.term);
                        response(results.slice(0,10));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        if ($('#autofillcheckbox').is(':checked')) {
                            indicateLoading("itemCode");
                            let itemCode;
                            if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                                itemCode = $(itemCodeInputField).val();
                            } else {
                                itemCode = ui.item.label.toUpperCase();
                            }
                            let itemData = getItemInfo(itemCode, "itemCode", restriction);
                            setFields(itemData, itemCodeInputField, itemDescriptionInputField);
                        }
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        if ($('#autofillcheckbox').is(':checked')) {
                            indicateLoading();
                            let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                            let itemData = getItemInfo(itemCode, "itemCode", restriction);
                            setFields(itemData, itemCodeInputField, itemDescriptionInputField);
                        }
                    },
                });
                //   ===============  Description Search  ===============
                $(itemDescriptionInputField).autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 3,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(BOMFields.item_descriptions, request.term);
                        response(results.slice(0,300));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        if ($('#autofillcheckbox').is(':checked')) {
                            indicateLoading("itemDescription");
                            let itemDesc;
                            if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                                itemDesc = $(itemDescriptionInputField).val();
                            } else {
                                itemDesc = ui.item.label.toUpperCase();
                            }
                            let itemData = getItemInfo(itemDesc, "itemDescription", restriction);
                            setFields(itemData, itemCodeInputField, itemDescriptionInputField);
                        }
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        if ($('#autofillcheckbox').is(':checked')) {
                            indicateLoading();
                            let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                            let itemData = getItemInfo(itemDesc, "itemDescription", restriction);
                            setFields(itemData, itemCodeInputField, itemDescriptionInputField);
                        }
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        };
        $(itemCodeInputField).focus(function(){
            $('.animation').hide();
            $("#warningParagraph").hide();
        }); 
        $(itemDescriptionInputField).focus(function(){
            $('.animation').hide();
            $("#warningParagraph").hide();
        });
    };
}

export class RawLabelLookupForm {
    constructor(itemCodeField, itemDescriptionField, locationFields, unitsField) {
        try{
            this.setUpAutoFill(itemCodeField, itemDescriptionField, locationFields, unitsField);
            console.log("Instance of class LocationLookupForm created.");
        } catch(err) {
            console.error(err.message);
        }
    }

    BOMFields = getAllBOMFields('blendcomponent');

    setFields(locationData, itemCodeField, itemDescriptionField, locationField, unitsField){
        itemCodeField.val(locationData.itemCode);
        itemDescriptionField.val(locationData.itemDescription);
        locationField.text(locationData.zone  + ", " + locationData.bin);
        unitsField.text(locationData.standardUOM);
    };

    setUpAutoFill(itemCodeField, itemDescriptionField, locationField, unitsField) {
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                itemCodeField.autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemCode = itemCodeField.val();
                        } else {
                            itemCode = ui.item.label.toUpperCase();
                        }
                        let locationData = getLocation(itemCode, "itemCode");
                        setFields(locationData, itemCodeField, itemDescriptionField, locationField, unitsField);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let locationData = getLocation(itemCode, "itemCode");
                        setFields(locationData, itemCodeField, itemDescriptionField, locationField, unitsField);
                    },
                });
        
                //   ===============  Description Search  ===============
                itemDescriptionField.autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemDesc = itemDescriptionField.val();
                        } else {
                            itemDesc = ui.item.label.toUpperCase();
                        }
                        let locationData = getLocation(itemDesc, "itemDescription");
                        setFields(locationData, itemCodeField, itemDescriptionField, locationField, unitsField);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let locationData = getLocation(itemDesc, "itemDescription");
                        setFields(locationData, itemCodeField, itemDescriptionField, locationField, unitsField);
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        };
        
        itemCodeField.focus(function(){
            $(".animation").hide();
        }); 
        itemDescriptionField.focus(function(){
            $(".animation").hide();
        });
    };
}