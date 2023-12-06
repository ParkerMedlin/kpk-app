import { GHSLotNumberButton } from '../objects/buttonObjects.js';

$(document).ready(function(){
    const thisGHSLotNumberButton = new GHSLotNumberButton();
    let urlParameters = new URLSearchParams(window.location.search);
    let lotNumber = urlParameters.get('lotNumber');
    console.log(lotNumber)
    if (lotNumber) {
        document.querySelectorAll('.lotNumberContainer').forEach(inputContainer => {
            inputContainer.style.display = "block";
            let inputField = inputContainer.querySelector('input');
            inputField.value = lotNumber;
        });
    };
});