import { CreateCountListButton, BlendComponentFilterButton } from '../objects/buttonObjects.js'
import { initDataTableWithExport } from '../objects/tableObjects.js'
import { ShiftSelectCheckBoxes, SelectAllCheckBox } from '../objects/pageUtilities.js'

const UPDATE_ENDPOINT_BASE = '/core/api/audit-group/';
const CREATE_ENDPOINT = '/core/api/audit-group/create/';

function getCsrfToken() {
    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (csrfInput && csrfInput.value) {
        return csrfInput.value;
    }
    const value = `; ${document.cookie}`;
    const parts = value.split('; csrftoken=');
    if (parts.length === 2) {
        return parts.pop().split(';').shift();
    }
    return '';
}

function buildSelect(choices, selectedValue) {
    const select = document.createElement('select');
    select.className = 'form-select form-select-sm';
    const normalizedChoices = Array.isArray(choices) ? choices : [];
    const selected = selectedValue ?? '';
    const hasSelected = normalizedChoices.includes(selected);

    if (!normalizedChoices.includes('')) {
        const blankOption = document.createElement('option');
        blankOption.value = '';
        blankOption.textContent = '';
        if (!selected) {
            blankOption.selected = true;
        }
        select.appendChild(blankOption);
    }

    if (selected && !hasSelected) {
        const option = document.createElement('option');
        option.value = selected;
        option.textContent = selected;
        option.selected = true;
        select.appendChild(option);
    }

    normalizedChoices.forEach((choice) => {
        const option = document.createElement('option');
        option.value = choice;
        option.textContent = choice;
        if (choice === selected) {
            option.selected = true;
        }
        select.appendChild(option);
    });

    if (!selected) {
        select.value = '';
    }

    return select;
}

function getRowSnapshot(row) {
    const snapshot = {};
    const auditGroupCell = row.querySelector('[data-field="audit_group"]');
    const actionsCell = row.querySelector('[data-field="actions"]');

    snapshot.audit_group = auditGroupCell ? auditGroupCell.textContent.trim() : '';
    snapshot.actionsHtml = actionsCell ? actionsCell.innerHTML : '';

    return snapshot;
}

function renderEditButton(actionsCell) {
    actionsCell.innerHTML = '';
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-link editRowButton p-0';
    const icon = document.createElement('i');
    icon.className = 'fa fa-pencil';
    icon.setAttribute('aria-hidden', 'true');
    button.appendChild(icon);
    actionsCell.appendChild(button);
}

function renderSaveCancelButtons(actionsCell) {
    actionsCell.innerHTML = '';
    const saveButton = document.createElement('button');
    saveButton.type = 'button';
    saveButton.className = 'btn btn-sm btn-primary saveRowButton me-2';
    saveButton.textContent = 'Save';

    const cancelButton = document.createElement('button');
    cancelButton.type = 'button';
    cancelButton.className = 'btn btn-sm btn-outline-secondary cancelRowButton';
    cancelButton.textContent = 'Cancel';

    actionsCell.appendChild(saveButton);
    actionsCell.appendChild(cancelButton);
}

async function persistRow(row, payload) {
    const recordId = row.dataset.id;
    const url = recordId ? `${UPDATE_ENDPOINT_BASE}${recordId}/` : CREATE_ENDPOINT;

    const response = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify(payload),
    });

    let data;
    try {
        data = await response.json();
    } catch (error) {
        throw new Error('Unexpected response from the server.');
    }

    if (!response.ok || data.status !== 'success') {
        const message = data.error || (data.errors && JSON.stringify(data.errors)) || 'Unable to save audit group.';
        throw new Error(message);
    }

    return data;
}

