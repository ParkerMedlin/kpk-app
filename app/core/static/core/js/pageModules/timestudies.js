import { FilterForm } from '../objects/lookupFormObjects.js';

let table;
let feedback;
let csrfTokenInput;
let refreshButton;

const dateFormatter = new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
});

function showMessage(message, variant = 'success') {
    if (!feedback) {
        return;
    }

    feedback.textContent = message;
    feedback.classList.remove('d-none', 'alert-success', 'alert-danger', 'alert-info');

    let cssClass = 'alert-success';
    if (variant === 'error') {
        cssClass = 'alert-danger';
    } else if (variant === 'info') {
        cssClass = 'alert-info';
    }
    feedback.classList.add(cssClass);
}

function clearMessage() {
    if (!feedback) {
        return;
    }
    feedback.textContent = '';
    feedback.classList.add('d-none');
    feedback.classList.remove('alert-success', 'alert-danger', 'alert-info');
}

function toInputValue(isoString) {
    if (!isoString) {
        return '';
    }
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
        return '';
    }
    const offset = date.getTimezoneOffset() * 60000;
    const local = new Date(date.getTime() - offset);
    return local.toISOString().slice(0, 16);
}

function nowInputValue() {
    const now = new Date();
    now.setSeconds(0, 0);
    const offset = now.getTimezoneOffset() * 60000;
    const local = new Date(now.getTime() - offset);
    return local.toISOString().slice(0, 16);
}

function formatDisplayValue(isoString) {
    if (!isoString) {
        return '—';
    }
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
        return 'Invalid timestamp';
    }
    return dateFormatter.format(date);
}

function setCellValue(cell, isoString) {
    const value = isoString || '';
    cell.dataset.raw = value;
    cell.innerHTML = '';
    const span = document.createElement('span');
    if (value) {
        span.className = 'timestudy-value';
        span.textContent = formatDisplayValue(value);
    } else {
        span.className = 'text-muted';
        span.textContent = '—';
    }
    cell.appendChild(span);
}

function buildDatetimeEditor(initialIso) {
    const wrapper = document.createElement('div');
    wrapper.className = 'timestudy-editor';

    const input = document.createElement('input');
    input.type = 'datetime-local';
    input.className = 'form-control form-control-sm';
    input.value = toInputValue(initialIso);
    wrapper.appendChild(input);

    const nowBtn = document.createElement('button');
    nowBtn.type = 'button';
    nowBtn.className = 'btn btn-outline-secondary btn-sm';
    nowBtn.textContent = 'Now';
    nowBtn.addEventListener('click', () => {
        input.value = nowInputValue();
        input.dispatchEvent(new Event('input'));
    });
    wrapper.appendChild(nowBtn);

    const clearBtn = document.createElement('button');
    clearBtn.type = 'button';
    clearBtn.className = 'btn btn-outline-secondary btn-sm';
    clearBtn.textContent = 'Clear';
    clearBtn.addEventListener('click', () => {
        input.value = '';
        input.dispatchEvent(new Event('input'));
    });
    wrapper.appendChild(clearBtn);

    return { container: wrapper, input };
}

function exitEditMode(row, revertToOriginal = false) {
    if (!row._editState) {
        return;
    }

    const { startCell, stopCell, originalStart, originalStop, originalActionsHTML } = row._editState;

    if (revertToOriginal) {
        setCellValue(startCell, originalStart);
        setCellValue(stopCell, originalStop);
    }

    const actionsCell = row.querySelector('[data-field="actions"]');
    actionsCell.innerHTML = originalActionsHTML;

    row.classList.remove('table-warning');
    row.dataset.editing = 'false';
    delete row._editState;
}

