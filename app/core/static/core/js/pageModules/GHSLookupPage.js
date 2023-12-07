import { GHSLookupForm } from '../objects/lookupFormObjects.js';

$(document).ready(function(){
    const thisGHSLookupForm  = new GHSLookupForm($("#id_item_code"), $("#id_item_description"));
    $("#id_item_code").change()
});