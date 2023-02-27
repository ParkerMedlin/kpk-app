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