$(document).ready(function() {
    new CreateCountListButton();
    new ShiftSelectCheckBoxes();
    const upcomingRunsFilter = document.getElementById('upcomingRunsFilterCheckbox');
    if (upcomingRunsFilter) new BlendComponentFilterButton(upcomingRunsFilter);
    new SelectAllCheckBox();

    const $auditGroupLinks = $('#auditGroupLinks');
    if ($auditGroupLinks.length) {
        $auditGroupLinks.on('change', () => $('#auditGroupFilterForm').submit());
    }

    const tableElement = document.getElementById('displayTable');
    const headerCells = tableElement ? tableElement.querySelectorAll('thead th') : [];
    const hasSelectColumn = headerCells.length
        ? headerCells[0].textContent.trim() === 'Add to Count List'
        : false;
    const nonSortableColumns = hasSelectColumn
        ? [0, 2, 3, 6, 9]
        : [1, 2, 5, 8];
    const itemColumnIndex = hasSelectColumn ? 1 : 0;

    const dataTable = initDataTableWithExport('#displayTable', {
        order: [[itemColumnIndex, 'asc']],
        columnDefs: nonSortableColumns.length
            ? [{ targets: nonSortableColumns, orderable: false }]
            : [],
    });

    const auditGroupChoices = window.AUDIT_GROUP_CHOICES || [];
    const rowSnapshots = new WeakMap();
    let activeRow = null;

    function exitEditMode(row, snapshot, updatedValues = null) {
        if (!row) {
            return;
        }
        const auditGroupCell = row.querySelector('[data-field="audit_group"]');
        const actionsCell = row.querySelector('[data-field="actions"]');

        if (auditGroupCell) {
            auditGroupCell.textContent = updatedValues ? updatedValues.audit_group : snapshot.audit_group;
        }
        if (actionsCell) {
            renderEditButton(actionsCell);
        }
        row.classList.remove('table-warning');
        rowSnapshots.delete(row);
        if (activeRow === row) {
            activeRow = null;
        }
        if (dataTable) {
            dataTable.row(row).invalidate('dom');
        }
    }

    function enterEditMode(row) {
        if (!row) {
            return;
        }
        if (activeRow && activeRow !== row) {
            const snapshot = rowSnapshots.get(activeRow);
            if (snapshot) {
                exitEditMode(activeRow, snapshot);
            }
        }
        if (rowSnapshots.has(row)) {
            return;
        }

        const auditGroupCell = row.querySelector('[data-field="audit_group"]');
        const actionsCell = row.querySelector('[data-field="actions"]');
        if (!auditGroupCell || !actionsCell) {
            return;
        }

        const snapshot = getRowSnapshot(row);
        rowSnapshots.set(row, snapshot);
        activeRow = row;

        const auditGroupSelect = buildSelect(auditGroupChoices, snapshot.audit_group);

        auditGroupCell.textContent = '';
        auditGroupCell.appendChild(auditGroupSelect);
        renderSaveCancelButtons(actionsCell);

        row.classList.add('table-warning');
    }

    async function handleSave(row) {
        const snapshot = rowSnapshots.get(row);
        if (!snapshot) {
            return;
        }
        const auditGroupSelect = row.querySelector('[data-field="audit_group"] select');
        if (!auditGroupSelect) {
            return;
        }

        const payload = {
            item_code: row.dataset.itemCode || '',
            item_description: row.dataset.itemDescription || '',
            audit_group: auditGroupSelect.value,
            item_type: row.dataset.itemType || '',
        };

        try {
            const data = await persistRow(row, payload);
            const record = data.record || {};
            if (record.id) {
                row.dataset.id = record.id;
            }
            if (record.item_type) {
                row.dataset.itemType = record.item_type;
            }
            exitEditMode(row, snapshot, {
                audit_group: record.audit_group ?? payload.audit_group,
            });
        } catch (error) {
            alert(error.message || 'Unable to save audit group.');
        }
    }

    if (tableElement) {
        tableElement.addEventListener('click', (event) => {
            const editButton = event.target.closest('.editRowButton');
            if (editButton) {
                event.preventDefault();
                enterEditMode(editButton.closest('tr'));
                return;
            }

            const saveButton = event.target.closest('.saveRowButton');
            if (saveButton) {
                event.preventDefault();
                const row = saveButton.closest('tr');
                if (row) {
                    handleSave(row);
                }
                return;
            }

            const cancelButton = event.target.closest('.cancelRowButton');
            if (cancelButton) {
                event.preventDefault();
                const row = cancelButton.closest('tr');
                const snapshot = rowSnapshots.get(row);
                if (row && snapshot) {
                    exitEditMode(row, snapshot);
                }
            }
        });
    }
});
