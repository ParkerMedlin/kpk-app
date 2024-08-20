import { AddCountListItemModal } from '../objects/modalObjects.js'
import { CountListPage } from '../objects/pageObjects.js'
import { DateChangeButton } from '../objects/buttonObjects.js'

$(document).ready(function(){
    const thisAddCountListItemModal = new AddCountListItemModal();
    const thisCountListPage = new CountListPage();
    const thisDateChangeButton = new DateChangeButton();
});