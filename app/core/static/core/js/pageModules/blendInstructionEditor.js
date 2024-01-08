import { BlendInstructionEditorPage } from '../objects/pageObjects.js'
import { getURLParameter } from '../requestFunctions/requestFunctions.js'
import { updateBlendInstructionsOrder } from '../requestFunctions/updateFunctions.js'

$(document).ready(function() {
    const thisBlendInstructionEditorPage = new BlendInstructionEditorPage();
    const deleteButtons = document.querySelectorAll('.deleteBtn');

    // Set the value of each cell in column 1 and then update the db.
    // Doing this on page load in case we delete a step.
    $(this).find("tr").each(function(index) {
        if (index > 0 && !($(this).attr('id') === 'addNewInstructionRow')) {
            $(this).find("td").eq(0).find('input').val(index); // Set Order column cell = index value
        }
    });
    
    updateBlendInstructionsOrder();

    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e){
            e.preventDefault();
            document.getElementById('deleteDialog').showModal();
            let confirmDeleteButton = document.getElementById('confirmDelete');
            let objectId = e.currentTarget.getAttribute('data-item-id');
            let encodedItemCode = getURLParameter('itemCode')
            confirmDeleteButton.setAttribute('href', `/core/delete-blend-instruction?objectID=${objectId}&encodedItemCode=${encodedItemCode}`)
        });
    });
});