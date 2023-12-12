import { GHSLookupForm } from '../objects/lookupFormObjects.js';

$(document).ready(function(){
    const createNewGHSLookupForm  = new GHSLookupForm($("#id_item_code"), $("#id_item_description"), "blend");
    const searchExistingGHSLookupForm  = new GHSLookupForm($("#id_item_code_0"), $("#id_item_description_0"), "ghs-blends");
});