function enterEditMode(row) {
    if (row.dataset.editing === 'true') {
        return;
    }

    const currentlyEditing = table.querySelector('tr[data-editing="true"]');
    if (currentlyEditing && currentlyEditing !== row) {
        exitEditMode(currentlyEditing, true);
    }

    const startCell = row.querySelector('[data-field="start_time"]');
    const stopCell = row.querySelector('[data-field="stop_time"]');
    const actionsCell = row.querySelector('[data-field="actions"]');
    const originalActionsHTML = actionsCell.innerHTML;

    const originalStart = startCell.dataset.raw || '';
    const originalStop = stopCell.dataset.raw || '';

    const { container: startEditor, input: startInput } = buildDatetimeEditor(originalStart);
    const { container: stopEditor, input: stopInput } = buildDatetimeEditor(originalStop);

    startCell.innerHTML = '';
    stopCell.innerHTML = '';
    startCell.appendChild(startEditor);
    stopCell.appendChild(stopEditor);

    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'btn btn-success btn-sm';
    saveBtn.dataset.action = 'save';
    saveBtn.textContent = 'Save';

    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'btn btn-outline-secondary btn-sm';
    cancelBtn.dataset.action = 'cancel';
    cancelBtn.textContent = 'Cancel';

    const buttonGroup = document.createElement('div');
    buttonGroup.className = 'btn-group btn-group-sm';
    buttonGroup.append(saveBtn, cancelBtn);
    actionsCell.innerHTML = '';
    actionsCell.appendChild(buttonGroup);

    row._editState = {
        startCell,
        stopCell,
        startInput,
        stopInput,
        originalStart,
        originalStop,
        originalActionsHTML,
        saveButton: saveBtn,
        cancelButton: cancelBtn,
    };

    row.classList.add('table-warning');
    row.dataset.editing = 'true';
    window.setTimeout(() => startInput.focus(), 0);
}

function formatErrors(errors) {
    if (!errors || typeof errors !== 'object') {
        return null;
    }
    return Object.entries(errors)
        .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join('; ') : messages}`)
        .join(' • ');
}

async function saveRow(row) {
    if (!row._editState) {
        return;
    }

    const { startInput, stopInput, startCell, stopCell, saveButton, cancelButton } = row._editState;
    const lotId = row.dataset.lotId;

    const payload = {
        start_time: startInput.value.trim(),
        stop_time: stopInput.value.trim(),
    };

    const url = `/core/lot-num-records/${lotId}/timestudy/`;

    try {
        showMessage('Saving timestudy…', 'info');
        saveButton.disabled = true;
        cancelButton.disabled = true;

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfTokenInput ? csrfTokenInput.value : '',
            },
            body: JSON.stringify(payload),
        });

        const responseText = await response.text();
        let responseData;
        try {
            responseData = responseText ? JSON.parse(responseText) : {};
        } catch {
            responseData = {};
        }

        if (!response.ok) {
            const message =
                (responseData && (responseData.error || formatErrors(responseData.errors))) ||
                `Unable to save timestudy (HTTP ${response.status}).`;
            throw new Error(message);
        }

        if (responseData.status === 'success') {
            const updatedRecord = responseData.data || {};
            setCellValue(startCell, updatedRecord.start_time || '');
            setCellValue(stopCell, updatedRecord.stop_time || '');

            showMessage(`Lot ${updatedRecord.lot_number || lotId} timestudy updated.`, 'success');
            exitEditMode(row, false);
        } else if (responseData.status === 'noop') {
            showMessage(responseData.message || 'No timestudy changes were detected.', 'info');
            exitEditMode(row, true);
        } else {
            const message =
                (responseData && (responseData.error || formatErrors(responseData.errors))) ||
                'Unable to save timestudy.';
            throw new Error(message);
        }
    } catch (error) {
        console.error(error);
        showMessage(error.message || 'Unable to save timestudy.', 'error');
        if (saveButton) {
            saveButton.disabled = false;
        }
        if (cancelButton) {
            cancelButton.disabled = false;
        }
    }
}

function bindTableEvents() {
    if (!table) {
        return;
    }

    table.addEventListener('click', (event) => {
        const button = event.target.closest('button');
        if (!button) {
            return;
        }

        const row = button.closest('tr');
        if (!row) {
            return;
        }

        if (button.classList.contains('edit-lot-btn')) {
            enterEditMode(row);
            clearMessage();
            return;
        }

        const action = button.dataset.action;
        if (action === 'save') {
            saveRow(row);
        } else if (action === 'cancel') {
            exitEditMode(row, true);
            clearMessage();
        }
    });
}

function bindRefreshButton() {
    if (!refreshButton) {
        return;
    }

    refreshButton.addEventListener('click', () => {
        window.location.reload();
    });
}

document.addEventListener('DOMContentLoaded', () => {
    table = document.querySelector('#displayTable');
    feedback = document.querySelector('#timestudy-feedback');
    csrfTokenInput = document.querySelector('#timestudy-csrf input[name="csrfmiddlewaretoken"]');
    refreshButton = document.querySelector('#timestudy-refresh-btn');

    new FilterForm();
    bindTableEvents();
    bindRefreshButton();
});
