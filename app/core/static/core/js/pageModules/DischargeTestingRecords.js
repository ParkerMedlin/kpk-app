import { FilterForm } from '../objects/tableObjects.js';

const API_BASE = '/core/api/discharge-testing/';

const PH_MIN = 5.1;
const PH_MAX = 10.9;

const htmlEscapeMap = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

function escapeHtml(value = '') {
  const stringValue = value == null ? '' : String(value);
  return stringValue.replace(/[&<>"']/g, (char) => htmlEscapeMap[char]);
}

function formatDateTime(isoString) {
  if (!isoString) {
    return '--';
  }
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return '--';
  }
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

function formatPhDisplay(value) {
  if (value === null || value === undefined || value === '') {
    return '--';
  }
  const numeric = Number(value);
  if (Number.isFinite(numeric)) {
    return numeric.toFixed(2);
  }
  return String(value);
}

function normalizeText(value) {
  return (value || '').toString().trim();
}

function isPhInRange(value) {
  return value >= PH_MIN && value <= PH_MAX;
}

function parsePhValue(raw) {
  const cleaned = normalizeText(raw);
  if (!cleaned) {
    return { value: null };
  }
  const normalized = cleaned.replace(/,/g, '');
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed)) {
    return { error: 'Enter a valid pH value.' };
  }
  return { value: parsed };
}

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

function extractErrorMessage(data) {
  if (!data) {
    return 'Unable to process request.';
  }
  if (data.error) {
    return data.error;
  }
  if (data.errors) {
    if (typeof data.errors === 'string') {
      return data.errors;
    }
    if (typeof data.errors === 'object') {
      const messages = [];
      Object.entries(data.errors).forEach(([field, message]) => {
        if (Array.isArray(message)) {
          messages.push(`${field}: ${message.join(' ')}`);
        } else {
          messages.push(`${field}: ${message}`);
        }
      });
      if (messages.length) {
        return messages.join(' ');
      }
    }
  }
  return 'Unable to process request.';
}

class DischargeTestingRecordsPage {
  constructor() {
    this.root = document.getElementById('discharge-testing-records-app');
    if (!this.root) {
      return;
    }
    this.table = document.getElementById('discharge-testing-records-table');
    this.tableBody = this.table ? this.table.querySelector('tbody') : null;
    this.samplingPersonnelTemplate = document.getElementById('sampling-personnel-options');

    this.canEdit = this.root.dataset.roleLine === 'true' || this.root.dataset.roleLab === 'true';

    this.activeRow = null;
    this.filterForm = new FilterForm({
      tableSelector: '#discharge-testing-records-table',
      rowSelector: 'tr.filterableRow',
      ignoreSelectors: ['[data-is-input="true"]'],
    });

    this.init();
  }

  init() {
    if (this.tableBody) {
      this.tableBody.querySelectorAll('tr.discharge-testing-row').forEach((row) => {
        this.normalizeRowTimestamps(row);
        this.attachRowEvents(row);
      });
    }
  }


  normalizeRowTimestamps(row) {
    if (!row) {
      return;
    }
    const dateCell = row.querySelector('[data-field="date"]');
    const fallbackDate = dateCell?.dataset?.value || '';
    if (!row.dataset.initialUpdatedAt) {
      row.dataset.initialUpdatedAt = fallbackDate;
    }
    if (!row.dataset.finalUpdatedAt) {
      row.dataset.finalUpdatedAt = fallbackDate;
    }
  }

  attachRowEvents(row) {
    const editButton = row.querySelector('.edit-row-btn');
    if (editButton) {
      editButton.addEventListener('click', () => this.enterEditMode(row));
    }
  }

  getRowSnapshot(row) {
    const snapshot = {
      id: row.dataset.toteId || null,
      initial_updated_at: row.dataset.initialUpdatedAt || '',
      final_updated_at: row.dataset.finalUpdatedAt || '',
    };
    row.querySelectorAll('[data-field]').forEach((cell) => {
      const field = cell.dataset.field;
      if (!field || field === 'actions') {
        return;
      }
      if (field === 'sampling_personnel_id') {
        snapshot.sampling_personnel_id = cell.dataset.value ?? '';
        snapshot.sampling_personnel_name = cell.dataset.label ?? cell.textContent.trim();
        return;
      }
      snapshot[field] = cell.dataset.value ?? cell.textContent.trim();
    });
    return snapshot;
  }

