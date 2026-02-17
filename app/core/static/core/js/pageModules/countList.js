import { AddCountListItemModal } from '../objects/modalObjects.js';
import { CountListPage } from '../objects/pageObjects.js';
// import { DateChangeButton } from '../objects/buttonObjects.js'
import { CountListWebSocket, CountCollectionWebSocket } from '../websockets/index.js';
import { getURLParameter } from '../requestFunctions/requestFunctions.js';
// import { MultiContainerZebraPrintButton } from '../objects/buttonObjects.js'

let countCollectionArchivedBannerShown = false;

function ensureArchivedBanner() {
    let bannerEl = document.getElementById('archivedBanner');
    if (bannerEl) {
        return bannerEl;
    }

    bannerEl = document.createElement('div');
    bannerEl.id = 'archivedBanner';
    bannerEl.className = 'alert alert-warning alert-dismissible fade show';
    bannerEl.setAttribute('role', 'alert');
    bannerEl.textContent = 'This count list has been archived.';

    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    closeButton.setAttribute('aria-label', 'Close');
    bannerEl.appendChild(closeButton);

    const headerElement = document.getElementById('countListNameHeader');
    const headerContainer = headerElement ? headerElement.closest('div') : null;
    if (headerContainer && headerContainer.parentNode) {
        headerContainer.parentNode.insertBefore(bannerEl, headerContainer.nextSibling);
    } else {
        document.body.prepend(bannerEl);
    }

    return bannerEl;
}

function showArchivedBanner() {
    const bannerEl = ensureArchivedBanner();
    if (!bannerEl) {
        return;
    }
    bannerEl.classList.add('show');
    bannerEl.style.display = '';
}

$(document).ready(function(){
    const listId = getURLParameter('listId');
    const normalizedListId = listId !== undefined && listId !== null ? String(listId) : null;
    const thisCountListWebSocket = new CountListWebSocket(listId);
    const thisCountListPage = new CountListPage(thisCountListWebSocket);
    const thisAddCountListItemModal = new AddCountListItemModal(thisCountListWebSocket);
    const handleCollectionHidden = (payload) => {
        if (!normalizedListId) {
            return;
        }
        const hiddenId = payload && payload.collection_id !== undefined && payload.collection_id !== null
            ? String(payload.collection_id)
            : null;
        if (!hiddenId || hiddenId !== normalizedListId) {
            return;
        }
        if (countCollectionArchivedBannerShown) {
            return;
        }
        countCollectionArchivedBannerShown = true;
        showArchivedBanner();
    };

    const thisCountCollectionWebSocket = new CountCollectionWebSocket({
        onCollectionHidden: handleCollectionHidden,
        onCollectionDeleted: handleCollectionHidden,
    });

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
