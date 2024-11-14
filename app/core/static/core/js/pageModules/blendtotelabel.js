import { ZebraPrintButton } from '../objects/buttonObjects.js';
import { BlendToteLabelLookupForm } from '../objects/lookupFormObjects.js'

$(document).ready(function(){
    const thisBlendToteLabelLookupForm = new BlendToteLabelLookupForm();
    const thisZebraPrintButton = new ZebraPrintButton(document.getElementById("blendLabelPrintButton"), false);
    $("#label-lot-number-dropdown").change(function(e) {
        let selectedOptionValue = this.value;
        $("#blend-label-lot-number").text(selectedOptionValue);
    });
});


