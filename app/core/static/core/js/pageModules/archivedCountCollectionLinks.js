import { CountCollectionWebSocket } from '../objects/webSocketObjects.js';
import { confirmAction } from '../objects/confirmModal.js';

$(document).ready(function () {
    const table = document.getElementById('archivedCountCollectionLinkTable');
    const tableBody = table ? table.querySelector('tbody') : null;
    const tableContainer = table ? table.parentElement : null;

    function resolveCollectionId(payload) {
        return payload?.collection_id || payload?.id;
    }

    function formatCreatedAt(payload) {
        if (payload.created_at_display) {
            return payload.created_at_display;
        }
        if (!payload.created_at) {
            return '';
        }
        const parsed = new Date(payload.created_at);
        if (Number.isNaN(parsed.getTime())) {
            return '';
        }
        return parsed.toLocaleDateString('en-US', {
            month: '2-digit',
            day: '2-digit',
            year: 'numeric',
        });
    }

    function removeEmptyState() {
        const existing = document.getElementById('archivedCollectionEmptyState');
        if (existing) {
            existing.remove();
        }
    }

    function ensureEmptyState() {
        if (!tableContainer) {
            return;
        }
        const existing = document.getElementById('archivedCollectionEmptyState');
        if (existing) {
            return;
        }
        const message = document.createElement('p');
        message.id = 'archivedCollectionEmptyState';
        message.className = 'text-muted';
        message.textContent = 'No archived count collections.';
        tableContainer.insertAdjacentElement('afterend', message);
    }

    function buildRow(payload) {
        const row = document.createElement('tr');
        row.className = 'tableBodyRow';
        const collectionId = resolveCollectionId(payload);
        row.setAttribute('collectionlinkitemid', collectionId);

        const nameCell = document.createElement('td');
        const nameLink = document.createElement('a');
        nameLink.className = 'collectionLink';
        nameLink.href = `/core/count-list/display/?listId=${collectionId}&recordType=${payload.record_type}`;
        nameLink.textContent = payload.collection_name || '';
        nameCell.appendChild(nameLink);

        const createdCell = document.createElement('td');
        createdCell.textContent = formatCreatedAt(payload);

        const restoreCell = document.createElement('td');
        restoreCell.className = 'text-center';
        const restoreButton = document.createElement('button');
        restoreButton.className = 'btn btn-outline-success restoreCountLinkButton';
        restoreButton.setAttribute('collectionlinkitemid', collectionId);
        const restoreIcon = document.createElement('i');
        restoreIcon.className = 'fa-solid fa-rotate-left';
        restoreButton.appendChild(restoreIcon);
        restoreCell.appendChild(restoreButton);

        const deleteCell = document.createElement('td');
        deleteCell.className = 'text-center';
        const deleteButton = document.createElement('button');
        deleteButton.className = 'btn btn-outline-danger deleteCountLinkButton';
        deleteButton.setAttribute('collectionlinkitemid', collectionId);
        const deleteIcon = document.createElement('i');
        deleteIcon.className = 'fa-solid fa-trash';
        deleteButton.appendChild(deleteIcon);
        deleteCell.appendChild(deleteButton);

        row.appendChild(nameCell);
        row.appendChild(createdCell);
        row.appendChild(restoreCell);
        row.appendChild(deleteCell);
        return row;
    }

    function handleCollectionArchived(payload) {
        const collectionId = resolveCollectionId(payload);
        if (!collectionId || !tableBody) {
            return;
        }
        const existingRow = document.querySelector(`tr[collectionlinkitemid="${collectionId}"]`);
        if (existingRow) {
            return;
        }
        if (!payload.collection_name || !payload.record_type) {
            window.location.reload();
            return;
        }
        removeEmptyState();
        tableBody.appendChild(buildRow(payload));
    }

    function handleCollectionRestored(payload) {
        const collectionId = resolveCollectionId(payload);
        if (!collectionId) {
            return;
        }
        const row = document.querySelector(`tr[collectionlinkitemid="${collectionId}"]`);
        if (row) {
            row.remove();
        }
        if (tableBody && tableBody.children.length === 0) {
            ensureEmptyState();
        }
    }

    function handleCollectionDeleted(payload) {
        const collectionId = resolveCollectionId(payload);
        if (!collectionId) {
            return;
        }
        const row = document.querySelector(`tr[collectionlinkitemid="${collectionId}"]`);
        if (row) {
            row.remove();
        }
        if (tableBody && tableBody.children.length === 0) {
            ensureEmptyState();
        }
    }

    const countCollectionWebSocket = new CountCollectionWebSocket({
        onCollectionArchived: handleCollectionArchived,
        onCollectionRestored: handleCollectionRestored,
        onCollectionDeleted: handleCollectionDeleted,
    });

    $(document).on('click', '.restoreCountLinkButton', function () {
        const collectionId = $(this).attr('collectionlinkitemid');
        if (!collectionId) {
            return;
        }
        countCollectionWebSocket.restoreCollection(collectionId);
    });

    $(document).on('click', '.deleteCountLinkButton', async function () {
        const collectionId = $(this).attr('collectionlinkitemid');
        if (!collectionId) {
            return;
        }
        if (await confirmAction("Are you sure you want to permanently delete this count collection?")) {
            countCollectionWebSocket.deleteCollection(collectionId);
        }
    });
});
