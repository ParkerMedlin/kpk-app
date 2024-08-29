import { AddCountListItemModal } from '../objects/modalObjects.js'
import { CountListPage } from '../objects/pageObjects.js'
import { DateChangeButton } from '../objects/buttonObjects.js'
import { CountListWebSocket } from '../objects/webSocketObjects.js'

$(document).ready(function(){
    const thisAddCountListItemModal = new AddCountListItemModal();
    const thisCountListWebSocket = new CountListWebSocket();
    const thisCountListPage = new CountListPage(thisCountListWebSocket);
    const thisDateChangeButton = new DateChangeButton();
});