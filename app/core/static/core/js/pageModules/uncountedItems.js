import { initDataTableWithExport } from '../objects/tableObjects.js';

function getCsrfToken() {
    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (csrfInput && csrfInput.value) {
        return csrfInput.value;
    }
    const cookieValue = `; ${document.cookie}`;
    const parts = cookieValue.split('; csrftoken=');
    if (parts.length === 2) {
        return parts.pop().split(';').shift();
    }
    return '';
}

function getRecordTypeFromItemType(itemType) {
    if (!itemType) {
        return 'warehouse';
    }
    const normalized = itemType.toLowerCase();
    if (normalized === 'component') {
        return 'blendcomponent';
    }
    if (normalized === 'blend') {
        return 'blend';
    }
    if (normalized === 'warehouse') {
        return 'warehouse';
    }
    return 'warehouse';
}

function buildAuditGroupSelect(currentValue) {
    const template = document.getElementById('auditGroupOptionsTemplate');
    if (!template) {
        return null;
    }
    const select = template.cloneNode(true);
    select.id = '';
    select.classList.remove('d-none');
    select.classList.add('audit-group-editor');
    select.removeAttribute('aria-hidden');
    select.removeAttribute('tabindex');
    if (currentValue) {
        select.value = currentValue;
    }
    if (currentValue && select.value !== currentValue) {
        const option = document.createElement('option');
        option.value = currentValue;
        option.textContent = currentValue;
        option.selected = true;
        select.appendChild(option);
    }
    return select;
}

function setAuditGroupDisplay(cell, value) {
    const displayValue = value ? value : '--';
    cell.textContent = displayValue;
    cell.dataset.auditGroup = value || '';
}

async function saveAuditGroup(row, auditGroupValue) {
    const auditGroupId = row.dataset.auditGroupId;
    if (!auditGroupId) {
        throw new Error('Missing audit group record.');
    }
    const recordType = getRecordTypeFromItemType(row.dataset.itemType);
    const params = new URLSearchParams({
        itemID: auditGroupId,
        auditGroup: auditGroupValue || '',
        recordType: recordType,
    });

    const response = await fetch(`/core/add-item-to-new-group?${params.toString()}`, {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        },
    });

    if (!response.ok) {
        throw new Error('Unable to update audit group.');
    }
}

function setupAuditGroupEditing() {
    const table = document.getElementById('uncountedItemsTable');
    if (!table) {
        return;
    }

    table.addEventListener('click', (event) => {
        const cell = event.target.closest('td.audit-group-cell');
        if (!cell || cell.dataset.editing === 'true') {
            return;
        }

        const row = cell.closest('tr');
        if (!row) {
            return;
        }

        const currentValue = cell.dataset.auditGroup || '';
        const select = buildAuditGroupSelect(currentValue);
        if (!select) {
            return;
        }

        cell.dataset.editing = 'true';
        cell.textContent = '';
        cell.appendChild(select);
        select.focus();

        let committed = false;
        const finishEdit = async (value) => {
            if (committed) {
                return;
            }
            committed = true;

            const newValue = value || '';
            if (newValue === currentValue) {
                cell.dataset.editing = 'false';
                setAuditGroupDisplay(cell, currentValue);
                return;
            }

            select.disabled = true;
            cell.classList.add('table-warning');
            try {
                await saveAuditGroup(row, newValue);
                cell.classList.remove('table-warning');
                cell.dataset.editing = 'false';
                setAuditGroupDisplay(cell, newValue);
            } catch (error) {
                console.error(error);
                cell.classList.remove('table-warning');
                cell.dataset.editing = 'false';
                setAuditGroupDisplay(cell, currentValue);
                alert(error.message || 'Unable to update audit group.');
            }
        };

        select.addEventListener('change', () => finishEdit(select.value));
        select.addEventListener('blur', () => finishEdit(select.value));
        select.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                finishEdit(select.value);
            }
            if (e.key === 'Escape') {
                e.preventDefault();
                committed = true;
                cell.dataset.editing = 'false';
                setAuditGroupDisplay(cell, currentValue);
            }
        });
    });
}

function getSelectedItemCodes() {
    const selected = Array.from(document.querySelectorAll('.uncounted-item-checkbox:checked'));
    return selected.map((checkbox) => checkbox.value).filter(Boolean);
}

function getSelectedRecordTypes() {
    const selected = Array.from(document.querySelectorAll('.uncounted-item-checkbox:checked'));
    const recordTypes = new Set();
    selected.forEach((checkbox) => {
        const row = checkbox.closest('tr');
        if (!row) {
            return;
        }
        recordTypes.add(getRecordTypeFromItemType(row.dataset.itemType));
    });
    return recordTypes;
}

async function createCountlistFromSelection() {
    const itemCodes = getSelectedItemCodes();
    if (!itemCodes.length) {
        alert('Select at least one item to create a countlist.');
        return;
    }

    const recordTypes = getSelectedRecordTypes();
    if (recordTypes.size > 1) {
        alert('Selected items must share the same item type.');
        return;
    }

    const response = await fetch('/core/api/countlist/from-items/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({ item_codes: itemCodes }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
        const errorMessage = payload.error || 'Unable to create countlist.';
        throw new Error(errorMessage);
    }

    const recordType = payload.record_type || Array.from(recordTypes)[0] || 'warehouse';
    const listId = payload.count_list_id;
    if (!listId) {
        throw new Error('No countlist ID returned.');
    }

    const redirectUrl = `/core/count-list/display/?recordType=${encodeURIComponent(recordType)}&listId=${encodeURIComponent(listId)}`;
    window.location.assign(redirectUrl);
}

function setupCreateCountlistButton() {
    const button = document.getElementById('createCountlistButton');
    if (!button) {
        return;
    }

    button.addEventListener('click', async () => {
        button.disabled = true;
        try {
            await createCountlistFromSelection();
        } catch (error) {
            console.error(error);
            alert(error.message || 'Unable to create countlist.');
        } finally {
            button.disabled = false;
        }
    });
}

function setupCheckboxSelection() {
    const selectAll = document.getElementById('selectAllUncountedItems');
    const checkboxes = Array.from(document.querySelectorAll('.uncounted-item-checkbox'));

    if (selectAll) {
        selectAll.addEventListener('change', () => {
            const shouldCheck = selectAll.checked;
            checkboxes.forEach((checkbox) => {
                checkbox.checked = shouldCheck;
            });
        });
    }

    checkboxes.forEach((checkbox) => {
        checkbox.addEventListener('change', () => {
            if (!selectAll) {
                return;
            }
            const allChecked = checkboxes.length && checkboxes.every((item) => item.checked);
            selectAll.checked = allChecked;
        });
    });
}

$(document).ready(function () {
    initDataTableWithExport('#uncountedItemsTable', {
        order: [[1, 'asc']],
        buttons: ['copy', 'csv', 'excel', 'print'],
        columnDefs: [
            { orderable: false, targets: [0] },
        ],
    });

    setupAuditGroupEditing();
    setupCheckboxSelection();
    setupCreateCountlistButton();
});
