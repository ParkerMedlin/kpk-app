import { CountCollectionLinksPage } from '../objects/pageObjects.js'
import { CountCollectionWebSocket } from '../objects/webSocketObjects.js'
import { AddAutomatedBlendcountButton, AddAutomatedBlendcomponentcountButton } from '../objects/buttonObjects.js'

$(document).ready(function(){
    const thisCountCollectionWebSocket = new CountCollectionWebSocket()
    const thisCountListPage = new CountCollectionLinksPage(thisCountCollectionWebSocket);
    const thisAddAutomatedBlendcountButton = new AddAutomatedBlendcountButton(document.getElementById('add-automated-blendcount-button'));
    const thisAddAutomatedBlendcomponentcountButton = new AddAutomatedBlendcomponentcountButton(document.getElementById('add-automated-blendcomponentcount-button'));
});