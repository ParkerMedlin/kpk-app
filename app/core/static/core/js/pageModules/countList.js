import { AddCountListItemModal } from '../objects/modalObjects.js';
import { CountListPage } from '../objects/pageObjects.js';
// import { DateChangeButton } from '../objects/buttonObjects.js'
import { CountListWebSocket, CountCollectionWebSocket } from '../websockets/index.js';
import { getURLParameter } from '../requestFunctions/requestFunctions.js';
// import { MultiContainerZebraPrintButton } from '../objects/buttonObjects.js'

const COUNT_COLLECTION_LINKS_URL = '/core/display-count-collection-links/';
let countCollectionDeletionModalShown = false;

function ensureCountCollectionDeletedModal() {
    let modalEl = document.getElementById('countCollectionLinkDeletedModal');
    if (modalEl) {
        return modalEl;
    }

    modalEl = document.createElement('div');
    modalEl.id = 'countCollectionLinkDeletedModal';
    modalEl.className = 'modal fade count-collection-deleted-modal';
    modalEl.tabIndex = -1;
    modalEl.setAttribute('aria-labelledby', 'countCollectionLinkDeletedModalLabel');
    modalEl.setAttribute('aria-hidden', 'true');

    modalEl.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header bg-warning text-dark">
                    <h5 class="modal-title" id="countCollectionLinkDeletedModalLabel">Count List Unavailable</h5>
                </div>
                <div class="modal-body">
                    <p class="mb-3" data-role="deletion-message"></p>
                    <p class="small text-muted mb-0" data-role="deletion-timestamp"></p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-primary" data-role="redirect">Go to Count Collection Links</button>
                    <button type="button" class="btn btn-outline-secondary" data-role="dismiss">Stay on Page</button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modalEl);

    const dismissButton = modalEl.querySelector('[data-role="dismiss"]');
    if (dismissButton) {
        dismissButton.addEventListener('click', () => {
            if (window.bootstrap && window.bootstrap.Modal) {
                const modalInstance = window.bootstrap.Modal.getInstance(modalEl) || window.bootstrap.Modal.getOrCreateInstance(modalEl);
                if (modalInstance) {
                    modalInstance.hide();
                }
            } else if (typeof $ === 'function' && typeof $(modalEl).modal === 'function') {
                $(modalEl).modal('hide');
            } else {
                modalEl.classList.remove('show');
                modalEl.style.display = 'none';
            }
        });
    }

    const redirectButton = modalEl.querySelector('[data-role="redirect"]');
    if (redirectButton) {
        redirectButton.addEventListener('click', (event) => {
            event.preventDefault();
            window.location.assign(COUNT_COLLECTION_LINKS_URL);
        });
    }

    return modalEl;
}

function showCountCollectionDeletedModal({ listName, receivedAt } = {}) {
    const modalEl = ensureCountCollectionDeletedModal();
    const messageEl = modalEl.querySelector('[data-role="deletion-message"]');
    const timestampEl = modalEl.querySelector('[data-role="deletion-timestamp"]');

    const safeListName = listName && listName.trim() !== '' ? listName.trim() : null;
    const message = safeListName
        ? `The count list "${safeListName}" is no longer available because a Counts Manager deleted its Count Collection Link.`
        : 'This count list is no longer available because a Counts Manager deleted its Count Collection Link.';
    if (messageEl) {
        messageEl.textContent = message;
    }

    const timestamp = receivedAt instanceof Date ? receivedAt : new Date();
    if (timestampEl) {
        timestampEl.textContent = `Update received ${timestamp.toLocaleString()}.`;
    }

    if (window.bootstrap && window.bootstrap.Modal) {
        const modalInstance = window.bootstrap.Modal.getOrCreateInstance(modalEl, {
            backdrop: 'static',
            keyboard: false,
        });
        modalInstance.show();
    } else if (typeof $ === 'function' && typeof $(modalEl).modal === 'function') {
        $(modalEl).modal({
            backdrop: 'static',
            keyboard: false,
        });
    } else {
        modalEl.classList.add('show');
        modalEl.style.display = 'block';
    }
}

$(document).ready(function(){
    const listId = getURLParameter('listId');
    const normalizedListId = listId !== undefined && listId !== null ? String(listId) : null;
    const thisCountListWebSocket = new CountListWebSocket(listId);
    const thisCountListPage = new CountListPage(thisCountListWebSocket);
    const thisAddCountListItemModal = new AddCountListItemModal(thisCountListWebSocket);
    const thisCountCollectionWebSocket = new CountCollectionWebSocket({
        onCollectionDeleted: (payload) => {
            if (!normalizedListId) {
                return;
            }
            const deletedId = payload && payload.collection_id !== undefined && payload.collection_id !== null
                ? String(payload.collection_id)
                : null;
            if (!deletedId || deletedId !== normalizedListId) {
                return;
            }
            if (countCollectionDeletionModalShown) {
                return;
            }
            countCollectionDeletionModalShown = true;

            if (thisCountListWebSocket && typeof thisCountListWebSocket.disconnect === 'function') {
                thisCountListWebSocket.disconnect({ reason: 'count_collection_link_deleted' });
            }

            const headerElement = document.getElementById('countListNameHeader');
            const listName = headerElement ? headerElement.textContent : '';
            showCountCollectionDeletedModal({ listName });
        },
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
