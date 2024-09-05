import { AddCountListItemModal } from '../objects/modalObjects.js'
import { CountListPage } from '../objects/pageObjects.js'
// import { DateChangeButton } from '../objects/buttonObjects.js'
import { CountListWebSocket, CountCollectionWebSocket } from '../objects/webSocketObjects.js'
import { getURLParameter } from '../requestFunctions/requestFunctions.js'

$(document).ready(function(){
    const thisAddCountListItemModal = new AddCountListItemModal();
    const listId = getURLParameter('listId');
    const thisCountListWebSocket = new CountListWebSocket(listId);
    // const thisCountCollectionWebSocket = new CountCollectionWebSocket();
    const thisCountListPage = new CountListPage(thisCountListWebSocket);
    // const thisDateChangeButton = new DateChangeButton();
});