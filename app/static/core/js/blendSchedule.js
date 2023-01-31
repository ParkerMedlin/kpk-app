const $partNumberInput = $('#id_item_code');
const $partDescInput = $('#id_description');
const $quantityInput = $('#id_lot_quantity');
const $lineInput = $('#id_line');
const $runDateInput = $("#id_run_date");
const $deskInput = $('#id_desk');
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
            $lineInput.val(event.target.getAttribute('data-line'));
            $runDateInput.val(event.target.getAttribute('data-rundate'));
            $deskInput.val(event.target.currentTarget.getAttribute('data-desk'));
        });
    });
});