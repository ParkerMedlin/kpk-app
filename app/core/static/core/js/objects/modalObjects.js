import { getAllBOMFields, getItemInfo, getURLParameter } from '../requestFunctions/requestFunctions.js';
import { indicateLoading } from '../uiFunctions/uiFunctions.js';

export class DeleteFoamFactorModal {
    modalButtonLink = document.getElementById("deleteFoamFactorModalButtonLink");
    modalLabel = document.getElementById("deleteFoamFactorModalLabel");
    modalBody = document.getElementById("deleteFoamFactorModalBody");
    modalButton = document.getElementById("deleteFoamFactorModalButton");
    modalButtonLink = document.getElementById("deleteFoamFactorModalButtonLink")

    setModalButtons(e) {
        try {
            let lot_id = e.currentTarget.getAttribute("dataitemid");
            document.getElementById("deleteFoamFactorModalButtonLink").setAttribute("href", `/core/delete-foam-factor/${lot_id}`);
            console.log("DeleteFoamFactorModal buttons set up.");
        } catch(err) {
            console.error(err.message);
        };
    };
};

export class DeleteLotNumModal {
    modalButtonLink = document.getElementById("deleteLotNumModalButtonLink");
    modalLabel = document.getElementById("deleteLotNumModalLabel");
    modalBody = document.getElementById("deleteLotNumModalBody");
    modalButton = document.getElementById("deleteLotNumModalButton");
    modalButtonLink = document.getElementById("deleteLotNumModalButtonLink")

    setModalButtons(e) {
        try {
            let lot_ids = e.currentTarget.getAttribute("dataitemid");
            let lot_id_arr = lot_ids.split(',');
            console.log(lot_id_arr.length);
            console.log(lot_id_arr);
            if (lot_id_arr.length > 1) {
                document.getElementById("deleteLotNumModalQuestion").innerHTML = "Are you sure you want to delete these records?"
            }
            let encoded_list = btoa(JSON.stringify(lot_ids));
            document.querySelectorAll('.rowCheckBox').forEach(checkBox => {
                checkBox.checked = false;
            });
            document.getElementById("deleteLotNumModalButtonLink").setAttribute("href", `/core/delete-lot-num-records/${encoded_list}`);
            console.log("DeleteLotNumModal buttons set up.");
        } catch(err) {
            console.error(err.message);
        };
    };
};

export class DeleteCountRecordModal {
    modalButtonLink = document.getElementById("deleteCountRecordsModalButtonLink");
    modalLabel = document.getElementById("deleteCountRecordsModalLabel");
    modalBody = document.getElementById("deleteCountRecordsModalBody");
    modalButton = document.getElementById("deleteCountRecordsModalButton");

    setModalButtons(e) {
        try {
            let count_id = e.currentTarget.getAttribute("dataitemid");
            let encoded_list = btoa(JSON.stringify(count_id));
            let encoded_full_list_placeholder = btoa(JSON.stringify('Nothin'));
            let urlParameters = new URLSearchParams(window.location.search);
            let recordType = urlParameters.get('recordType');
            console.log(`/core/delete-count-record?redirectPage=count-records&listToDelete=${encoded_list}&fullList=${encoded_full_list_placeholder}&recordType=${recordType}`)
            console.log(count_id);
            $("#deleteCountRecordsModalButtonLink").attr("href", `/core/delete-count-record?redirectPage=count-records&listToDelete=${encoded_list}&fullList=${encoded_full_list_placeholder}&recordType=${recordType}`);
            console.log("DeleteCountRecordModal buttons set up.");
        } catch(err) { 
            console.error(err.message);
        };
    };
}

export class EditConfirmCountRecordModal {
    modalButtonLink = $("#editCountRecordsModalButtonLink");
    modalLabel = document.getElementById("editCountRecordsModalLabel");
    modalBody = document.getElementById("editCountRecordsModalBody");
    modalButton = document.getElementById("editCountRecordsModalButton");
    modalButtonLink = document.getElementById("editCountRecordsModalButtonLink");

