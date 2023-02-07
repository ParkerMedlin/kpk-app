import { getAllBOMFields, getItemInfo } from '../requestFunctions/requestFunctions.js';
import { indicateLoading } from '../uiFunctions/uiFunctions.js';



export class DeleteLotNumModal {
    modalButtonLink = document.getElementById("deleteLotNumModalButtonLink");
    modalLabel = document.getElementById("deleteLotNumModalLabel");
    modalBody = document.getElementById("deleteLotNumModalBody");
    modalButton = document.getElementById("deleteLotNumModalButton");
    modalButtonLink = document.getElementById("deleteLotNumModalButtonLink")

    setModalButtons(e) {
        let modalButtonLink = this.modalButtonLink;
        let count_ids = e.currentTarget.getAttribute("dataitemid");
        let encoded_list = btoa(JSON.stringify(count_ids));
        document.querySelectorAll('.rowCheckBox').forEach(checkBox => {
            checkBox.checked = false;
        });
        modalButtonLink.setAttribute("href", `/core/deletelotnumrecords/${encoded_list}`);
        $('button[data-bs-dismiss="modal"]').click(function(){
            modalButtonLink.setAttribute("href", "");
        });
    };
};

export class DeleteCountRecordModal {
    modalButtonLink = document.getElementById("deleteCountRecordModalButtonLink");
    modalLabel = document.getElementById("deleteCountRecordModalLabel");
    modalBody = document.getElementById("deleteCountRecordModalBody");
    modalButton = document.getElementById("deleteCountRecordModalButton");
    modalButtonLink = document.getElementById("deleteCountRecordModalButtonLink");

    setModalButtons(e) {
        let buttonLink = this.modalButtonLink;
        let count_id = e.currentTarget.getAttribute("dataitemid");
        let encoded_list = btoa(JSON.stringify(count_id));
        buttonLink.setAttribute("href", `/core/countlist/delete_countrecord/countrecords/${encoded_list}`);
        $('button[data-bs-dismiss="modal"]').click(function(){
            modalButtonLink.setAttribute("href", "");
        });
    };
}

export class EditConfirmCountRecordModal {
    modalButtonLink = $("#editCountRecordsModalButtonLink");
    modalLabel = document.getElementById("editCountRecordsModalLabel");
    modalBody = document.getElementById("editCountRecordsModalBody");
    modalButton = document.getElementById("editCountRecordsModalButton");
    modalButtonLink = document.getElementById("editCountRecordsModalButtonLink");

    setModalButtons(e) {
        let count_id = e.currentTarget.getAttribute("dataitemid");
        let encoded_list = btoa(JSON.stringify(count_id));
        $("#editCountRecordsModalButtonLink").attr("href", `/core/countlist/display/${encoded_list}`);
        $('button[data-bs-dismiss="modal"]').click(function(){
            buttonLink.setAttribute("href", "");
        });
    };
}

export class AddLotNumModal {
    constructor(){
        this.autoFillSetup();
    }

    itemCodeInput = document.getElementById("id_lotNumModal-item_code");
    itemDescriptionInput = document.getElementById("id_lotNumModal-item_description");
    quantityInput = document.getElementById("id_lotNumModal-lot_quantity");
    lineInput = document.getElementById("id_lotNumModal-line");
    deskInput = document.getElementById("id_lotNumModal-desk");
    addLotNumButton = document.getElementById("addLotNumButton");
    runDateInput = document.getElementById("id_lotNumModal-run_date");
    $addLotNumButton = $("#addLotNumButton");
    BOMFields = getAllBOMFields('blends-only');

    setAddLotModalInputs(e) {
        $('#id_lotNumModal-item_code').val(e.currentTarget.getAttribute('data-itemcode'));
        $('#id_lotNumModal-item_description').val(e.currentTarget.getAttribute('data-desc'));
        if (e.currentTarget.getAttribute('data-lotqty')){
            $('#id_lotNumModal-lot_quantity').val(Math.round(parseFloat(e.currentTarget.getAttribute('data-lotqty'))));
        } else if (e.currentTarget.getAttribute('data-threewkqty')) {
            let thisQuantity = Math.round(parseFloat(e.currentTarget.getAttribute('data-threewkqty')));
            if (thisQuantity>5100) {
                thisQuantity=5100;
            } else if (thisQuantity==5040) {
                thisQuantity=5100;
            }
            $('#id_lotNumModal-lot_quantity').val(Math.round(parseFloat(e.currentTarget.getAttribute('data-threewkqty'))));
        }
        $('#id_lotNumModal-line').val(e.currentTarget.getAttribute('data-line'));
        $('#id_lotNumModal-desk').val(e.currentTarget.getAttribute('data-desk'));
        $("#id_lotNumModal-run_date").val(e.currentTarget.getAttribute('data-rundate'));
    };

    setFields(itemData) {
        $('#id_lotNumModal-item_code').val(itemData.item_code);
        $('#id_lotNumModal-item_description').val(itemData.item_description);
    };

    autoFillSetup(){
        let BOMFields = this.BOMFields;
        let setFields = this.setFields;
        try {
            $( function() {
                // ===============  Item Number Search  ==============
                $('#id_lotNumModal-item_code').autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemCode = $('#id_lotNumModal-item_code').val();
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
                $("#id_lotNumModal-item_description").autocomplete({ // Sets up a dropdown for the part number field 
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
                            itemDesc = $("#id_lotNumModal-item_description").val();
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
        } catch (pnError) {
            console.log(pnError)
        };
        $('#id_lotNumModal-item_code').focus(function(){
            $('.animation').hide();
        }); 
        $("#id_lotNumModal-item_description").focus(function(){
            $('.animation').hide();
        });
    };

};

export class AddScheduleItemModal {
    setUpScheduleModal(targetElement){
        this.thisForm.show();
        this.theOtherForm.hide();
        this.itemCodeInput.val(targetElement.attr('data-itemcode')); 
        this.itemDescriptionInput.val(targetElement.attr('data-desc'));
        this.lotNumInput.val(targetElement.attr('data-lotnum'));
        this.qtyInput.val(targetElement.attr('data-lotqty'));
        this.totesNeedInput.val(Math.ceil(targetElement.attr('data-lotqty')/250));
        this.blendAreaInput.val(targetElement.attr('data-blenddesk'));
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
        this.autoFillSetup();
    };

    itemCodeInput = $("#id_countListModal_item_code");
    itemDescriptionInput = $("#id_countListModal_item_description");
    BOMFields = getAllBOMFields('blends-only');

    setModalButtonLink(itemData) {
        let encodedItemCode = btoa(JSON.stringify(itemData.item_code));
        let encodedPkList = window.location.href.substring(window.location.href.lastIndexOf('/') + 1);
        $("#addCountLink").attr("href", `/core/countlist/add/${encodedItemCode}/${encodedPkList}`);
    }

    setFields(itemData) {
        $('#id_countListModal_item_code').val(itemData.item_code);
        $('#id_countListModal_item_description').val(itemData.item_description);
    };

    autoFillSetup() {
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
        } catch (pnError) {
            console.log(pnError)
        };
        $('#id_countListModal_item_code').focus(function(){
            $('.animation').hide();
        }); 
        $("#id_countListModal-item_description").focus(function(){
            $('.animation').hide();
        });
    }
    

}