  clearValidation(row) {
    row.querySelectorAll('.is-invalid').forEach((input) => {
      input.classList.remove('is-invalid');
    });
    row.querySelectorAll('.invalid-feedback').forEach((feedback) => {
      feedback.remove();
    });
  }

  applyValidationErrors(row, errors) {
    if (!errors || typeof errors !== 'object') {
      return;
    }
    Object.entries(errors).forEach(([field, message]) => {
      const input = row.querySelector(`[data-field="${field}"] [data-is-input="true"]`);
      if (!input) {
        return;
      }
      input.classList.add('is-invalid');
      const feedback = document.createElement('div');
      feedback.className = 'invalid-feedback';
      if (Array.isArray(message)) {
        feedback.textContent = message.join(' ');
      } else {
        feedback.textContent = message;
      }
      input.insertAdjacentElement('afterend', feedback);
    });
  }

  createTextInput(field, value, options = {}) {
    const input = document.createElement('input');
    input.type = options.type || 'text';
    input.className = 'form-control form-control-sm';
    input.dataset.field = field;
    input.dataset.isInput = 'true';
    input.value = value ?? '';
    if (options.step) {
      input.step = options.step;
    }
    if (options.inputMode) {
      input.inputMode = options.inputMode;
    }
    return input;
  }

  createTextarea(field, value) {
    const textarea = document.createElement('textarea');
    textarea.className = 'form-control form-control-sm';
    textarea.dataset.field = field;
    textarea.dataset.isInput = 'true';
    textarea.rows = 2;
    textarea.value = value ?? '';
    return textarea;
  }

  createSelectInput(field, value) {
    const select = document.createElement('select');
    select.className = 'form-select form-select-sm';
    select.dataset.field = field;
    select.dataset.isInput = 'true';

    if (this.samplingPersonnelTemplate) {
      this.samplingPersonnelTemplate.querySelectorAll('option').forEach((option) => {
        select.appendChild(option.cloneNode(true));
      });
    }

    if (value != null && value !== '') {
      select.value = String(value);
    }
    return select;
  }

  enterEditMode(row) {
    if (!this.canEdit || !row) {
      return;
    }

    if (this.activeRow && this.activeRow !== row) {
      const currentData = this.getRowSnapshot(this.activeRow);
      const identifier = currentData.discharge_type || `ID ${this.activeRow.dataset.toteId}`;
      const abandon = window.confirm(`You have unsaved changes on ${identifier}. Abandon them?`);
      if (!abandon) {
        return;
      }
      this.exitEditMode(this.activeRow, currentData);
    }

    if (this.activeRow === row) {
      return;
    }

    const snapshot = this.getRowSnapshot(row);
    row.dataset.snapshot = JSON.stringify(snapshot);
    row.classList.add('table-warning');
    this.activeRow = row;

    row.querySelectorAll('[data-field]').forEach((cell) => {
      const field = cell.dataset.field;
      if (field === 'actions') {
        this.renderEditButtons(row, cell);
        return;
      }
      if (!field || field === 'date' || field === 'lab_technician_name') {
        return;
      }

      const currentValue = cell.dataset.value ?? '';
      let input;
      if (field === 'sampling_personnel_id') {
        input = this.createSelectInput(field, currentValue);
      } else if (field === 'action_required' || field === 'final_disposition') {
        input = this.createTextarea(field, currentValue);
      } else if (field === 'initial_pH' || field === 'final_pH') {
        input = this.createTextInput(field, currentValue, {
          type: 'number',
          step: '0.01',
          inputMode: 'decimal',
        });
      } else {
        input = this.createTextInput(field, currentValue, {
          type: 'text',
        });
      }
      cell.innerHTML = '';
      cell.appendChild(input);
    });
  }

  exitEditMode(row, data, options = {}) {
    if (!row) {
      return;
    }
    const snapshot = data || JSON.parse(row.dataset.snapshot || '{}');
    row.classList.remove('table-warning');
    this.activeRow = null;
    delete row.dataset.snapshot;
    this.applyRowData(row, snapshot, options);
  }

