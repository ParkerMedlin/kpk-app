import { GHSLookupForm } from '../objects/lookupFormObjects.js';

$(document).ready(function(){
    const thisGHSLookupForm  = new GHSLookupForm($("#id_item_code"), $("#id_item_description"), "blend");
    const thatGHSLookupForm  = new GHSLookupForm($("#id_item_code_0"), $("#id_item_description_0"), "ghs-blends");
});