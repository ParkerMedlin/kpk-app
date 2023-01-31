$(document).ready(function(){
    const $partNumberInput = $('#id_part_number');
    const $partDescInput = $('#id_description');
    const $quantityInput = $('#id_lot_quantity');
    const $lineInput = $('#id_line');
    const $deskInput = $('#id_desk');
    const $addLotNumButton = $("#addLotNumButton");
    const $runDateInput = $("#id_run_date");

    const $batchDeleteButton = $('#batchDeleteButton');
    const $confirmModalButtonLink = $("#confirmModalButtonLink");
    const $confirmModalLabel = $('#lotNumConfirmModalLabel');
    const $confirmModalBody = $('#lotNumConfirmModalBody');
    const $confirmModalButton = $('#confirmModalButton');
    const deleteButtons = document.querySelectorAll('.deleteBtn');
    const checkBoxes = document.querySelectorAll('.rowCheckBox');
    const $duplicateBtns = $(".duplicateBtn");

    const $addToScheduleLinks = $(".addToScheduleLink");
    const $deskOneAddForm = $("#deskOneFormContainer");
    const $deskTwoAddForm = $("#deskTwoFormContainer");
    const $deskOnePartNumInput = $("#id_deskone-component_item_code");
    const $deskOneDescInput = $("#id_deskone-description");
    const $deskOneLotInput =  $("#id_deskone-lot");
    const $deskOneQtyInput =  $("#id_deskone-quantity");
    const $deskOneTotesNeedInput = $("#id_deskone-totes_needed");
    const $deskOneBlendAreaInput = $("#id_deskone-blend_area");
    const $deskTwoPartNumInput = $("#id_desktwo-component_item_code");
    const $deskTwoDescInput = $("#id_desktwo-description");
    const $deskTwoLotInput =  $("#id_desktwo-lot");
    const $deskTwoQtyInput =  $("#id_desktwo-quantity");
    const $deskTwoTotesNeedInput = $("#id_desktwo-totes_needed");
    const $deskTwoBlendAreaInput = $("#id_desktwo-blend_area");

    
        function setUpScheduleModal(desk, targetElement){
            if (desk=='Desk_1'){
                $deskOneAddForm.show();
                $deskTwoAddForm.hide();
                $deskOnePartNumInput.val(targetElement.attr('data-partnum')); 
                $deskOneDescInput.val(targetElement.attr('data-desc'));
                $deskOneLotInput.val(targetElement.attr('data-lotnum'));
                $deskOneQtyInput.val(targetElement.attr('data-lotqty'));
                $deskOneTotesNeedInput.val(Math.ceil(targetElement.attr('data-lotqty')/250));
                $deskOneBlendAreaInput.val(targetElement.attr('data-blenddesk'));

            } else if (desk=='Desk_2'){
                $deskTwoAddForm.show();
                $deskOneAddForm.hide();
                $deskTwoPartNumInput.val(targetElement.attr('data-partnum')); 
                $deskTwoDescInput.val(targetElement.attr('data-desc'));
                $deskTwoLotInput.val(targetElement.attr('data-lotnum'));
                $deskTwoQtyInput.val(targetElement.attr('data-lotqty'));
                $deskTwoTotesNeedInput.val(Math.ceil(targetElement.attr('data-lotqty')/250));
                $deskTwoBlendAreaInput.val(targetElement.attr('data-blenddesk'));
            };
        };

        $addToScheduleLinks.each(function(){
            $(this).click(function(){
                let desk=$(this).attr('data-blendDesk');
                let $targetElement = $(this);
                setUpScheduleModal(desk, $targetElement);
            });
        });


        function setLotModalInputs(e) {
            $partNumberInput.val(e.currentTarget.getAttribute('data-partnum'));
            $partDescInput.val(e.currentTarget.getAttribute('data-desc'));
            $quantityInput.val(Math.round(parseFloat(e.currentTarget.getAttribute('data-lotqty'))));
            $lineInput.val(e.currentTarget.getAttribute('data-line'));
            $deskInput.val(e.currentTarget.getAttribute('data-desk'));
            $runDateInput.val(e.currentTarget.getAttribute('data-rundate'));
        };

        $duplicateBtns.each(function(){
            $(this).click(setLotModalInputs);
        });


    $addLotNumButton.click(function() {
        $partNumberInput.val("");
        $partDescInput.val("");
        $quantityInput.val("");
        $lineInput.val("");
    });

    function setDeleteModalButton(e) {
        let count_id = e.currentTarget.getAttribute("dataitemid");
        let encoded_list = btoa(JSON.stringify(count_id));
        checkBoxes.forEach(checkBox => {
            checkBox.checked = false;
        });
        $confirmModalButtonLink.attr("href", `/core/deletelotnumrecords/${encoded_list}`);
        $confirmModalLabel.text('Confirm Deletion');
        $confirmModalBody.text('Are you sure?');
        $confirmModalButton.text('Delete');
        $confirmModalButton.removeClass( "btn-primary" ).addClass( "btn-outline-danger" );
    }

    deleteButtons.forEach(delButton => {
        delButton.addEventListener('click', setDeleteModalButton);
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