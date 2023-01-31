const $itemCodeInput = $('#id_component_item_code');
const $itemDescInput = $('#id_item_description');
const $quantityInput = $('#id_lot_quantity');
const $lotNumButtons = $('.lotNumButton');
const $lotNumCells = $('.lotNumCell');



$(document).ready(function(){
    $lotNumCells.each(function(){
        $(this).click(function(event) {
            $itemCodeInput.val(event.target.getAttribute('data-partnum'));
            $itemDescInput.val(event.target.getAttribute('data-desc'));
            $quantityInput.val(
                Math.round(parseFloat(event.target.getAttribute('data-threewkqty')))
                );
        });
    });
});