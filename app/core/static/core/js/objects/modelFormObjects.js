export class CountListForm {
    constructor() {
        try {
            this.setupVarianceCalculation();
            this.setupDiscardButtons();
            this.setupFieldattributes();
        console.log("Instance of class CountListForm created.");
        } catch(err) {
            console.error(err.message);
        };
    };

    setupVarianceCalculation(){
        $('input[id*=counted_quantity]').blur(function(){
            let expected_quantity = $(this).parent().prev('td').children().first().val();
            console.log("expected qty: " + expected_quantity);
            let counted_quantity = $(this).val();
            console.log("counted qty: " + counted_quantity);
            let variance = counted_quantity - expected_quantity;
            // console.log("variance: " + variance);
            $(this).parent().next('td').next('td').children().attr('value', variance.toFixed(4));
        });
    };

    setupDiscardButtons() {
        let fullEncodedList = $("#encodedListDiv").attr("encoded-list");
        let thisRowIdEncoded;
        let thisRowID;
        $('.discardButtonCell').each(function(){
            thisRowID = $(this).prev().children().first().attr("value");
            thisRowIdEncoded = btoa(thisRowID)
            let urlParameters = new URLSearchParams(window.location.search);
            let recordType = urlParameters.get('recordType');
            $(this).children().first().attr("href", `/core/delete-count-record/?redirectPage=count-records&listToDelete=${thisRowIdEncoded}&fullList=${fullEncodedList}&recordType=${recordType}`)
        });  
    };

    setupFieldattributes() {
        let missedaCount = true;
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
        });
        $('input').each(function() {
            $(this).attr('readonly', true)
        });
        $('input[id*="counted_quantity"]').each(function() {
            $(this).attr('tabindex', '0');
            $(this).removeAttr('readonly');
            $(this).on('focus', function() {
                $(this).addClass('entered')
                if ($(this).hasClass('missingCount')) {
                    $(this).removeClass('missingCount');
                };
            });
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
        // Prevent the enter key from submitting the form
        $('table').keypress(function(event){
            if (event.which == '13') {
                event.preventDefault();
            };
        });
    };

};