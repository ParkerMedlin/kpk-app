import { BlendInstructionEditorPage } from '../objects/pageObjects.js'
import { getURLParameter } from '../requestFunctions/requestFunctions.js'

$(document).ready(function() {
    const thisBlendInstructionEditorPage = new BlendInstructionEditorPage();
    const deleteButtons = document.querySelectorAll('.deleteBtn');

    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e){
            document.getElementById('deleteDialog').showModal();
            let confirmDeleteButton = document.getElementById('confirmDelete');
            let objectId = e.currentTarget.getAttribute('data-item-id');
            let encodedItemCode = getURLParameter('itemCode')
            confirmDeleteButton.setAttribute('href', `/core/delete-blend-instruction?objectID=${objectId}&encodedItemCode=${encodedItemCode}`)
        })
    })
});