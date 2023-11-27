import { DeleteFoamFactorModal, AddFoamFactorModal, EditFoamFactorModal } from '../objects/modalObjects.js';

$(document).ready(function(){

    const thisDeleteFoamFactorModal = new DeleteFoamFactorModal();
    const thisEditFoamFactorModal = new EditFoamFactorModal();
    const thisAddFoamFactorModal = new AddFoamFactorModal();

    const deleteButtons = document.querySelectorAll('.deleteBtn');
    deleteButtons.forEach(delButton => {
        delButton.addEventListener('click', thisDeleteFoamFactorModal.setModalButtons);
    });

});