$(document).ready(function() {
    const $partNumberInput = $('#id_part_number');
    const $partDescInput = $('#id_description');
    const $quantityInput = $('#id_lot_quantity');
    const $lineInput = $('#id_line');
    
    const $batchDeleteButton = $('#batchDeleteButton');
    const $modalButtonLink = $("#modalButtonLink");
    const $modalLabel = $('#lotNumConfirmModalLabel');
    const $modalBody = $('#lotNumConfirmModalBody');
    const $modalButton = $('#modalButton');
    const deleteButtons = document.querySelectorAll('.deleteBtn');
    const checkBoxes = document.querySelectorAll('.rowCheckBox');
    const $duplicateBtns = $(".duplicateBtn");


    $(document).ready(function(){
        $duplicateBtns.each(function(){
            $(this).click(function(event) {
                $partNumberInput.val(event.target.getAttribute('data-partnum'));
                $partDescInput.val(event.target.getAttribute('data-desc'));
                $quantityInput.val(
                    Math.round(parseFloat(event.target.getAttribute('data-lotqty')))
                    );
                $lineInput.val(event.target.getAttribute('data-line'));
            });
        });
    });

    deleteButtons.forEach(delButton => {
        delButton.addEventListener('click', function setModalButton(e) {
            let count_id = e.target.getAttribute("dataitemid");
            let encoded_list = btoa(JSON.stringify(count_id));
            checkBoxes.forEach(checkBox => {
                checkBox.checked = false;
            });
            $modalButtonLink.attr("href", `/core/deletelotnumrecords/${encoded_list}`);
            $modalLabel.text('Confirm Deletion');
            $modalBody.text('Are you sure?');
            $modalButton.text('Delete');
            $modalButton.removeClass( "btn-primary" ).addClass( "btn-outline-danger" );
        });
    });

    
    checkBoxes.forEach(checkBox => {
        checkBox.addEventListener('click', function(){
            $batchDeleteButton.show();
        });
    });

    $batchDeleteButton.click(function() {
        let part_numbers = [];
        $('td input:checked').each(function() {
            part_numbers.push($(this).attr("name"));
        });
        console.log(part_numbers)
        if (part_numbers.length === 0) {
            alert("Please check at least one row to delete.")
        } else {
            let encoded_list = btoa(JSON.stringify(part_numbers));
            base_url = window.location.href.split('core')[0];
            $modalButtonLink.attr("href", `/core/deletelotnumrecords/${encoded_list}`);
            $modalLabel.text('Confirm Deletion');
            $modalButton.text('Delete');
            $modalButton.addClass("btn-outline-danger").removeClass("btn-primary");
            $modalBody.text('Are you sure?');
        }
    });


});