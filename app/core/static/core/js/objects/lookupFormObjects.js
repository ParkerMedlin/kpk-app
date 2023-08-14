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
    
    setItemProtectionDiv(itemData) {+
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
                        $("#reportLink").prop('href', `/core/create-report/${reportType}?itemCode=${btoa(itemData.item_code)}`);
                        $("#reportLink").show();
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        let reportType = $("#id_which_report").val().replaceAll(' ', '-');
                        setFields(itemData);
                        $("#reportLink").prop('href', `/core/create-report/${reportType}?itemCode=${btoa(itemData.item_code)}`);
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
                        $("#reportLink").prop('href', `/core/create-report/${reportType}?itemCode=${btoa(itemData.item_code)}`);
                        $("#reportLink").show();
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDescription = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDescription, "itemDescription");
                        let reportType = $("#id_which_report").val().replaceAll(' ', '-');
                        setFields(itemData);
                        $("#reportLink").prop('href', `/core/create-report/${reportType}?itemCode=${btoa(itemData.item_code)}`);
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
            }else{
                $("#itemCodeRow").show();
                $("#itemDescriptionRow").show();
            };
            $("#reportLink").prop('href', `/core/create-report/${reportType}?itemCode=${btoa(itemCode)}`);
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
