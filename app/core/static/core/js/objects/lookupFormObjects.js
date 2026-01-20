import { getLocation, getAllBOMFields, getItemInfo, getMostRecentLotRecords, getURLParameter } from '../requestFunctions/requestFunctions.js'
import { indicateLoading } from '../uiFunctions/uiFunctions.js'

export class LocationLookupForm {
    constructor() {
        try{
            this.setUpAutoFill();
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
        } catch(err) {
            console.error(err.message);
        }
    };

    BOMFields = getAllBOMFields();
    itemQuantityDiv = $("#item_quantity");

    setItemQuantityDiv(itemData) {
        const rawQty = Number(itemData.qtyOnHand);
        const qtyOnHand = Number.isFinite(rawQty) ? Math.round(rawQty) : "N/A";
        const uom = itemData.standardUOM || "";
        $("#item_quantity").text(`${qtyOnHand} ${uom}`.trim());
        $("#itemQtyContainer").show();
    };

    setItemWeightDiv(itemData) {
        let weightText;
        if (itemData.shipweight === null || itemData.shipweight === undefined) {
            weightText = "No weight per gallon recorded.";
        } else {
            const weightValue = Number(itemData.shipweight);
            weightText = Number.isFinite(weightValue)
                ? `${weightValue.toFixed(2)} lb/gal`
                : "No weight per gallon recorded.";
        }
        $("#item_weight").text(weightText);
        $("#itemWeightContainer").show();
    };

    // setItemProtectionDiv(itemData) {
    //     console.log(itemData);
    //     let protectionValue;
    //     switch (itemData.uv_protection) {
    //         case "no":
    //           switch (itemData.freeze_protection) {
    //             case "no":
    //               return "none";
    //             case "yes":
    //                 protectionValue = "freeze only";
    //           }
    //           break;
    //         case "yes":
    //           switch (itemData.freeze_protection) {
    //             case "no":
    //               return "uv only";
    //             case "yes":
    //                 protectionValue = "both";
    //           }
    //           break;
    //         default:
    //             protectionValue = "unknown";
    //       }
    //     $("#item_protection").text(protectionValue)
    // }

    setFields(itemData) {
        $("#id_item_code").val(itemData.item_code);
        $("#id_item_description").val(itemData.item_description);
    };

