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

    const addNewOption = document.createElement('option');
    addNewOption.value = '__add_new__';
    addNewOption.textContent = 'Add New...';
    select.appendChild(addNewOption);

    if (!selected) {
        select.value = '';
    }

    return select;
}

function getRowSnapshot(row) {
    const snapshot = {};
    const auditGroupCell = row.querySelector('[data-field="audit_group"]');

    snapshot.audit_group = auditGroupCell ? auditGroupCell.textContent.trim() : '';

    return snapshot;
}

function renderEditButton(auditGroupCell, textValue) {
    auditGroupCell.innerHTML = '';
    const valueSpan = document.createElement('span');
    valueSpan.className = 'audit-group-value';
    valueSpan.textContent = textValue;

    auditGroupCell.appendChild(valueSpan);
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-link editRowButton p-0 ms-1';
    const icon = document.createElement('i');
    icon.className = 'fa fa-pencil';
    icon.setAttribute('aria-hidden', 'true');
    button.appendChild(icon);
    auditGroupCell.appendChild(button);
}

function renderSaveCancelButtons(container) {
    container.innerHTML = '';
    const saveButton = document.createElement('button');
    saveButton.type = 'button';
    saveButton.className = 'btn btn-sm btn-primary saveRowButton me-2';
    saveButton.textContent = 'Save';

    const cancelButton = document.createElement('button');
    cancelButton.type = 'button';
    cancelButton.className = 'btn btn-sm btn-outline-secondary cancelRowButton';
    cancelButton.textContent = 'Cancel';

    container.appendChild(saveButton);
    container.appendChild(cancelButton);
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
        ? [0, 2, 6]
        : [1, 2, 5];
    const itemColumnIndex = hasSelectColumn ? 1 : 0;

    const dataTable = initDataTableWithExport('#displayTable', {
        order: [[itemColumnIndex, 'asc']],
        columnDefs: nonSortableColumns.length
            ? [{ targets: nonSortableColumns, orderable: false }]
            : [],
    });

    const auditGroupChoices = window.AUDIT_GROUP_CHOICES || [];
    const $groupSelectModal = $('#groupSelectModal');
    if ($groupSelectModal.length) {
        auditGroupChoices.forEach((group) => {
            $groupSelectModal.append(`<option value="${group}">${group}</option>`);
        });

        $groupSelectModal.on('change', function () {
            $('#listNameInput').val($(this).val());
        });

        $('#submitCreateListFromGroup').on('click', async function() {
            const selectedGroup = $groupSelectModal.val();
            const listName = $('#listNameInput').val().trim();

            if (!selectedGroup) {
                alert('Please select an audit group.');
                return;
            }

            const urlParams = new URLSearchParams(window.location.search);
            const recordType = urlParams.get('recordType') || '';

            try {
                const response = await fetch('/core/api/count-list-from-group/', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({
                        audit_group: selectedGroup,
                        record_type: recordType,
                        collection_name: listName,
                    }),
                });

                const data = await response.json();
                if (!response.ok || data.status !== 'success') {
                    alert(data.error || 'Failed to create count list.');
                    return;
                }

                alert(`Count list "${data.collection_name}" created with ${data.item_count} items.`);
                const modal = bootstrap.Modal.getInstance(document.getElementById('createListFromGroupModal'));
                if (modal) modal.hide();
                $groupSelectModal.val('');
                $('#listNameInput').val('');
            } catch (error) {
                alert('Unable to create count list. Please try again.');
            }
        });
    }
    const rowSnapshots = new WeakMap();
    let activeRow = null;

    function exitEditMode(row, snapshot, updatedValues = null) {
        if (!row) {
            return;
        }
        const auditGroupCell = row.querySelector('[data-field="audit_group"]');

        if (auditGroupCell) {
            const displayValue = updatedValues ? updatedValues.audit_group : snapshot.audit_group;
            renderEditButton(auditGroupCell, displayValue);
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
        if (!auditGroupCell) {
            return;
        }

        const snapshot = getRowSnapshot(row);
        rowSnapshots.set(row, snapshot);
        activeRow = row;

        const auditGroupSelect = buildSelect(auditGroupChoices, snapshot.audit_group);

        auditGroupCell.textContent = '';
        auditGroupCell.appendChild(auditGroupSelect);
        const actionsWrapper = document.createElement('div');
        actionsWrapper.className = 'd-flex align-items-center gap-1 mt-1';
        renderSaveCancelButtons(actionsWrapper);
        auditGroupCell.appendChild(actionsWrapper);
        auditGroupSelect.addEventListener('change', () => {
            const existingInput = auditGroupCell.querySelector('.custom-audit-group-input');
            if (auditGroupSelect.value === '__add_new__') {
                if (!existingInput) {
                    const input = document.createElement('input');
                    input.type = 'text';
                    input.className = 'form-control form-control-sm custom-audit-group-input mt-1';
                    input.placeholder = 'New audit group name';
                    auditGroupCell.insertBefore(input, auditGroupCell.querySelector('.d-flex'));
                    input.focus();
                }
            } else if (existingInput) {
                existingInput.remove();
            }
        });

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
        let auditGroupValue;
        const customInput = row.querySelector('[data-field="audit_group"] .custom-audit-group-input');
        if (auditGroupSelect.value === '__add_new__' && customInput) {
            auditGroupValue = customInput.value.trim();
            if (!auditGroupValue) {
                alert('Please enter a name for the new audit group.');
                return;
            }
        } else {
            auditGroupValue = auditGroupSelect.value;
        }

        const payload = {
            item_code: row.dataset.itemCode || '',
            item_description: row.dataset.itemDescription || '',
            audit_group: auditGroupValue,
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
            if (customInput && auditGroupValue && !auditGroupChoices.includes(auditGroupValue)) {
                auditGroupChoices.push(auditGroupValue);
                auditGroupChoices.sort();
            }
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
