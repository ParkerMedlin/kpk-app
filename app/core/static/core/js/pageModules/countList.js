import { AddCountListItemModal } from '../objects/modalObjects.js';
import { CountListPage } from '../objects/pageObjects.js';
import { CountListWebSocket } from '../websockets/index.js';
import { getURLParameter } from '../requestFunctions/requestFunctions.js';

$(document).ready(function(){
    const listId = getURLParameter('listId');
    const thisCountListWebSocket = new CountListWebSocket(listId);
    const thisCountListPage = new CountListPage(thisCountListWebSocket);
    const thisAddCountListItemModal = new AddCountListItemModal(thisCountListWebSocket);

    window.thisCountListWebSocket = thisCountListWebSocket;

    $('.modal').on('show.bs.modal', function(){
        if (window.innerWidth < 600) {
            $(this).appendTo('body');
        }
    });
});
