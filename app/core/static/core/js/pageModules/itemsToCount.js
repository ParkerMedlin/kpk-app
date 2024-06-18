import { CreateCountListButton, BlendComponentFilterButton } from '../objects/buttonObjects.js'
import { FilterForm, DropDownFilter } from '../objects/lookupFormObjects.js'
import { ShiftSelectCheckBoxes, SelectAllCheckBox } from '../objects/pageUtilities.js'
import { ItemsToCountPage } from '../objects/pageObjects.js'

$(document).ready(function() {
    const thisCreateCountListButton = new CreateCountListButton();
    const thisFilterForm = new FilterForm();
    const thisDropDownFilter = new DropDownFilter();
    const thisShiftSelectCheckBoxes = new ShiftSelectCheckBoxes();
    const thisItemsToCountPage = new ItemsToCountPage();
    const thisBlendComponentFilterButton = new BlendComponentFilterButton(document.getElementById('upcomingRunsFilterCheckbox'));
    //const thisSelectAllCheckBox = new SelectAllCheckBox();
        //that^ must be modified to include only filtered items before it will be usable
});