  renderEditButtons(row, cell) {
    cell.innerHTML = '';
    const group = document.createElement('div');
    group.className = 'btn-group btn-group-sm';
    group.setAttribute('role', 'group');

    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'btn btn-success save-row-btn';
    saveBtn.innerHTML = '<i class="fas fa-check"></i>';

    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'btn btn-outline-secondary cancel-row-btn';
    cancelBtn.innerHTML = '<i class="fas fa-times"></i>';

    group.appendChild(saveBtn);
    group.appendChild(cancelBtn);
    cell.appendChild(group);

    saveBtn.addEventListener('click', () => this.handleSave(row));
    cancelBtn.addEventListener('click', () => this.exitEditMode(row));
  }

  renderEditButton(row, cell) {
    cell.innerHTML = '';
    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'btn btn-sm btn-outline-primary edit-row-btn';
    editBtn.title = 'Edit';
    editBtn.innerHTML = '<i class="fas fa-edit"></i>';
    if (!this.canEdit) {
      editBtn.disabled = true;
    }
    editBtn.addEventListener('click', () => this.enterEditMode(row));
    cell.appendChild(editBtn);
  }

  async requestJson(url, options = {}) {
    let response;
    try {
      response = await fetch(url, options);
    } catch (error) {
      throw new Error('Network error. Please check your connection.');
    }

    let data;
    try {
      data = await response.json();
    } catch (error) {
      throw new Error('Unexpected response from the server.');
    }

    if (!response.ok || data.status === 'error') {
      const errorMessage = extractErrorMessage(data);
      const error = new Error(errorMessage);
      error.payload = data;
      throw error;
    }

    return data;
  }

