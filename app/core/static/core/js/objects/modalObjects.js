import { getAllBOMFields, getItemInfo } from '../requestFunctions/requestFunctions.js';
import { indicateLoading } from '../uiFunctions/uiFunctions.js';



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
            console.log(`/core/delete-count-record/count-records/${encoded_list}/${encoded_full_list_placeholder}`)
            console.log(count_id);
            $("#deleteCountRecordsModalButtonLink").attr("href", `/core/delete-count-record/count-records/${encoded_list}/${encoded_full_list_placeholder}`);
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
            $("#editCountRecordsModalButtonLink").attr("href", `/core/count-list/display/${encoded_list}`);
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
    BOMFields = getAllBOMFields('blends-only');

    setLotNumberFieldReadOnly() {
        document.getElementById("id_editLotNumModal-lot_number").setAttribute("readonly", true);
    }

    setAddLotModalInputs(e) {
        $('#id_editLotNumModal-item_code').val(e.currentTarget.getAttribute('data-itemcode'));
        $('#id_editLotNumModal-item_description').val(e.currentTarget.getAttribute('data-desc'));
        if (e.currentTarget.getAttribute('data-lotqty')){
            $('#id_editLotNumModal-lot_quantity').val(Math.round(parseFloat(e.currentTarget.getAttribute('data-lotqty'))));
        } else if (e.currentTarget.getAttribute('data-threewkqty')) {
            let thisQuantity = Math.round(parseFloat(e.currentTarget.getAttribute('data-threewkqty')));
            if (thisQuantity>5100) {
                thisQuantity=5100;
            } else if (thisQuantity==5040) {
                thisQuantity=5100;
            }
            $('#id_editLotNumModal-lot_quantity').val(Math.round(parseFloat(e.currentTarget.getAttribute('data-threewkqty'))));
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
                $('#id_editLotNumModal-desk').val('Totes');
            } else if ($('#id_editLotNumModal-line').val() == 'Pails') {
                $('#id_editLotNumModal-desk').val('Pails');
            };
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
    BOMFields = getAllBOMFields('blends-only');

    setLotNumberFieldReadOnly() {
        $("#id_addLotNumModal-lot_number").prop('readonly', true);
    }

    setAddLotModalInputs(e) {
        $('#id_addLotNumModal-item_code').val(e.currentTarget.getAttribute('data-itemcode'));
        $('#id_addLotNumModal-item_description').val(e.currentTarget.getAttribute('data-desc'));
        if (e.currentTarget.getAttribute('data-lotqty')){
            $('#id_addLotNumModal-lot_quantity').val(Math.round(parseFloat(e.currentTarget.getAttribute('data-lotqty'))));
        } else if (e.currentTarget.getAttribute('data-threewkqty')) {
            let thisQuantity = Math.round(parseFloat(e.currentTarget.getAttribute('data-threewkqty')));
            if (thisQuantity>5100) {
                thisQuantity=5100;
            } else if (thisQuantity==5040) {
                thisQuantity=5100;
            }
            $('#id_addLotNumModal-lot_quantity').val(Math.round(parseFloat(e.currentTarget.getAttribute('data-threewkqty'))));
        }
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
                $('#id_addLotNumModal-desk').val('Drums');
            } else if ($('#id_addLotNumModal-line').val() == 'Totes') {
                $('#id_addLotNumModal-desk').val('Totes');
            } else if ($('#id_addLotNumModal-line').val() == 'Pails') {
                $('#id_addLotNumModal-desk').val('Pails');
            };
        });
    };

};

export class AddScheduleItemModal {

    setUpScheduleModal(targetElement){
        try {
            this.thisForm.show();
            this.theOtherForm.hide();
            this.itemCodeInput.val(targetElement.attr('data-itemcode')); 
            this.itemDescriptionInput.val(targetElement.attr('data-desc'));
            this.lotNumInput.val(targetElement.attr('data-lotnum'));
            this.qtyInput.val(targetElement.attr('data-lotqty'));
            this.totesNeedInput.val(Math.ceil(targetElement.attr('data-lotqty')/250));
            this.blendAreaInput.val(targetElement.attr('data-blenddesk'));
            console.log("AddScheduleItemModal set up.");
        } catch(err) {
            console.error(err.message);
        };
    };

};

export class AddDeskOneItemModal extends AddScheduleItemModal {
    desk = 'Desk_1'
    thisForm = $("#deskOneFormContainer");
    theOtherForm = $("#deskTwoFormContainer");
    itemCodeInput = $("#id_deskone-item_code");
    itemDescriptionInput = $("#id_deskone-item_description");
    lotNumInput = $("#id_deskone-lot");
    qtyInput = $("#id_deskone-quantity");
    totesNeedInput = $("#id_deskone-totes_needed");
    blendAreaInput = $("#id_deskone-blend_area");
};

export class AddDeskTwoItemModal extends AddScheduleItemModal {
    desk = 'Desk_2'
    thisForm = $("#deskTwoFormContainer");
    theOtherForm = $("#deskOneFormContainer");
    itemCodeInput = $("#id_desktwo-item_code");
    itemDescriptionInput = $("#id_desktwo-item_description");
    lotNumInput = $("#id_desktwo-lot");
    qtyInput = $("#id_desktwo-quantity");
    totesNeedInput = $("#id_desktwo-totes_needed");
    blendAreaInput = $("#id_desktwo-blend_area");
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
    BOMFields = getAllBOMFields('blends-only');

    setModalButtonLink(itemData) {
        let encodedItemCode = btoa(JSON.stringify(itemData.item_code));
        let encodedPkList = window.location.href.substring(window.location.href.lastIndexOf('/') + 1);
        $("#addCountLink").attr("href", `/core/count-list/add/${encodedItemCode}/${encodedPkList}`);
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

