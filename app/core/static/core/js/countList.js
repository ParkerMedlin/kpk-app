let expected_quantity;
let counted_quantity;
let variance;
const $countedQuantityInputs = $('input[id*="counted_quantity"]')
const $saveCountsButton = $('#saveCountsButton')

let missedaCount = true;





$('input[id*=counted_quantity]').blur(function(){
    expected_quantity = $(this).parent().prev('td').children().first().val();
    console.log("expected qty: " + expected_quantity);
    counted_quantity = $(this).val();
    console.log("counted qty: " + counted_quantity);
    variance = counted_quantity - expected_quantity;
    console.log("variance: " + variance);
    $(this).parent().next('td').next('td').children().attr('value', variance);
});

$(document).ready(function(){
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

    $countedQuantityInputs.each(function() {
        $(this).attr('tabindex', '0');
        $(this).on('focus', function() {
            $(this).addClass('entered')
            if ($(this).hasClass('missingCount')) {
                $(this).removeClass('missingCount');
            }
        });

    });

    $saveCountsButton.on('click', function(e){
        missedaCount = false;
        $countedQuantityInputs.each(function(e) {
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
        }
        
    });

    $('table').keypress(
        function(event){
          if (event.which == '13') {
            event.preventDefault();
          }
      });

    let fullEncodedList = $("#encodedListDiv").attr("data-encoded-list");
    let thisRowIdEncoded;
    let thisRowID;

    $('.discardButtonCell').each(function(){
        thisRowID = $(this).prev().children().first().attr("value");
        thisRowIdEncoded = btoa(thisRowID)
        $(this).children().first().attr("href", `/core/delete_countrecord/countlist/${thisRowIdEncoded}/${fullEncodedList}`)
    });

    
    
});