  async handleSave(row) {
    if (!row) {
      return;
    }

    this.clearValidation(row);

    const snapshot = JSON.parse(row.dataset.snapshot || '{}');
    const payload = {};
    const updatedFields = [];

    const sourceInput = row.querySelector('[data-field="discharge_source"] [data-is-input="true"]');
    const dischargeTypeInput = row.querySelector('[data-field="discharge_type"] [data-is-input="true"]');
    const samplingPersonnelInput = row.querySelector('[data-field="sampling_personnel_id"] [data-is-input="true"]');

    if (sourceInput) {
      const value = normalizeText(sourceInput.value);
      if (value !== normalizeText(snapshot.discharge_source)) {
        payload.discharge_source = value;
        updatedFields.push('discharge_source');
      }
    }
    if (dischargeTypeInput) {
      const value = normalizeText(dischargeTypeInput.value);
      if (value !== normalizeText(snapshot.discharge_type)) {
        payload.discharge_type = value;
        updatedFields.push('discharge_type');
      }
    }
    if (samplingPersonnelInput) {
      const value = samplingPersonnelInput.value ?? '';
      if (!value) {
        samplingPersonnelInput.classList.add('is-invalid');
        this.applyValidationErrors(row, { sampling_personnel_id: 'Sampling personnel is required.' });
        return;
      }
      if (String(value) !== String(snapshot.sampling_personnel_id ?? '')) {
        payload.sampling_personnel_id = value;
        updatedFields.push('sampling_personnel_id');
      }
    }

    let initialParsed = { value: null };
    let finalParsed = { value: null };

    const initialInput = row.querySelector('[data-field="initial_pH"] [data-is-input="true"]');
    const actionInput = row.querySelector('[data-field="action_required"] [data-is-input="true"]');
    const dispositionInput = row.querySelector('[data-field="final_disposition"] [data-is-input="true"]');
    const finalInput = row.querySelector('[data-field="final_pH"] [data-is-input="true"]');

    if (initialInput) {
      initialParsed = parsePhValue(initialInput.value);
      if (initialParsed.error) {
        initialInput.classList.add('is-invalid');
        this.applyValidationErrors(row, { initial_pH: initialParsed.error });
        return;
      }
      const snapshotInitial = snapshot.initial_pH;
      const normalizedSnapshot = snapshotInitial === '' || snapshotInitial == null
        ? null
        : Number(snapshotInitial);
      if (initialParsed.value === null) {
        if (normalizedSnapshot !== null) {
          initialInput.classList.add('is-invalid');
          this.applyValidationErrors(row, { initial_pH: 'Initial pH is required.' });
          return;
        }
      } else if (!Number.isFinite(normalizedSnapshot) || initialParsed.value !== normalizedSnapshot) {
        payload.initial_pH = initialParsed.value;
        updatedFields.push('initial_pH');
      }
    }

    if (actionInput) {
      const actionValue = actionInput.value || '';
      if (normalizeText(actionValue) !== normalizeText(snapshot.action_required)) {
        payload.action_required = actionValue;
        updatedFields.push('action_required');
      }
    }

    if (dispositionInput) {
      const dispositionValue = normalizeText(dispositionInput.value);
      if (!dispositionValue) {
        dispositionInput.classList.add('is-invalid');
        this.applyValidationErrors(row, { final_disposition: 'Final disposition is required.' });
        return;
      }
      if (dispositionValue !== normalizeText(snapshot.final_disposition)) {
        payload.final_disposition = dispositionValue;
        updatedFields.push('final_disposition');
      }
    }

    if (finalInput) {
      finalParsed = parsePhValue(finalInput.value);
      if (finalParsed.error) {
        finalInput.classList.add('is-invalid');
        this.applyValidationErrors(row, { final_pH: finalParsed.error });
        return;
      }

      const snapshotFinal = snapshot.final_pH;
      const normalizedSnapshot = snapshotFinal === '' || snapshotFinal == null
        ? null
        : Number(snapshotFinal);
      if (finalParsed.value === null) {
        if (normalizedSnapshot !== null) {
          finalInput.classList.add('is-invalid');
          this.applyValidationErrors(row, { final_pH: 'Final pH is required.' });
          return;
        }
      } else if (!Number.isFinite(normalizedSnapshot) || finalParsed.value !== normalizedSnapshot) {
        payload.final_pH = finalParsed.value;
        updatedFields.push('final_pH');
      }
    }

    if (finalParsed.value !== null) {
      const initialValue = initialParsed.value !== null
        ? initialParsed.value
        : snapshot.initial_pH === '' || snapshot.initial_pH == null
          ? null
          : Number(snapshot.initial_pH);
      if (initialValue === null) {
        this.applyValidationErrors(row, { final_pH: 'Initial pH must be recorded before final pH.' });
        return;
      }
      if (!isPhInRange(finalParsed.value)) {
        this.applyValidationErrors(row, {
          final_pH: `Final pH must be between ${PH_MIN} and ${PH_MAX}.`,
        });
        return;
      }

      if (initialValue !== null && !isPhInRange(initialValue)) {
        const actionValue = normalizeText(payload.action_required ?? snapshot.action_required);
        if (!actionValue) {
          this.applyValidationErrors(row, {
            action_required: 'Action details are required when initial pH is out of range.',
          });
          return;
        }
      }
    }

    if (!Object.keys(payload).length) {
      this.exitEditMode(row, snapshot);
      return;
    }

    const saveButton = row.querySelector('.save-row-btn');
    const cancelButton = row.querySelector('.cancel-row-btn');
    [saveButton, cancelButton].forEach((btn) => {
      if (btn) {
        btn.disabled = true;
      }
    });

    const originalSaveHtml = saveButton ? saveButton.innerHTML : '';
    if (saveButton) {
      saveButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
    }

    try {
      const toteId = row.dataset.toteId;
      if (!toteId) {
        throw new Error('Unable to determine which discharge test to update.');
      }
      const response = await this.requestJson(`${API_BASE}${toteId}/`, {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify(payload),
      });

      const tote = response.tote || {};
      this.exitEditMode(row, tote, { updatedFields });
    } catch (error) {
      console.error(error);
      if (error.payload && error.payload.errors) {
        this.applyValidationErrors(row, error.payload.errors);
      }
      alert(error.message);
    } finally {
      if (saveButton) {
        saveButton.innerHTML = originalSaveHtml;
      }
      [saveButton, cancelButton].forEach((btn) => {
        if (btn) {
          btn.disabled = false;
        }
      });
    }
  }

