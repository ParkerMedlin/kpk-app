$(document).ready(function(){
    $('input[type="number"]').each(function(){
        $(this).attr("value", Math.round($(this).attr("value")));
    });
});

let expected_quantity;
let counted_quantity;
let variance;

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
    $('input[type=hidden]').each(function() {
        $(this).parent('td').attr('style', "display:none;");
    });

    let fullEncodedList = $("#encodedListDiv").attr("data-encoded-list");
    let thisRowIdEncoded;
    let thisRowId;
    

    $('.discardButtonCell').each(function(){
        thisRowID = $(this).prev().children().first().attr("value");
        thisRowIdEncoded = btoa(thisRowID)
        $(this).children().first().attr("href", `/core/delete_countrecord/countlist/${thisRowIdEncoded}/${fullEncodedList}`)
    });

    
    $('input').each(function(){
        let thisID = $(this).attr('name')
        if (!(thisID.includes('counted_quantity'))) {
            $(this).attr('readonly', 'True');
        };
    });
});

