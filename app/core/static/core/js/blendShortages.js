const $partNumberInput = $('#id_item_code');
const $partDescInput = $('#id_item_description');
const $quantityInput = $('#id_lot_quantity');
const $lotNumButtons = $('.lotNumButton');
const $lotNumCells = $('.lotNumCell');



$(document).ready(function(){
    $lotNumCells.each(function(){
        $(this).click(function(event) {
            $partNumberInput.val(event.target.getAttribute('data-partnum'));
            $partDescInput.val(event.target.getAttribute('data-desc'));
            $quantityInput.val(
                Math.round(parseFloat(event.target.getAttribute('data-threewkqty')))
                );
        });
    });
});