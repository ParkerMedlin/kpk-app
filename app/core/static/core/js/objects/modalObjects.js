


export class DeleteLotNumModal {
    confirmModalButtonLink = document.getElementById("confirmModalButtonLink");
    lotNumConfirmModalLabel = document.getElementById("lotNumConfirmModalLabel");
    lotNumConfirmModalBody = document.getElementById("lotNumConfirmModalBody");
    confirmModalButton = document.getElementById("confirmModalButton");

    setModalButton(e) {
        let count_id = e.currentTarget.getAttribute("dataitemid");
        let encoded_list = btoa(JSON.stringify(count_id));
        document.querySelectorAll('.rowCheckBox').forEach(checkBox => {
            checkBox.checked = false;
        });
        document.getElementById("confirmModalButtonLink").setAttribute("href", `/core/deletelotnumrecords/${encoded_list}`);
        document.getElementById("lotNumConfirmModalLabel").innerText = 'Confirm Deletion';
        document.getElementById("lotNumConfirmModalBody").innerText = 'Are you sure?';
        document.getElementById("confirmModalButton").innerText = 'Delete';
        document.getElementById("confirmModalButton").classList.remove( "btn-primary" )
        document.getElementById("confirmModalButton").classList.add( "btn-outline-danger" );
    };
};


export class AddLotNumModal {
    itemCodeInput = document.getElementById("id_lotNumModal-item_code");
    itemDescriptionInput = document.getElementById("id_lotNumModal-item_description");
    quantityInput = document.getElementById("id_lotNumModal-lot_quantity");
    lineInput = document.getElementById("id_lotNumModal-line");
    deskInput = document.getElementById("id_lotNumModal-desk");
    addLotNumButton = document.getElementById("addLotNumButton");
    runDateInput = document.getElementById("id_lotNumModal-run_date");
    $addLotNumButton = $("#addLotNumButton");
    
    setAddLotModalInputs(e) {
        $('#id_lotNumModal-item_code').val(e.currentTarget.getAttribute('data-itemcode'));
        $('#id_lotNumModal-item_description').val(e.currentTarget.getAttribute('data-desc'));
        $('#id_lotNumModal-lot_quantity').val(Math.round(parseFloat(e.currentTarget.getAttribute('data-lotqty'))));
        $('#id_lotNumModal-line').val(e.currentTarget.getAttribute('data-line'));
        $('#id_lotNumModal-desk').val(e.currentTarget.getAttribute('data-desk'));
        $("#id_lotNumModal-run_date").val(e.currentTarget.getAttribute('data-rundate'));
    };

    autoFillSetup(){
        try {
            $( function() {
                getAllItemCodeAndDesc();
        
                // ===============  Item Number Search  ==============
                $('#id_lotNumModal-item_code').autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 2,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(availableItemCodes, request.term);
                        response(results.slice(0,10));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemCode");
                        let itemCode;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemCode = $itemCodeInput.val();
                        } else {
                            itemCode = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemData(itemCode, "itemCode");
                        setFields(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemCode = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemData(itemCode, "itemCode");
                        setFields(itemData);
                    },
                });
        
                //   ===============  Description Search  ===============
                $itemDescriptionInput.autocomplete({ // Sets up a dropdown for the part number field 
                    minLength: 3,
                    autoFocus: true,
                    source: function (request, response) {
                        let results = $.ui.autocomplete.filter(availableItemDescriptions, request.term);
                        response(results.slice(0,300));
                    },
                    change: function(event, ui) { // Autofill desc when change event happens to the item_code field 
                        indicateLoading("itemDescription");
                        let itemDesc;
                        if (ui.item==null) { // in case the user clicks outside the input instead of using dropdown
                            itemDesc = $itemDescriptionInput.val();
                        } else {
                            itemDesc = ui.item.label.toUpperCase();
                        }
                        let itemData = getItemData(itemDesc, "itemDescription");
                        setFields(itemData);
                    },
                    select: function(event , ui) { // Autofill desc when select event happens to the item_code field 
                        indicateLoading();
                        let itemDesc = ui.item.label.toUpperCase(); // Make sure the item_code field is uppercase
                        let itemData = getItemData(itemDesc, "itemDescription");
                        setFields(itemData);
                    },
                });
            });
        } catch (pnError) {
            console.log(pnError)
        };
        $itemCodeInput.focus(function(){
            $animation.hide();
        }); 
        $itemDescriptionInput.focus(function(){
            $animation.hide();
        });
    };

};