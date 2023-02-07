import { getLocation, getAllBOMFields } from '../requestFunctions/requestFunctions.js'
import { indicateLoading } from '../uiFunctions/uiFunctions.js'


export class LocationLookupForm {
    
    BOMFields = getAllBOMFields('chem-dye-frag');
    itemCodeInput = $("#id_item_code");
    itemDescriptionInput = $("#id_item_description");
    itemLocation = $('#id_location');
    itemQty = $('#id_quantity');
    animation = $(".animation");

    setFields(locationData){
        $("#id_item_code").val(locationData.item_code);
        $("#id_item_description").val(locationData.item_description);
        $('#id_location').text(locationData.general_location + ", " + locationData.specific_location);
        $('#id_quantity').text(locationData.qtyonhand + " " + locationData.standard_uom + " on hand.");
        };

    setUpDropDown() {
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
    }

}