  applyRowData(row, tote, options = {}) {
    const data = {
      id: tote.id ?? row.dataset.toteId ?? null,
      date: tote.date ?? row.querySelector('[data-field="date"]')?.dataset?.value ?? '',
      discharge_source: tote.discharge_source ?? '',
      discharge_type: tote.discharge_type ?? '',
      initial_pH: tote.initial_pH ?? '',
      action_required: tote.action_required ?? '',
      final_disposition: tote.final_disposition ?? '',
      final_pH: tote.final_pH ?? '',
      sampling_personnel_id: tote.sampling_personnel_id ?? '',
      sampling_personnel_name: tote.sampling_personnel_name ?? '',
      lab_technician_name: tote.lab_technician_name ?? '',
    };

    const updatedFields = options.updatedFields || [];
    const nowIso = new Date().toISOString();

    let initialUpdatedAt = row.dataset.initialUpdatedAt || data.date;
    let finalUpdatedAt = row.dataset.finalUpdatedAt || data.date;

    if (options.initialize) {
      initialUpdatedAt = data.date;
      finalUpdatedAt = data.date;
    }

    if (updatedFields.includes('initial_pH')) {
      initialUpdatedAt = nowIso;
    }
    if (updatedFields.includes('final_pH')) {
      finalUpdatedAt = nowIso;
    }

    row.dataset.toteId = data.id ? String(data.id) : '';
    row.dataset.initialUpdatedAt = initialUpdatedAt || '';
    row.dataset.finalUpdatedAt = finalUpdatedAt || '';

    const dateCell = row.querySelector('[data-field="date"]');
    if (dateCell) {
      dateCell.dataset.value = data.date || '';
      const dateDisplay = dateCell.querySelector('.fw-semibold') || document.createElement('div');
      dateDisplay.className = 'fw-semibold';
      dateDisplay.textContent = formatDateTime(data.date);
      if (!dateCell.contains(dateDisplay)) {
        dateCell.appendChild(dateDisplay);
      }
    }

    this.setTextCell(row, 'discharge_source', data.discharge_source);
    this.setTextCell(row, 'discharge_type', data.discharge_type);

    this.setPhCell(row, 'initial_pH', data.initial_pH, data.lab_technician_name, initialUpdatedAt, 'initial');
    this.setTextCell(row, 'action_required', data.action_required, true);
    this.setTextCell(row, 'final_disposition', data.final_disposition, true);
    this.setPhCell(row, 'final_pH', data.final_pH, data.lab_technician_name, finalUpdatedAt, 'final');

    this.setSamplingPersonnelCell(row, data.sampling_personnel_id, data.sampling_personnel_name);
    this.setTextCell(row, 'lab_technician_name', data.lab_technician_name);

    const actionsCell = row.querySelector('[data-field="actions"]');
    if (actionsCell) {
      this.renderEditButton(row, actionsCell);
    }
  }

  setTextCell(row, field, value, allowLineBreaks = false) {
    const cell = row.querySelector(`[data-field="${field}"]`);
    if (!cell) {
      return;
    }
    const textValue = value == null ? '' : String(value);
    cell.dataset.value = textValue;
    if (!textValue) {
      cell.textContent = '--';
      return;
    }
    if (allowLineBreaks) {
      cell.innerHTML = escapeHtml(textValue).replace(/\n/g, '<br>');
    } else {
      cell.textContent = textValue;
    }
  }

  setPhCell(row, field, value, updatedBy, updatedAt, prefix) {
    const cell = row.querySelector(`[data-field="${field}"]`);
    if (!cell) {
      return;
    }
    const displayValue = formatPhDisplay(value);
    cell.dataset.value = value == null ? '' : value;
    const byText = updatedBy || '--';
    const timeText = formatDateTime(updatedAt);

    cell.innerHTML = `
      <div class="fw-semibold">${escapeHtml(displayValue)}</div>
      <div class="text-muted small" data-role="${prefix}-ph-updated-by">${escapeHtml(byText)}</div>
      <div class="text-muted small" data-role="${prefix}-ph-updated-at">${escapeHtml(timeText)}</div>
    `;
  }

  setSamplingPersonnelCell(row, id, name) {
    const cell = row.querySelector('[data-field="sampling_personnel_id"]');
    if (!cell) {
      return;
    }
    const idValue = id == null ? '' : String(id);
    const labelValue = name == null ? '' : String(name);
    cell.dataset.value = idValue;
    cell.dataset.label = labelValue;
    if (!labelValue) {
      cell.textContent = '--';
      return;
    }
    cell.textContent = labelValue;
  }
}

function init() {
  document.addEventListener('DOMContentLoaded', () => {
    new DischargeTestingRecordsPage();
  });
}

init();
