import { ZebraPrintButton } from '../objects/buttonObjects.js';
import { PartialContainerLabelPage } from '../objects/pageObjects.js'
import { BlendComponentLabelInfoLookupForm } from '../objects/lookupFormObjects.js'

$(document).ready(function(){
    const thisZebraPrintButton = new ZebraPrintButton(document.getElementById("blendLabelPrintButton"));
    const thisPartialContainerLabelPage = new PartialContainerLabelPage();
    const thisBlendComponentLabelInfoLookupForm = new BlendComponentLabelInfoLookupForm();
});