    setModalButtons(e) {
        try {
            let count_id = e.currentTarget.getAttribute("dataitemid");
            let encoded_list = btoa(JSON.stringify(count_id));
            let urlParameters = new URLSearchParams(window.location.search);
            let recordType = urlParameters.get('recordType');
            $("#editCountRecordsModalButtonLink").attr("href", `/core/count-list/display/${encoded_list}?recordType=${recordType}`);
            console.log("EditConfirmCountRecordModal buttons set up.");
        } catch(err) {
            console.error(err.message);
        };
    };
}

export class EditLotNumModal {
    constructor(){
        try {
            this.setUpAutofill();
            this.setUpEventListeners();
            this.setLotNumberFieldReadOnly();
            console.log("Instance of class EditLotNumModal created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    itemCodeInput = document.getElementById("id_editLotNumModal-item_code");
    itemDescriptionInput = document.getElementById("id_editLotNumModal-item_description");
    quantityInput = document.getElementById("id_editLotNumModal-lot_quantity");
    lineInput = document.getElementById("id_editLotNumModal-line");
    deskInput = document.getElementById("id_editLotNumModal-desk");
    addLotNumButton = document.getElementById("addLotNumButton");
    runDateInput = document.getElementById("id_editLotNumModal-run_date");
    $addLotNumButton = $("#addLotNumButton");
    formElement = $("#addLotNumFormElement");
    BOMFields = getAllBOMFields('blend');

    setLotNumberFieldReadOnly() {
        document.getElementById("id_editLotNumModal-lot_number").setAttribute("readonly", true);
    }

    setAddLotModalInputs(e) {
        $('#id_editLotNumModal-item_code').val(e.currentTarget.getAttribute('data-itemcode'));
        $('#id_editLotNumModal-item_description').val(e.currentTarget.getAttribute('data-desc'));
        if (e.currentTarget.getAttribute('data-lotqty')){
            $('#id_editLotNumModal-lot_quantity').val(Math.round(parseFloat(e.currentTarget.getAttribute('data-lotqty'))));
        } else if (e.currentTarget.getAttribute('data-totalqty')) {
            let thisQuantity = Math.round(parseFloat(e.currentTarget.getAttribute('data-totalqty')));
            if (thisQuantity>5100) {
                thisQuantity=5100;
            } else if (thisQuantity==5040) {
                thisQuantity=5100;
            }
            $('#id_editLotNumModal-lot_quantity').val(Math.round(parseFloat(e.currentTarget.getAttribute('data-totalqty'))));
        }
        $('#id_editLotNumModal-line').val(e.currentTarget.getAttribute('data-line'));
        $('#id_editLotNumModal-desk').val(e.currentTarget.getAttribute('data-desk'));
        $("#id_editLotNumModal-run_date").val(e.currentTarget.getAttribute('data-rundate'));
    };

    setFields(itemData) {
        $('#id_editLotNumModal-item_code').val(itemData.item_code);
        $('#id_editLotNumModal-item_description').val(itemData.item_description);
    };

    setUpAutofill(){
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $('#id_editLotNumModal-item_code').autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemCode = $('#id_editLotNumModal-item_code').val();
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
                $("#id_editLotNumModal-item_description").autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemDesc = $("#id_editLotNumModal-item_description").val();
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
        $('#id_editLotNumModal-item_code').focus(function(){
            $('.animation').hide();
        }); 
        $("#id_editLotNumModal-item_description").focus(function(){
            $('.animation').hide();
        });
    };

    setUpEventListeners() {
        $('#id_editLotNumModal-line').change(function(){
            if ($('#id_editLotNumModal-line').val() == 'Prod') {
                $('#id_editLotNumModal-desk').val('Desk_1');
            } else if ($('#id_editLotNumModal-line').val() == 'Hx') {
                $('#id_editLotNumModal-desk').val('Horix');
            } else if ($('#id_editLotNumModal-line').val() == 'Dm') {
                $('#id_editLotNumModal-desk').val('Drums');
            } else if ($('#id_editLotNumModal-line').val() == 'Totes') {
                $('#id_editLotNumModal-desk').val('Desk_1');
            } else if ($('#id_editLotNumModal-line').val() == 'Pails') {
                $('#id_editLotNumModal-desk').val('Desk_1');
            };
        });
    };

};

export class EditFoamFactorModal {
    constructor(){
        try {
            this.setUpAutofill();
            this.setUpEventListeners();
            console.log("Instance of class EditFoamFactorModal created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    itemCodeInput = document.getElementById("id_editFoamFactorModal-item_code");
    itemDescriptionInput = document.getElementById("id_editFoamFactorModal-item_description");
    $addFoamFactorButton = $("#addFoamFactorButton");
    formElement = $("#addFoamFactorFormElement");
    BOMFields = getAllBOMFields('blend');


    setAddFoamFactorModalInputs(e) {
        $('#id_editFoamFactorModal-item_code').val(e.currentTarget.getAttribute('data-itemcode'));
        $('#id_editFoamFactorModal-item_description').val(e.currentTarget.getAttribute('data-desc'));
    };

    setFields(itemData) {
        $('#id_editFoamFactorModal-item_code').val(itemData.item_code);
        $('#id_editFoamFactorModal-item_description').val(itemData.item_description);
    };

    setUpAutofill(){
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $('#id_editFoamFactorModal-item_code').autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemCode = $('#id_editFoamFactorModal-item_code').val();
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
                $("#id_editFoamFactorModal-item_description").autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemDesc = $("#id_editFoamFactorModal-item_description").val();
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
        $('#id_editFoamFactorModal-item_code').focus(function(){
            $('.animation').hide();
        }); 
        $("#id_editFoamFactorModal-item_description").focus(function(){
            $('.animation').hide();
        });
    };

    setUpEventListeners() {
        $('#id_editFoamFactorModal-line').change(function(){
            if ($('#id_editFoamFactorModal-line').val() == 'Prod') {
                $('#id_editFoamFactorModal-desk').val('Desk_1');
            } else if ($('#id_editFoamFactorModal-line').val() == 'Hx') {
                $('#id_editFoamFactorModal-desk').val('Horix');
            } else if ($('#id_editFoamFactorModal-line').val() == 'Dm') {
                $('#id_editFoamFactorModal-desk').val('Drums');
            } else if ($('#id_editFoamFactorModal-line').val() == 'Totes') {
                $('#id_editFoamFactorModal-desk').val('Desk_1');
            } else if ($('#id_editFoamFactorModal-line').val() == 'Pails') {
                $('#id_editFoamFactorModal-desk').val('Desk_1');
            };
        });
    };

};

export class AddFoamFactorModal {
    constructor(){
        try {
            this.setUpAutofill();
        console.log("Instance of class AddFoamFactorModal created.");
        } catch(err) {
            console.error(err.message);
        };
    }

    itemCodeInput = document.getElementById("id_addFoamFactorModal-item_code");
    itemDescriptionInput = document.getElementById("id_addFoamFactorModal-item_description");
    addFoamFactorButton = document.getElementById("addFoamFactorButton");
    $addFoamFactorButton = $("#addFoamFactorButton");
    formElement = $("#addFoamFactorFormElement");
    BOMFields = getAllBOMFields('blend');


    setAddLotModalInputs(e) {
        $('#id_addFoamFactorModal-item_code').val(e.currentTarget.getAttribute('data-itemcode'));
        $('#id_addFoamFactorModal-item_description').val(e.currentTarget.getAttribute('data-desc'));
    };

    setFields(itemData) {
        $('#id_addFoamFactorModal-item_code').val(itemData.item_code);
        $('#id_addFoamFactorModal-item_description').val(itemData.item_description);
    };

    setUpAutofill(){
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $('#id_addFoamFactorModal-item_code').autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemCode = $('#id_addFoamFactorModal-item_code').val();
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
                $("#id_addFoamFactorModal-item_description").autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemDesc = $("#id_addFoamFactorModal-item_description").val();
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
        $('#id_addFoamFactorModal-item_code').focus(function(){
            $('.animation').hide();
        }); 
        $("#id_addFoamFactorModal-item_description").focus(function(){
            $('.animation').hide();
        });
    };

};

export class AddLotNumModal {
    constructor(){
        try {
            this.setUpAutofill();
            this.setUpEventListeners();
            this.setLotNumberFieldReadOnly();
        console.log("Instance of class AddLotNumModal created.");
        } catch(err) {
            console.error(err.message);
        };
    }

    itemCodeInput = document.getElementById("id_addLotNumModal-item_code");
    itemDescriptionInput = document.getElementById("id_addLotNumModal-item_description");
    quantityInput = document.getElementById("id_addLotNumModal-lot_quantity");
    lineInput = document.getElementById("id_addLotNumModal-line");
    deskInput = document.getElementById("id_addLotNumModal-desk");
    addLotNumButton = document.getElementById("addLotNumButton");
    runDateInput = document.getElementById("id_addLotNumModal-run_date");
    $addLotNumButton = $("#addLotNumButton");
    formElement = $("#addLotNumFormElement");
    BOMFields = getAllBOMFields('blend');

    setLotNumberFieldReadOnly() {
        $("#id_addLotNumModal-lot_number").prop('readonly', true);
    }

    setAddLotModalInputs(e) {
        $('#id_addLotNumModal-item_code').val(e.currentTarget.getAttribute('data-itemcode'));
        $('#id_addLotNumModal-item_description').val(e.currentTarget.getAttribute('data-desc'));
        let thisQuantity;
        if (e.currentTarget.getAttribute('data-lotqty')){
            thisQuantity = Math.round(parseFloat(e.currentTarget.getAttribute('data-lotqty')));
        } else if (e.currentTarget.getAttribute('data-totalqty')) {
            thisQuantity = Math.round(parseFloat(e.currentTarget.getAttribute('data-totalqty')));
        }
        if (e.currentTarget.getAttribute('data-line') == 'Prod' && thisQuantity > 2800) {
            thisQuantity = 2800;
        }
        if (e.currentTarget.getAttribute('data-line') == 'Dm' && thisQuantity > 2925) {
            thisQuantity = 2925;
        }
        if (e.currentTarget.getAttribute('data-line') == 'Hx' && thisQuantity > 5100) {
            thisQuantity = 5100;
        }
        $('#id_addLotNumModal-lot_quantity').val(thisQuantity);
        $('#id_addLotNumModal-line').val(e.currentTarget.getAttribute('data-line'));
        $('#id_addLotNumModal-desk').val(e.currentTarget.getAttribute('data-desk'));
        $("#id_addLotNumModal-run_date").val(e.currentTarget.getAttribute('data-rundate'));
    };

    setFields(itemData) {
        $('#id_addLotNumModal-item_code').val(itemData.item_code);
        $('#id_addLotNumModal-item_description').val(itemData.item_description);
    };

    setUpAutofill(){
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $('#id_addLotNumModal-item_code').autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemCode = $('#id_addLotNumModal-item_code').val();
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
                $("#id_addLotNumModal-item_description").autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemDesc = $("#id_addLotNumModal-item_description").val();
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
        $('#id_addLotNumModal-item_code').focus(function(){
            $('.animation').hide();
        }); 
        $("#id_addLotNumModal-item_description").focus(function(){
            $('.animation').hide();
        });
    };

    setUpEventListeners() {
        $('#id_addLotNumModal-line').change(function(){
            if ($('#id_addLotNumModal-line').val() == 'Prod') {
                $('#id_addLotNumModal-desk').val('Desk_1');
            } else if ($('#id_addLotNumModal-line').val() == 'Hx') {
                $('#id_addLotNumModal-desk').val('Horix');
            } else if ($('#id_addLotNumModal-line').val() == 'Dm') {
                $('#id_addLotNumModal-desk').val('Desk_1');
            } else if ($('#id_addLotNumModal-line').val() == 'Totes') {
                $('#id_addLotNumModal-desk').val('Desk_1');
            } else if ($('#id_addLotNumModal-line').val() == 'Pails') {
                $('#id_addLotNumModal-desk').val('Desk_1');
            };
        });
        
            // Your code here
        // });
        
        // $('#addLotNumModal').click(function(){
        $('#addLotNumModal').on('shown.bs.modal', function () {
            let latestLotNumber;
            $.ajax({
                url: '/core/get-latest-lot-num-record/',
                async: false,
                dataType: 'json',
                success: function(data) {
                    latestLotNumber = data;
                }
            });

            const today = new Date();
            const monthLetterAndYear = String.fromCharCode(64 + today.getMonth() + 1) + String(today.getFullYear()).slice(-2);
            const fourDigitNumber = String(parseInt(latestLotNumber.lot_number.toString().slice(-4)) + 1).padStart(4, '0');
            const nextLotNumber = monthLetterAndYear + fourDigitNumber;

            $("#id_addLotNumModal-lot_number").val(nextLotNumber);

        });

        $('#addLotNumDuplicateSelector').on('change', function () {
            const duplicateCount = $(this).val()
            console.log(duplicateCount)
            $('#addLotNumFormElement').prop('action', `/core/add-lot-num-record/?redirect-page=lot-num-records&duplicates=${duplicateCount}&redirect-page=blend-schedule`)
        });
       
    };

};

export class AddCountListItemModal {
    constructor(){
        try {
            this.setUpAutofill();
            console.log("Instance of class AddCountListItemModal created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    itemCodeInput = $("#id_countListModal_item_code");
    itemDescriptionInput = $("#id_countListModal_item_description");
    BOMFields = getAllBOMFields(getURLParameter('recordType'));

    setModalButtonLink(itemData) {
        let encodedItemCode = btoa(JSON.stringify(itemData.item_code));
        let hrefWithoutParams = window.location.href.split('?')[0];
        let encodedPkList = hrefWithoutParams.substring(hrefWithoutParams.lastIndexOf('/') + 1);
        let urlParameters = new URLSearchParams(window.location.search);
        let recordType = urlParameters.get('recordType');
        $("#addCountLink").attr("href", `/core/count-list/add?itemsToAdd=${encodedItemCode}&encodedPkList=${encodedPkList}&recordType=${recordType}`);
    }

    setFields(itemData) {
        $('#id_countListModal_item_code').val(itemData.item_code);
        $('#id_countListModal_item_description').val(itemData.item_description);
    };

    setUpAutofill() {
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        let setModalButtonLink = this.setModalButtonLink;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $("#id_countListModal_item_code").autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemCode = $("#id_countListModal_item_code").val();
                        } else {
                            itemCode = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                        setModalButtonLink(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemCode, "itemCode");
                        setFields(itemData);
                        setModalButtonLink(itemData);
                    },
                });
                //   ===============  Description Search  ===============
                $("#id_countListModal_item_description").autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemDesc = $("#id_countListModal_item_description").val();
                        } else {
                            itemDesc = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                        setModalButtonLink(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemInfo(itemDesc, "itemDescription");
                        setFields(itemData);
                        setModalButtonLink(itemData);
                    },
                });
            });
        } catch (err) {
            console.error(err.message);
        };
        $('#id_countListModal_item_code').focus(function(){
            $('.animation').hide();
        }); 
        $("#id_countListModal-item_description").focus(function(){
            $('.animation').hide();
        });
    }
    

}

