import { getLocation, getAllBOMFields, getItemInfo } from '../requestFunctions/requestFunctions.js'
import { indicateLoading } from '../uiFunctions/uiFunctions.js'


export class LocationLookupForm {
    constructor() {
        this.setUpAutoFill();
    }

    BOMFields = getAllBOMFields('chem-dye-frag');

    setFields(locationData){
        $("#id_item_code").val(locationData.itemCode);
        $("#id_item_description").val(locationData.itemDescription);
        $('#id_location').text(locationData.generalLocation + ", " + locationData.specificLocation);
        $('#id_quantity').text(locationData.qtyOnHand + " " + locationData.standardUOM + " on hand.");
    };

    setUpAutoFill() {
        let allBOMFields = this.BOMFields;
        let setFields = this.setFields;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $("#id_item_code").autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 2,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(allBOMFields.item_codes, request.term);
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
                        let results = $.ui.autocomplete.filter(allBOMFields.item_descriptions, request.term);
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
        } catch (pnError) {
            console.log(pnError)
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
        this.setUpAutofill();
    }

    BOMFields = getAllBOMFields('blends-only');    

    setSearchButtonLink(itemData) {
        $("#lotNumSearchLink").attr("href", `/core/reports/Lot-Numbers/${itemData.item_code}`);
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
        } catch (pnError) {
            console.log(pnError)
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
        this.setUpAutofill();
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
        } catch (pnError) {
            console.log(pnError)
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
        this.setUpAutofill();
        this.setUpEventListener();
    }

    BOMFields = getAllBOMFields();    

    setModalButtonLink(itemData) {
        $("#reportLink").attr("href", `/core/reports/Lot-Numbers/${itemData.item_code}`);
    }

    setFields(itemData){
        $("#id_item_code").val(itemData.item_code);
        $("#id_item_description").val(itemData.item_description);
        $("#reportLink").prop("data-itemcode", itemData.item_code);
    };

    setUpAutofill() {
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        let setModalButtonLink = this.setModalButtonLink;
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
                        $("#reportLink").prop('href', `${reportType}/${itemData.item_code}`);
                        $("#reportLink").show();
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        let reportType = $("#id_which_report").val().replaceAll(' ', '-');
                        setFields(itemData);
                        $("#reportLink").prop('href', `${reportType}/${itemData.item_code}`);
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
                        $("#reportLink").prop('href', `${reportType}/${itemData.item_code}`);
                        $("#reportLink").show();
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDescription = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDescription, "itemDescription");
                        let reportType = $("#id_which_report").val().replaceAll(' ', '-');
                        setFields(itemData);
                        $("#reportLink").prop('href', `${reportType}/${itemData.item_code}`);
                        $("#reportLink").show();
                    },
                });
            });
        } catch (pnError) {
            console.log(pnError)
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
            console.log(`${reportType}/${itemCode}`);
            $("#reportLink").prop('href', `${reportType}/${itemCode}`);
        });
    };
}