import { CountCollectionLinksPage } from '../objects/pageObjects.js'
import { CountCollectionWebSocket } from '../objects/webSocketObjects.js'

$(document).ready(function(){
    const thisCountCollectionWebSocket = new CountCollectionWebSocket()
    const thisCountListPage = new CountCollectionLinksPage(thisCountCollectionWebSocket);
});