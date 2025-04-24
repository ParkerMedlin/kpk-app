import { AddCountListItemModal } from '../objects/modalObjects.js'
import { CountListPage } from '../objects/pageObjects.js'
// import { DateChangeButton } from '../objects/buttonObjects.js'
import { CountListWebSocket, CountCollectionWebSocket } from '../objects/webSocketObjects.js'
import { getURLParameter } from '../requestFunctions/requestFunctions.js'
// import { MultiContainerZebraPrintButton } from '../objects/buttonObjects.js'

$(document).ready(function(){
    const listId = getURLParameter('listId');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const thisCountListWebSocket = new CountListWebSocket(`${protocol}//${window.location.host}/ws/count_list/${listId}/`);
    const thisCountListPage = new CountListPage(thisCountListWebSocket);
    const thisAddCountListItemModal = new AddCountListItemModal(thisCountListWebSocket);
    const thisCountCollectionWebSocket = new CountCollectionWebSocket();

    // Store the WebSocket instance globally
    window.thisCountListWebSocket = thisCountListWebSocket;
    
    // Log ContainerManager initialization
    console.log("💫 CountListPage initialized with ContainerManager:", !!window.countListPage && !!window.countListPage.containerManager);

    // When a modal is about to be shown, if on a small screen, detach it and append to body for proper stacking
    $('.modal').on('show.bs.modal', function(){
        if (window.innerWidth < 600) {
            $(this).appendTo('body');
            console.log('[VC] Moved modal to body for proper stacking on mobile.');
        }
    });

    // const multiContainerPrintButtons = document.querySelectorAll('.multi-container-print-button');
    // multiContainerPrintButtons.forEach(button => {
    //     const countRecordId = button.getAttribute('data-countrecord-id');
    //     new MultiContainerZebraPrintButton(button, countRecordId);
    // });

});