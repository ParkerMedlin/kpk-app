import { CreateCountListButton, BlendComponentFilterButton } from '../objects/buttonObjects.js'
import { FilterForm, DropDownFilter } from '../objects/lookupFormObjects.js'
import { ShiftSelectCheckBoxes, SelectAllCheckBox } from '../objects/pageUtilities.js'
import { ItemsByAuditGroupPage } from '../objects/pageObjects.js'

$(document).ready(function() {
    new CreateCountListButton();
    new FilterForm();
    new DropDownFilter();
    new ShiftSelectCheckBoxes();
    new ItemsByAuditGroupPage();
    new BlendComponentFilterButton(document.getElementById('upcomingRunsFilterCheckbox'));
    new SelectAllCheckBox();
        //that^ must be modified to include only filtered items before it will be usable
});