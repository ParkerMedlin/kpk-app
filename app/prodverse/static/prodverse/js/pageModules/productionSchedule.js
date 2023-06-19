import { ProductionSchedulePage } from '../objects/pageObjects.js'
import { IssueSheetDropdown } from '../objects/buttonObjects.js'

$(document).ready(function(){
    const thisProductionSchedulePage = new ProductionSchedulePage();
    const thisIssueSheetDropdown = new IssueSheetDropdown();
});