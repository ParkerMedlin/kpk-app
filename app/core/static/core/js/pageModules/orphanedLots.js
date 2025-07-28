import { DeleteLotNumModal, EditLotNumModal } from '../objects/modalObjects.js';

$(document).ready(function(){
    const deleteButtons = document.querySelectorAll('.deleteBtn');
    const editLotButtons = document.querySelectorAll('.editLotButton');

    const thisDeleteLotNumModal = new DeleteLotNumModal();
    deleteButtons.forEach(delButton => {
        delButton.addEventListener('click', thisDeleteLotNumModal.setModalButtons);
    });

    const thisEditLotNumModal = new EditLotNumModal();
    editLotButtons.forEach(button => {
        let thisEditLotNumButton = new EditLotNumButton();
    })
});