    setUpAutofill() {
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        let setItemQuantityDiv = this.setItemQuantityDiv;
        let setItemWeightDiv = this.setItemWeightDiv;
        // let setItemProtectionDiv = this.setItemProtectionDiv;
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
                        if (itemData) {
                            setFields(itemData);
                            setItemQuantityDiv(itemData);
                            setItemWeightDiv(itemData);
                        }
                        // if (itemData.item_description.toLowerCase().includes("blend")){
                        //     $("#itemProtectionContainer").show();
                        //     setItemProtectionDiv(itemData);
                        // } else {
                        //     $("#itemProtectionContainer").hide();
                        //     $("#itemProtectionContainer").text("");
                        // };
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        if (itemData) {
                            setFields(itemData);
                            setItemQuantityDiv(itemData);
                            setItemWeightDiv(itemData);
                        }
                        // if (itemData.item_description.toLowerCase().includes("blend")){
                        //     $("#itemProtectionContainer").show();
                        //     setItemProtectionDiv(itemData);
                        // } else {
                        //     $("#itemProtectionContainer").hide();
                        //     $("#itemProtectionContainer").text("");
                        // };
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
                        if (itemData) {
                            setFields(itemData);
                            setItemQuantityDiv(itemData);
                            setItemWeightDiv(itemData);
                        }
                        // if (itemData.item_description.toLowerCase().includes("blend")){
                        //     $("#itemProtectionContainer").show();
                        //     setItemProtectionDiv(itemData);
                        // } else {
                        //     $("#itemProtectionContainer").hide();
                        //     $("#itemProtectionContainer").text("");
                        // };
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        if (itemData) {
                            setFields(itemData);
                            setItemQuantityDiv(itemData);
                            setItemWeightDiv(itemData);
                        }
                        // if (itemData.item_description.toLowerCase().includes("blend")){
                        //     $("#itemProtectionContainer").show();
                        //     setItemProtectionDiv(itemData);
                        // } else {
                        //     $("#itemProtectionContainer").hide();
                        //     $("#itemProtectionContainer").text("");
                        // };
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
        } catch(err) {
            console.error(err.message);
        }
    };

    BOMFields = getAllBOMFields();

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
        // console.log(BOMFields);
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
        this.reportDefinitions = [];
        this.BOMFields = getAllBOMFields();
        this._autoNavigateSlugs = new Set(['bom-cost-tool', 'sales-order-bom-cost', 'cost-impact-analysis']);
        this._suppressAutoNavigate = false;
        try {
            this.initialize();
        } catch (err) {
            console.error(err.message);
        }
    }

    async initialize() {
        try {
            await this.populateReportOptions();
            this.setUpAutofill();
            this.setUpEventListener();
            this.applyInitialSelection();
        } catch (err) {
            console.error(err.message);
        }
    }

    async populateReportOptions() {
        const selectElement = document.getElementById('id_which_report');
        if (!selectElement) {
            return;
        }

        const cachedDefinitions = window.__miscReportDefinitions;
        if (Array.isArray(cachedDefinitions) && cachedDefinitions.length) {
            this.reportDefinitions = cachedDefinitions.slice();
            this.renderReportOptions(selectElement, this.reportDefinitions);
            return;
        }

        try {
            const response = await fetch('/core/api/misc-report-types/');
            if (!response.ok) {
                throw new Error(`Request failed with status ${response.status}`);
            }
            const payload = await response.json();
            const reports = Array.isArray(payload?.reports) ? payload.reports : [];
            this.reportDefinitions = reports;
            window.__miscReportDefinitions = reports.slice();
            this.renderReportOptions(selectElement, reports);
        } catch (err) {
            console.error('Failed to load misc report definitions:', err);
            selectElement.innerHTML = '';
            const errorOption = document.createElement('option');
            errorOption.value = '';
            errorOption.disabled = true;
            errorOption.selected = true;
            errorOption.textContent = 'Unable to load reports';
            selectElement.appendChild(errorOption);
        }
    }

    renderReportOptions(selectElement, reports) {
        selectElement.innerHTML = '';
        reports.forEach((report) => {
            const option = document.createElement('option');
            option.value = report.slug;
            option.textContent = report.label;
            option.dataset.requiresItem = report.requires_item ? 'true' : 'false';
            option.dataset.requiresQuantity = report.requires_quantity ? 'true' : 'false';
            option.dataset.requiresStartTime = report.requires_start_time ? 'true' : 'false';
            if (report.direct_url) {
                option.dataset.directUrl = report.direct_url;
            } else {
                delete option.dataset.directUrl;
            }
            selectElement.appendChild(option);
        });
    }

    getSelectedReportOption() {
        const selectElement = document.getElementById('id_which_report');
        if (!selectElement) {
            return null;
        }
        const { selectedIndex, options } = selectElement;
        if (selectedIndex < 0 || selectedIndex >= options.length) {
            return null;
        }
        return options[selectedIndex];
    }

    optionRequiresItem(option) {
        return ((option?.dataset?.requiresItem) || '').toString().toLowerCase() === 'true';
    }

    optionRequiresQuantity(option) {
        return ((option?.dataset?.requiresQuantity) || '').toString().toLowerCase() === 'true';
    }

    optionRequiresStartTime(option) {
        return ((option?.dataset?.requiresStartTime) || '').toString().toLowerCase() === 'true';
    }

    optionHasDirectUrl(option) {
        const url = option?.dataset?.directUrl;
        return typeof url === 'string' && url.length > 0;
    }

    shouldAutoNavigate(option) {
        if (!option) {
            return false;
        }
        const slug = (option.value || '').toString().toLowerCase();
        return this._autoNavigateSlugs.has(slug) && this.optionHasDirectUrl(option);
    }

    maybeAutoNavigate(option) {
        if (this.shouldAutoNavigate(option)) {
            window.location.href = option.dataset.directUrl;
        }
    }

    normalizeReportKey(value) {
        return (value || '').toString().toLowerCase().replace(/[^a-z0-9]/g, '');
    }

    applyInitialSelection() {
        const selectElement = document.getElementById('id_which_report');
        if (!selectElement || !selectElement.options.length) {
            return;
        }

        const reportParam = getURLParameter('report');
        if (reportParam) {
            const targetKey = this.normalizeReportKey(reportParam);
            for (let i = 0; i < selectElement.options.length; i += 1) {
                const option = selectElement.options[i];
                const slugKey = this.normalizeReportKey(option.value);
                const labelKey = this.normalizeReportKey(option.textContent);
                if (targetKey === slugKey || targetKey === labelKey) {
                    selectElement.value = option.value;
                    this._suppressAutoNavigate = true;
                    $('#id_which_report').trigger('change');
                    this._suppressAutoNavigate = false;
                    return;
                }
            }
        }

        selectElement.selectedIndex = 0;
        this._suppressAutoNavigate = true;
        $('#id_which_report').trigger('change');
        this._suppressAutoNavigate = false;
    }

    updateFieldVisibility(option) {
        const requiresItem = this.optionRequiresItem(option);
        const requiresQuantity = this.optionRequiresQuantity(option);
        const requiresStartTime = this.optionRequiresStartTime(option);

        $('#itemCodeRow').toggle(requiresItem);
        $('#itemDescriptionRow').toggle(requiresItem);
        $('#itemQuantityRow').toggle(requiresQuantity);
        $('#startTimeRow').toggle(requiresStartTime);

        if (!requiresItem) {
            $('#id_item_code').val('');
            $('#id_item_description').val('');
        }
        if (!requiresQuantity) {
            $('#id_item_quantity').val('');
        }
        if (!requiresStartTime) {
            $('#id_start_time').val('');
        }
    }

    shouldShowGenerateButton(option) {
        if (!option) {
            return false;
        }
        if (this.optionHasDirectUrl(option)) {
            return true;
        }
        if (!this.optionRequiresItem(option)) {
            return true;
        }
        if (this.optionRequiresQuantity(option)) {
            return true;
        }
        const itemCode = $('#id_item_code').val();
        const itemDescription = $('#id_item_description').val();
        return !!(itemCode && itemDescription);
    }

    toggleGenerateButton(option) {
        const effectiveOption = option || this.getSelectedReportOption();
        const shouldShow = this.shouldShowGenerateButton(effectiveOption);
        $('#reportLink').toggle(shouldShow);
    }

    updateReportLink(option) {
        const linkElement = document.getElementById('reportLink');
        const selectedOption = option || this.getSelectedReportOption();
        if (!linkElement || !selectedOption || !selectedOption.value) {
            return;
        }

        if (this.optionHasDirectUrl(selectedOption)) {
            linkElement.href = selectedOption.dataset.directUrl;
            return;
        }

        const slug = selectedOption.value;
        const params = new URLSearchParams();
        const encodedItemCode = this.getEncodedItemCode(selectedOption);
        params.set('itemCode', encodedItemCode);

        const itemQuantity = $('#id_item_quantity').val() || '';
        const startTime = $('#id_start_time').val() || '';
        params.set('itemQuantity', itemQuantity);
        params.set('startTime', startTime);

        const queryString = params.toString();
        linkElement.href = queryString ? `/core/create-report/${slug}?${queryString}` : `/core/create-report/${slug}`;
    }

    getEncodedItemCode(option) {
        if (!option) {
            return '';
        }
        if (!this.optionRequiresItem(option)) {
            return btoa('n-a');
        }
        const itemCode = $('#id_item_code').val() || '';
        try {
            return btoa(itemCode);
        } catch (err) {
            console.error('Failed to encode item code:', err);
            return '';
        }
    }

    setFields(itemData) {
        if (!itemData) {
            return;
        }
        $('#id_item_code').val(itemData.item_code);
        $('#id_item_description').val(itemData.item_description);
        this.updateReportLink();
        this.toggleGenerateButton(this.getSelectedReportOption());
    }

    setUpAutofill() {
        const BOMFields = this.BOMFields;
        const self = this;
        try {
            $(function() {
                $('#id_item_code').autocomplete({
                    minLength: 2,
                    autoFocus: true,
                    source: function(request, response) {
                        const results = $.ui.autocomplete.filter(BOMFields.item_codes, request.term);
                        response(results.slice(0, 10));
                    },
                    change: function(event, ui) {
                        indicateLoading('itemCode');
                        const itemCode = ui && ui.item ? ui.item.label.toUpperCase() : $('#id_item_code').val();
                        const itemData = getItemInfo(itemCode, 'itemCode');
                        self.setFields(itemData);
                    },
                    select: function(event, ui) {
                        indicateLoading();
                        const itemCode = ui.item.label.toUpperCase();
                        const itemData = getItemInfo(itemCode, 'itemCode');
                        self.setFields(itemData);
                    },
                });

                $('#id_item_description').autocomplete({
                    minLength: 3,
                    autoFocus: true,
                    source: function(request, response) {
                        const results = $.ui.autocomplete.filter(BOMFields.item_descriptions, request.term);
                        response(results.slice(0, 300));
                    },
                    change: function(event, ui) {
                        indicateLoading('itemDescription');
                        const itemDescription = ui && ui.item ? ui.item.label.toUpperCase() : $('#id_item_description').val();
                        const itemData = getItemInfo(itemDescription, 'itemDescription');
                        self.setFields(itemData);
                    },
                    select: function(event, ui) {
                        indicateLoading();
                        const itemDescription = ui.item.label.toUpperCase();
                        const itemData = getItemInfo(itemDescription, 'itemDescription');
                        self.setFields(itemData);
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        }
        $('#id_item_code').focus(function() {
            $('.animation').hide();
            $('#warningParagraph').hide();
        });
        $('#id_item_description').focus(function() {
            $('.animation').hide();
            $('#warningParagraph').hide();
        });
    }

    setUpEventListener() {
        const self = this;
        $('#id_which_report').on('change', function() {
            const option = self.getSelectedReportOption();
            self.updateFieldVisibility(option);
            self.toggleGenerateButton(option);
            self.updateReportLink(option);
            if (!self._suppressAutoNavigate) {
                self.maybeAutoNavigate(option);
            }
        });
        $('#id_item_quantity').on('change input', function() {
            self.updateReportLink();
        });
        $('#id_start_time').on('change input', function() {
            self.updateReportLink();
        });
        $('#id_item_code, #id_item_description').on('change', function() {
            self.updateReportLink();
            self.toggleGenerateButton(self.getSelectedReportOption());
        });
    }
}

export { FilterForm } from './tableObjects.js';

export class BlendShortagesFilterForm {
    constructor() {
        try{
            this.setUpFiltering();
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
    constructor(options = {}) {
        this.selectSelector = options.selectSelector || '#auditGroupLinks';
        this.tableSelector = options.tableSelector || '#displayTable';
        this.rowSelector = options.rowSelector || 'tr.filterableRow';
        this.ignoreSelectors = Array.isArray(options.ignoreSelectors) ? options.ignoreSelectors : [];

        try {
            this.setUpDropDownFiltering();
        } catch (err) {
            console.error(err.message);
        }
    }

    setUpDropDownFiltering() {
        const $select = $(this.selectSelector);
        if (!$select.length) {
            return;
        }

        $select.on('change', () => this.applyFilter($select.val()));
    }

    applyFilter(selectedValue = '') {
        const value = (selectedValue || '').toString().toLowerCase().trim();

        $(`${this.tableSelector} ${this.rowSelector}`).each((_, element) => {
            const $row = $(element);
            const rowText = this._getRowSearchText($row);

            const isMatch = !value || rowText.includes(value);

            $row.toggle(isMatch);
            if (isMatch) {
                $row.addClass('chosen');
            } else {
                $row.removeClass('chosen');
            }
        });
    }

    _getRowSearchText($row) {
        let text;

        if (this.ignoreSelectors.length) {
            const $clone = $row.clone();
            this.ignoreSelectors.forEach((selector) => {
                $clone.find(selector).remove();
            });
            text = $clone.text();
        } else {
            text = $row.text();
        }

        return (text || '').toString().toLowerCase().replace(/\s+/g, '');
    }
}

export class ItemReferenceFieldPair {
    constructor(itemCodeInputField, itemDescriptionInputField) {
        try{
            this.setUpAutofill(itemCodeInputField, itemDescriptionInputField)
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
        } catch(err) {
            console.error(err.message);
        }
    }

    BOMFields = getAllBOMFields('blends-and-components');

    setFields(locationData, itemCodeField, itemDescriptionField, locationField, unitsField) {
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

export class BlendToteLabelLookupForm {
    constructor() {
        try {
            this.setUpAutofill();
        } catch(err) {
            console.error(err.message);
        }
    };

    BOMFields = getAllBOMFields();

    setItemProtectionDiv(itemData) {
        let itemProtection;
        $("#blend-label-uv-img").hide();
        $("#blend-label-freeze-img").hide();
        $("#blend-label-blank-freeze-img").hide();
        $("#blend-label-blank-uv-img").hide();
        $("#blend-label-protection").show();
        if (itemData.uv_protection == 'yes' && itemData.freeze_protection == 'yes'){
            itemProtection = "UV and Freeze Protection Required";
            let uvImg = $('#blend-label-uv-img');
            uvImg.show();
            let freezeImg = $('#blend-label-freeze-img');
            freezeImg.show();
        } else if (itemData.uv_protection == 'no' && itemData.freeze_protection == 'yes'){
            itemProtection = "Freeze Protection Required";
            let freezeImg = $('#blend-label-freeze-img');
            freezeImg.show();
            let blankUVImg = $('#blend-label-blank-uv-img');
            blankUVImg.show();
        } else if (itemData.uv_protection == 'yes' && itemData.freeze_protection == 'no'){
            itemProtection = "UV Protection Required";
            let uvImg = $('#blend-label-uv-img');
            uvImg.show();
            let blankFreezeImg = $('#blend-label-blank-freeze-img');
            blankFreezeImg.show();
        } else {
            itemProtection = "No Protection Required";
            let blankUVImg = $('#blend-label-blank-uv-img');
            blankUVImg.show();
            let blankFreezeImg = $('#blend-label-blank-freeze-img');
            blankFreezeImg.show();
        };
        $("#blend-label-protection").text(itemProtection);
    }

    setFields(itemData) {
        $("#id_item_code").val(itemData.item_code);
        $("#id_item_description").val(itemData.item_description);
        $("#blend-label-item-code").text(itemData.item_code);
        $("#blend-label-item-description").text(itemData.item_description);
        let dropdown = $("#label-lot-number-dropdown");
        dropdown.empty(); // Clear existing options

        let lotNumbers = getMostRecentLotRecords(btoa(itemData.item_code));
        for (let key in lotNumbers) {
            let option = document.createElement("option");
            option.text = `${key} (${lotNumbers[key]} gal on hand)`;
            option.value = key;
            dropdown.append(option);
        }
        if (Object.keys(lotNumbers).length > 0) {
            let firstLotNumber = Object.keys(lotNumbers)[0];
            $("#blend-label-lot-number").text(firstLotNumber);
        }
    };

    setUpAutofill() {
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
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
