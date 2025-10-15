import { CountCollectionLinksPage } from '../objects/pageObjects.js';
import { CountCollectionWebSocket } from '../objects/webSocketObjects.js';
import {
    AddAutomatedBlendcountButton,
    AddAutomatedBlendcomponentcountButton,
} from '../objects/buttonObjects.js';

$(document).ready(function () {
    const countCollectionWebSocket = new CountCollectionWebSocket();
    const countListPage = new CountCollectionLinksPage(countCollectionWebSocket);

    const addBlendCountButtonEl = document.getElementById('add-automated-blendcount-button');
    if (addBlendCountButtonEl) {
        new AddAutomatedBlendcountButton(addBlendCountButtonEl);
    }

    const addBlendComponentButtonEl = document.getElementById(
        'add-automated-blendcomponentcount-button',
    );
    if (addBlendComponentButtonEl) {
        new AddAutomatedBlendcomponentcountButton(addBlendComponentButtonEl);
    }
});
