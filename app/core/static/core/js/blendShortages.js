// const $itemCodeInput = $('#id_item_code');
// const $itemDescriptionInput = $('#id_item_description');
// const $quantityInput = $('#id_lot_quantity');
const $lotNumCells = $('.lotNumCell');



$(document).ready(function(){
    $lotNumCells.each(function(){
        $(this).click(function(event) {
            $('#id_lotNumModal-item_code').val(event.target.getAttribute('data-itemcode'));
            $('#id_lotNumModal-item_description').val(event.target.getAttribute('data-desc'));
            $('#id_lotNumModal-lot_quantity').val(
                Math.round(parseFloat(event.target.getAttribute('data-threewkqty')))
                );
        });
    });
});