import { CreateCountListButton } from '../objects/buttonObjects.js'
import { FilterForm, DropDownFilter } from '../objects/lookupFormObjects.js'
import { ShiftSelectCheckBoxes, SelectAllCheckBox } from '../objects/pageUtilities.js'

$(document).ready(function() {
    const thisCreateCountListButton = new CreateCountListButton();
    const thisFilterForm = new FilterForm();
    const thisDropDownFilter = new DropDownFilter();
    const thisShiftSelectCheckBoxes = new ShiftSelectCheckBoxes();
    //const thisSelectAllCheckBox = new SelectAllCheckBox();
        //this^ must be modified to include only filtered items before it will be usable
});