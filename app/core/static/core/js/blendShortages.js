// const $itemCodeInput = $('#id_item_code');
// const $itemDescriptionInput = $('#id_item_description');
// const $quantityInput = $('#id_lot_quantity');
const $lotNumCells = $('.lotNumCell');



$(document).ready(function(){
    $lotNumCells.each(function(){
        $(this).click(function(event) {
            $('#id_newLotModal-item_code').val(event.target.getAttribute('data-itemcode'));
            $('#id_newLotModal-item_description').val(event.target.getAttribute('data-desc'));
            $('#id_newLotModal-lot_quantity').val(
                Math.round(parseFloat(event.target.getAttribute('data-threewkqty')))
                );
        });
    });
});