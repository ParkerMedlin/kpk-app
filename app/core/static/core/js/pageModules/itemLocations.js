import { EditItemLocationButton, AddMissingItemLocationsButton } from '../objects/buttonObjects.js';
import { FilterForm } from '../objects/lookupFormObjects.js';

$(document).ready(function() {
    const editItemLocationButtons = document.querySelectorAll('.editLocationButton');
    const thisAddMissingItemLocationsButton = new AddMissingItemLocationsButton(document.querySelector('#addMissingItemLocationsBtn'));

    // Initialize filter functionality for the item locations table
    const thisFilterForm = new FilterForm();
    editItemLocationButtons.forEach(button => {
        let thisEditItemLocationButton = new EditItemLocationButton(button);
    })

});