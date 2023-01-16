const $partNumberInput = $('#id_part_number');
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
            thisQuantity = Math.round(parseFloat(event.target.getAttribute('data-threewkqty')));
            if (thisQuantity>5100) {
                thisQuantity=5100;
            } else if (thisQuantity==5040) {
                thisQuantity=5100;
            }
            $quantityInput.val(thisQuantity);
            thisLine = event.target.getAttribute('data-line')
            $lineInput.val();
            $runDateInput.val(event.target.getAttribute('data-rundate'));
            $deskInput.val(event.target.currentTarget.getAttribute('data-desk'));
        });
    });
});