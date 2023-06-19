import { getMaxProducibleQuantity } from '../requestFunctions/requestFunctions.js'

export class CountListPage {
    constructor(countListType) {
        try {
            this.setupVarianceCalculation();
            this.setupDiscardButtons();
            this.setupFieldattributes(countListType);
            console.log("Instance of class CountListPage created.");
        } catch(err) {
            console.error(err.message);
        };
    }

    setupVarianceCalculation(){
        $('input[id*=counted_quantity]').blur(function(){
            let expected_quantity = $(this).parent().prev('td').children().first().val();
            let counted_quantity = $(this).val();
            let variance = counted_quantity - expected_quantity;
            let formNumber = $(this).prop('name').replace('-counted_quantity', '');
            console.log(formNumber);
            $(this).parent().next('td').next('td').children().prop('value', variance.toFixed(4));
            $(this).parent().next('td').next('td').next('td').children().prop( "checked", true );
            $(this).addClass('entered')
                if ($(this).hasClass('missingCount')) {
                    $(this).removeClass('missingCount');
                };
        });
    };

    setupDiscardButtons() {
        let fullEncodedList = $("#encodedListDiv").attr("encoded-list");
        let thisRowIdEncoded;
        let thisRowID;
        $('.discardButtonCell').each(function(){
            thisRowID = $(this).prev().children().first().attr("value");
            thisRowIdEncoded = btoa(thisRowID)
            $(this).children().first().attr("href", `/core/delete-count-record/count-list/${thisRowIdEncoded}/${fullEncodedList}`)
        });  
    };

    setupFieldattributes() {
        let missedaCount = true;
        $('.tbl-cell-counted_date, .tbl-cell-variance, .tbl-cell-counted, .tbl-cell-count_type').addClass('noPrint');
        $('input[type="number"]').each(function(){
            $(this).attr("value", parseFloat(($(this).attr("value"))).toFixed(4));
        });
        $('input[name*="counted_quantity"]').each(function(){
            $(this).attr("value", Math.round($(this).attr("value")));
        });
        $('input[type=hidden]').each(function() {
            $(this).parent('td').attr('style', "display:none;");
        });
        $('input').each(function() {
            $(this).attr('tabindex', '-1');
            $(this).attr('readonly', true)
        });
        $('.discardButton').each(function() {
            $(this).attr('tabindex', '-1');
        });
        $('input[id*="counted_quantity"]').each(function() {
            $(this).attr('tabindex', '0');
            $(this).removeAttr('readonly');
            //$(this).on('focus', function() {
            //});
        });
        $('input[id*="counted_date"]').each(function() {
            $(this).removeAttr('readonly');
        });
        $('#id_countListModal_item_code').removeAttr('readonly');
        $('#id_countListModal_item_description').removeAttr('readonly');
        
        $('#saveCountsButton').on('click', function(e){
            missedaCount = false;
            $('input[id*="counted_quantity"]').each(function(e) {
                if (!($(this).hasClass('entered'))) {
                    $(this).addClass('missingCount');
                    missedaCount = true;
                }
                $(this).on('focus', function() {
                    $(this).addClass('entered')
                });
            });   
            if (missedaCount) {
                e.preventDefault();
                alert("Please fill in the missing counts.");
            };
        });

        $('input[id*="-item_description"]').each(function(){
            let thisFormNumber = $(this).attr("id").slice(3,10);
            if (thisFormNumber.slice(6,7) == "-"){
                thisFormNumber = thisFormNumber.slice(0,6);
            }
            if ($(this).val().includes("BLEND")) {
                $(`#id_${thisFormNumber}-count_type`).val("blend");
            } else {$(`#id_${thisFormNumber}-count_type`).val("component");

            }
            
        })

        // Prevent the enter key from submitting the form
        $('table').keypress(function(event){
            if (event.which == '13') {
                event.preventDefault();
            };
        });
        
    }
};

export class MaxProducibleQuantityPage {
    constructor() {
        try {
            const urlParameters = new URLSearchParams(window.location.search);
            const itemCode = atob(urlParameters.get('itemCode'));
            const itemData = getMaxProducibleQuantity(itemCode, "NoComponentItemFilter", "itemCode");
            this.setMaxProducibleQuantityDiv(itemData)
            console.log("Instance of class MaxBlendCapacityForm created.");
        } catch(err) {
            console.error(err.message);
        }
    };

    setMaxProducibleQuantityDiv(itemData){
        console.log(itemData)
        $("#itemCodeAndDescription").text(`${itemData.item_code} ${itemData.item_description}:`);
        $("#max_producible_quantity").text(`${itemData.max_producible_quantity} gallons`);
        $("#max_producible_quantity").css('font-weight', 'bold');
        $("#limiting_factor").text(`${itemData.limiting_factor_item_code}: ${itemData.limiting_factor_item_description}`);
        $("#limiting_factor_onhand").text(
            `${Math.round(itemData.limiting_factor_quantity_onhand, 0)}
            ${itemData.limiting_factor_UOM} on hand now --
            ${Math.round(itemData.limiting_factor_OH_minus_other_orders)}  ${itemData.limiting_factor_UOM} available after all other usage is taken into account.`
            );
        $("#next_shipment").text(`${itemData.next_shipment_date}`);
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
        $("#blendCapacityContainer").show();
    }

}

