import { FilterForm } from '../objects/tableObjects.js';

const API_ENDPOINT_BASE = '/core/api/container-classification/';
const CREATE_ENDPOINT = `${API_ENDPOINT_BASE}create/`;
const NEXT_ID_ENDPOINT = `${API_ENDPOINT_BASE}next-id/`;
const VALIDATE_ENDPOINT = '/core/api/validate-blend-item/';

const itemValidationCache = new Map();

const WASTE_RAG_CHOICES = [
  { value: '', label: '' },
  { value: 'Acid', label: 'Acid' },
  { value: 'Flammable', label: 'Flammable' },
  { value: 'Grease/Oil', label: 'Grease/Oil' },
  { value: 'Soap', label: 'Soap' },
  { value: 'Base', label: 'Base' },
];

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

function normalizeItemCode(value = '') {
  return (value || '').trim().toUpperCase();
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

function buildInput(field, value) {
  if (field === 'waste_rag') {
    const select = document.createElement('select');
    select.className = 'form-select form-select-sm';
    WASTE_RAG_CHOICES.forEach((choice) => {
      const option = document.createElement('option');
      option.value = choice.value;
      option.textContent = choice.label;
      select.appendChild(option);
    });
    select.value = value ?? '';
    select.dataset.field = field;
    select.dataset.isInput = 'true';
    return select;
  }

  const inputType = field === 'tank_classification' ? 'textarea' : 'input';
  const input = document.createElement(inputType);
  input.className = 'form-control form-control-sm';
  if (inputType === 'textarea') {
    input.rows = 3;
  }
  if (field === 'item_code') {
    input.value = normalizeItemCode(value);
  } else {
    input.value = value ?? '';
  }
  input.dataset.field = field;
  input.dataset.isInput = 'true';
  if (field === 'item_code') {
    input.placeholder = 'ITEMCODE';
    input.autocomplete = 'off';
    input.spellcheck = false;
  } else {
    input.autocomplete = 'off';
  }
  return input;
}

function renderDisplayCell(field, value) {
  if (!value) {
    return '';
  }
  if (field === 'tank_classification') {
    return escapeHtml(value).replace(/\n/g, '<br>');
  }
  return escapeHtml(value);
}

async function saveRow(classificationId, payload) {
  const url = new URL(`${API_ENDPOINT_BASE}${classificationId}/`, window.location.origin);
  const payloadToSend = { ...payload };
  if (Object.prototype.hasOwnProperty.call(payloadToSend, 'item_code')) {
    payloadToSend.item_code = normalizeItemCode(payloadToSend.item_code);
  }

  const response = await fetch(url.toString(), {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
      'X-Requested-With': 'XMLHttpRequest',
    },
    body: JSON.stringify(payloadToSend),
  });

  let data;
  try {
    data = await response.json();
  } catch (error) {
    throw new Error('Unexpected response from the server.');
  }

  if (!response.ok || data.status !== 'success') {
    const message = data.error || (data.errors && JSON.stringify(data.errors)) || 'Unable to update container classification.';
    throw new Error(message);
  }

  return data;
}

async function createClassification(payload) {
  const payloadToSend = {
    ...payload,
    item_code: normalizeItemCode(payload.item_code),
  };
  const response = await fetch(CREATE_ENDPOINT, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
      'X-Requested-With': 'XMLHttpRequest',
    },
    body: JSON.stringify(payloadToSend),
  });

  let data;
  try {
    data = await response.json();
  } catch (error) {
    throw new Error('Unexpected response from the server.');
  }

  if (!response.ok || data.status !== 'success') {
    const message = data.error || (data.errors && JSON.stringify(data.errors)) || 'Unable to create container classification.';
    throw new Error(message);
  }

  return data;
}

class ContainerClassificationTable {
  constructor() {
    this.activeRow = null;
    this.table = document.getElementById('containerClassificationTable');
    this.tableBody = this.table ? this.table.querySelector('tbody') : null;
    this.addButton = document.getElementById('add-classification-btn');
    this.autofillFields = ['tote_classification', 'flush_tote', 'hose_color', 'tank_classification'];
    this.datalistMap = {};
    this.autofillFields.forEach((field) => {
      this.datalistMap[field] = this.ensureDatalist(field);
    });

    new FilterForm({
      ignoreSelectors: ['[data-is-input="true"]'],
    });

    this.init();
    this.refreshAutofillOptions();
  }

  init() {
    if (!this.table || !this.tableBody) {
      return;
    }

    this.table.querySelectorAll('.filterableRow').forEach((row) => {
      this.normalizeRowDisplay(row);
      this.attachRowEvents(row);
    });

    if (this.addButton) {
      this.addButton.addEventListener('click', () => this.handleAdd());
    }
  }

  getRowSnapshot(row) {
    const data = {};
    row.querySelectorAll('[data-field]').forEach((cell) => {
      const field = cell.dataset.field;
      if (field === 'actions') {
        return;
      }
      if (field === 'item_code') {
        const rawValue = cell.dataset.value ?? cell.textContent.trim();
        data[field] = normalizeItemCode(rawValue);
        return;
      }
      data[field] = cell.dataset.value ?? cell.textContent.trim();
    });
    return data;
  }

  normalizeRowDisplay(row) {
    const itemCell = row.querySelector('[data-field="item_code"]');
    if (itemCell) {
      const normalized = normalizeItemCode(itemCell.dataset.value ?? itemCell.textContent.trim());
      itemCell.dataset.value = normalized;
      itemCell.textContent = normalized;
    }
  }

  ensureDatalist(field) {
    const id = `container-classification-${field}-options`;
    let datalist = document.getElementById(id);
    if (!datalist) {
      datalist = document.createElement('datalist');
      datalist.id = id;
      document.body.appendChild(datalist);
    }
    return datalist;
  }

  refreshAutofillOptions() {
    this.autofillFields.forEach((field) => {
      const datalist = this.datalistMap[field];
      if (!datalist) {
        return;
      }
      const values = Array.from(this.collectColumnValues(null, field));
      values.sort((a, b) => a.localeCompare(b));
      datalist.innerHTML = '';
      values.forEach((value) => {
        const option = document.createElement('option');
        option.value = value;
        datalist.appendChild(option);
      });
    });
  }

  getAutofillPlaceholder(field) {
    switch (field) {
      case 'tote_classification':
        return 'Use existing storage tote...';
      case 'flush_tote':
        return 'Use existing flush tote...';
      case 'hose_color':
        return 'Use existing hose class...';
      case 'tank_classification':
        return 'Use existing guidance...';
      default:
        return 'Use existing value...';
    }
  }

  collectColumnValues(excludeRow = null, field = 'item_code') {
    const values = new Set();
    if (!this.tableBody) {
      return values;
    }

    this.tableBody.querySelectorAll('tr.filterableRow').forEach((row) => {
      if (excludeRow && row === excludeRow) {
        return;
      }

      const cell = row.querySelector(`[data-field="${field}"]`);
      if (!cell) {
        return;
      }
      const rawValue = cell.dataset.value ?? cell.textContent.trim();
      if (!rawValue) {
        return;
      }
      const normalized = field === 'item_code'
        ? normalizeItemCode(rawValue)
        : rawValue.trim();
      if (normalized) {
        values.add(normalized);
      }
    });

    return values;
  }

  collectExistingItemCodes(excludeRow = null) {
    return this.collectColumnValues(excludeRow, 'item_code');
  }

  setupItemCodeValidation(row, input, feedbackNode) {
    if (!input) {
      return;
    }
    input.validationFeedbackEl = feedbackNode || null;
    const queueValidation = (options) => {
      const token = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
      input.dataset.validationToken = token;
      this.runItemCodeValidation(row, input, feedbackNode, { ...options, token }).catch((error) => {
        console.error('Item code validation error', error);
      });
    };
    input.addEventListener('input', () => {
      input.value = normalizeItemCode(input.value);
      queueValidation({ skipRemote: true, allowEmpty: true });
    });
    input.addEventListener('blur', () => {
      queueValidation({ skipRemote: false, allowEmpty: false });
    });

    if (input.value) {
      queueValidation({ skipRemote: false, allowEmpty: false });
    }
  }

  clearValidationState(input, feedback) {
    if (input) {
      input.classList.remove('is-invalid');
      input.classList.remove('is-valid');
    }
    if (feedback) {
      feedback.textContent = '';
      feedback.classList.add('d-none');
      feedback.classList.remove('text-danger', 'text-success');
    }
  }

  applyInvalidState(input, feedback, message) {
    if (input) {
      input.classList.add('is-invalid');
      input.classList.remove('is-valid');
    }
    if (feedback) {
      feedback.textContent = message || 'Invalid item code.';
      feedback.classList.remove('d-none');
      feedback.classList.remove('text-success');
      feedback.classList.add('text-danger');
    }
  }

  applyValidState(input, feedback, message) {
    if (input) {
      if (message) {
        input.classList.add('is-valid');
      } else {
        input.classList.remove('is-valid');
      }
      input.classList.remove('is-invalid');
    }
    if (feedback) {
      if (message) {
        feedback.textContent = message;
        feedback.classList.remove('d-none');
        feedback.classList.remove('text-danger');
        feedback.classList.add('text-success');
      } else {
        feedback.textContent = '';
        feedback.classList.add('d-none');
        feedback.classList.remove('text-danger', 'text-success');
      }
    }
  }

  async fetchBlendItemValidation(itemCode) {
    const normalized = normalizeItemCode(itemCode);
    if (!normalized) {
      return { valid: false, message: 'Item code is required.' };
    }
    if (itemValidationCache.has(normalized)) {
      return itemValidationCache.get(normalized);
    }

    const formData = new FormData();
    formData.append('item_code', normalized);

    let response;
    let data;
    try {
      response = await fetch(VALIDATE_ENDPOINT, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCsrfToken(),
        },
        body: formData,
      });
    } catch (error) {
      throw new Error('Unable to validate item code right now.');
    }

    try {
      data = await response.json();
    } catch (error) {
      throw new Error('Unexpected response while validating item code.');
    }

    if (!response.ok) {
      const message = (data && data.error) || 'Unable to validate item code right now.';
      throw new Error(message);
    }

    const description = (data.item_description || '').trim();
    const isBlend = Boolean(data.valid && description.toUpperCase().startsWith('BLEND-'));
    const result = isBlend
      ? { valid: true, description }
      : { valid: false, message: (data && data.error) || 'Item code must match a blend item.' };

    itemValidationCache.set(normalized, result);
    return result;
  }

  async runItemCodeValidation(row, input, feedback, options = {}) {
    const {
      skipRemote = false,
      allowEmpty = false,
      token = null,
    } = options;

    const value = normalizeItemCode(input.value);
    input.value = value;

    if (!value) {
      if (allowEmpty) {
        this.clearValidationState(input, feedback);
      } else {
        this.applyInvalidState(input, feedback, 'Item code is required.');
      }
      return false;
    }

    const existingCodes = this.collectExistingItemCodes(row);
    if (existingCodes.has(value)) {
      this.applyInvalidState(input, feedback, 'This item already has a container classification.');
      return false;
    }

    if (skipRemote) {
      this.clearValidationState(input, feedback);
      return true;
    }

    let validation;
    try {
      validation = await this.fetchBlendItemValidation(value);
    } catch (error) {
      this.applyInvalidState(input, feedback, error.message || 'Unable to validate item code right now.');
      return false;
    }

    if (token && input.dataset.validationToken && input.dataset.validationToken !== token) {
      return validation.valid;
    }

    if (!validation.valid) {
      this.applyInvalidState(input, feedback, validation.message || 'Item code must match a blend item.');
      return false;
    }

    const successMessage = validation.description ? `Blend: ${validation.description}` : '';
    this.applyValidState(input, feedback, successMessage);
    return true;
  }

  enterEditMode(row) {
    if (!row) {
      return;
    }

    if (this.activeRow && this.activeRow !== row) {
      const currentData = this.getRowSnapshot(this.activeRow);
      const identifier = currentData.item_code || `ID ${this.activeRow.dataset.classificationId}`;
      const abandon = window.confirm(`You have unsaved changes on ${identifier}. Abandon them?`);
      if (!abandon) {
        return;
      }
      if (this.activeRow.dataset.isNew === 'true') {
        this.activeRow.remove();
        this.activeRow = null;
      } else {
        this.exitEditMode(this.activeRow, JSON.stringify(currentData));
      }
    }

    if (this.activeRow === row) {
      return;
    }

    const snapshot = this.getRowSnapshot(row);
    row.dataset.snapshot = JSON.stringify(snapshot);
    row.classList.add('table-warning');

    row.querySelectorAll('[data-field]').forEach((cell) => {
      const field = cell.dataset.field;
      if (field === 'actions') {
        cell.innerHTML = '';
        const buttonGroup = document.createElement('div');
        buttonGroup.className = 'btn-group btn-group-sm';
        buttonGroup.setAttribute('role', 'group');
        const saveBtn = document.createElement('button');
        saveBtn.type = 'button';
        saveBtn.className = 'btn btn-success save-row-btn';
        saveBtn.innerHTML = '<i class="fas fa-check"></i>';
        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className = 'btn btn-outline-secondary cancel-row-btn';
        cancelBtn.innerHTML = '<i class="fas fa-times"></i>';
        const deleteBtn = document.createElement('button');
        deleteBtn.type = 'button';
        deleteBtn.className = 'btn btn-outline-danger delete-row-btn';
        deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
        buttonGroup.append(saveBtn, cancelBtn, deleteBtn);
        cell.appendChild(buttonGroup);

        saveBtn.addEventListener('click', () => this.handleSave(row));
        cancelBtn.addEventListener('click', () => {
          if (row.dataset.isNew === 'true') {
            row.remove();
            this.activeRow = null;
            return;
          }
          this.exitEditMode(row, row.dataset.snapshot);
        });
        deleteBtn.addEventListener('click', () => this.handleDelete(row));
        return;
      }

      const input = buildInput(field, snapshot[field]);
      if (this.datalistMap[field]) {
        input.setAttribute('list', this.datalistMap[field].id);
      }
      cell.innerHTML = '';
      if (field === 'item_code') {
        const wrapper = document.createElement('div');
        wrapper.className = 'd-flex flex-column gap-1';
        wrapper.appendChild(input);
        const feedback = document.createElement('div');
        feedback.className = 'form-text validation-feedback d-none';
        wrapper.appendChild(feedback);
        cell.appendChild(wrapper);
        this.setupItemCodeValidation(row, input, feedback);
      } else if (this.autofillFields.includes(field)) {
        const wrapper = document.createElement('div');
        wrapper.className = 'd-flex flex-column gap-1';
        wrapper.appendChild(input);
        const suggestions = Array.from(this.collectColumnValues(row, field));
        if (suggestions.length) {
          const select = document.createElement('select');
          select.className = 'form-select form-select-sm';
          const placeholderOption = document.createElement('option');
          placeholderOption.value = '';
          placeholderOption.textContent = this.getAutofillPlaceholder(field);
          placeholderOption.disabled = true;
          select.appendChild(placeholderOption);
          const sortedSuggestions = suggestions.sort((a, b) => a.localeCompare(b));
          sortedSuggestions.forEach((value) => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = value;
            select.appendChild(option);
          });
          const existingValue = (input.value || '').trim();
          if (existingValue && sortedSuggestions.includes(existingValue)) {
            select.value = existingValue;
          } else {
            placeholderOption.selected = true;
          }
          select.addEventListener('change', () => {
            input.value = select.value;
            input.dispatchEvent(new Event('input', { bubbles: true }));
          });
          wrapper.appendChild(select);
        }
        cell.appendChild(wrapper);
      } else {
        cell.appendChild(input);
      }
    });

    this.activeRow = row;
    const firstInput = row.querySelector('[data-is-input="true"]');
    if (firstInput) {
      firstInput.focus();
      if (firstInput.select) {
        firstInput.select();
      }
    }
  }

  exitEditMode(row, snapshotJSON) {
    if (!row) {
      return;
    }

    const snapshot = snapshotJSON ? JSON.parse(snapshotJSON) : this.getRowSnapshot(row);

    row.querySelectorAll('[data-field]').forEach((cell) => {
      const field = cell.dataset.field;
      if (field === 'actions') {
        cell.innerHTML = '<button type="button" class="btn btn-sm btn-outline-primary edit-row-btn" title="Edit"><i class="fas fa-edit"></i></button>';
        this.attachRowEvents(row);
        return;
      }
      const value = snapshot[field] ?? '';
      cell.dataset.value = value;
      cell.innerHTML = renderDisplayCell(field, value);
      if (!cell.innerHTML) {
        cell.textContent = value;
      }
    });

    this.normalizeRowDisplay(row);
    row.classList.remove('table-warning');
    delete row.dataset.snapshot;
    this.activeRow = null;
    this.refreshAutofillOptions();
  }

  async handleSave(row) {
    const classificationId = row.dataset.classificationId;
    const isNew = row.dataset.isNew === 'true';
    const originalSnapshot = row.dataset.snapshot ? JSON.parse(row.dataset.snapshot) : {};
    const payload = {};

    row.querySelectorAll('[data-field]').forEach((cell) => {
      const field = cell.dataset.field;
      if (field === 'actions') {
        return;
      }
      const input = cell.querySelector('[data-is-input="true"]');
      if (!input) {
        return;
      }
      let value;
      if (field === 'item_code') {
        value = normalizeItemCode(input.value);
      } else {
        value = input.value.trim();
      }
      const originalValue = field === 'item_code'
        ? normalizeItemCode(originalSnapshot[field] || '')
        : (originalSnapshot[field] || '');
      if (value !== originalValue) {
        payload[field] = value;
      }
    });

    if (!Object.keys(payload).length && !isNew) {
      this.exitEditMode(row, row.dataset.snapshot);
      return;
    }

    const itemInput = row.querySelector('[data-field="item_code"] [data-is-input="true"]');
    if (itemInput) {
      const feedback = itemInput.validationFeedbackEl
        || row.querySelector('[data-field="item_code"] .validation-feedback');
      const requiresValidation = isNew || Object.prototype.hasOwnProperty.call(payload, 'item_code');
      if (requiresValidation) {
        const token = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        itemInput.dataset.validationToken = token;
        const itemCodeValid = await this.runItemCodeValidation(
          row,
          itemInput,
          feedback,
          { skipRemote: false, allowEmpty: false, token },
        );
        if (!itemCodeValid) {
          return;
        }
        if (!Object.prototype.hasOwnProperty.call(payload, 'item_code')) {
          payload.item_code = normalizeItemCode(itemInput.value);
        }
      }
    }

    if (!Object.keys(payload).length && isNew) {
      // No changes and validation already ensured item code state; revert.
      this.exitEditMode(row, row.dataset.snapshot);
      return;
    }

    if (Object.prototype.hasOwnProperty.call(payload, 'item_code')) {
      payload.item_code = normalizeItemCode(payload.item_code);
    }

    const saveButton = row.querySelector('.save-row-btn');
    const cancelButton = row.querySelector('.cancel-row-btn');
    const deleteButton = row.querySelector('.delete-row-btn');
    [saveButton, cancelButton, deleteButton].forEach((btn) => {
      if (btn) btn.disabled = true;
    });

    const originalSaveContent = saveButton ? saveButton.innerHTML : '';
    if (saveButton) {
      saveButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
    }

    try {
      let response;
      if (isNew) {
        const itemCodeValue = normalizeItemCode(
          row.querySelector('[data-field="item_code"] [data-is-input="true"]').value,
        );
        const toteValue = (row.querySelector('[data-field="tote_classification"] [data-is-input="true"]')?.value || '').trim();
        const flushToteValue = (row.querySelector('[data-field="flush_tote"] [data-is-input="true"]')?.value || '').trim();
        const wasteRagValue = (row.querySelector('[data-field="waste_rag"] [data-is-input="true"]')?.value || '').trim();
        const hoseValue = (row.querySelector('[data-field="hose_color"] [data-is-input="true"]')?.value || '').trim();
        const containerValue = (row.querySelector('[data-field="tank_classification"] [data-is-input="true"]')?.value || '').trim();

        response = await createClassification({
          item_code: itemCodeValue,
          tote_classification: toteValue,
          flush_tote: flushToteValue,
          waste_rag: wasteRagValue,
          hose_color: hoseValue,
          tank_classification: containerValue,
        });
      } else {
        response = await saveRow(classificationId, payload);
      }

      const classification = response.classification;
      const snapshot = {
        item_code: normalizeItemCode(classification.item_code || ''),
        tote_classification: classification.tote_classification || '',
        flush_tote: classification.flush_tote || '',
        waste_rag: classification.waste_rag || '',
        hose_color: classification.hose_color || '',
        tank_classification: classification.tank_classification || '',
      };

      this.exitEditMode(row, JSON.stringify(snapshot));
      if (classification.id != null) {
        row.dataset.classificationId = String(classification.id);
      }
      if (isNew) {
        delete row.dataset.isNew;
      }
    } catch (error) {
      console.error(error);
      alert(error.message);
    } finally {
      if (saveButton) {
        saveButton.innerHTML = originalSaveContent;
      }
      [saveButton, cancelButton, deleteButton].forEach((btn) => {
        if (btn) btn.disabled = false;
      });
    }
  }

  async handleAdd() {
    if (!this.tableBody || !this.addButton) {
      return;
    }

    if (this.activeRow) {
      const currentData = this.getRowSnapshot(this.activeRow);
      const identifier = currentData.item_code || `ID ${this.activeRow.dataset.classificationId}`;
      const abandon = window.confirm(`You have unsaved changes on ${identifier}. Abandon them?`);
      if (!abandon) {
        return;
      }
      this.exitEditMode(this.activeRow, JSON.stringify(currentData));
    }

    const originalText = this.addButton.innerHTML;
    this.addButton.disabled = true;
    this.addButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Preparing...';

    try {
      const response = await fetch(NEXT_ID_ENDPOINT, {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
      });

      let data;
      try {
        data = await response.json();
      } catch (error) {
        throw new Error('Unexpected response from the server.');
      }

      if (!response.ok || data.status !== 'success') {
        const message = data.error || 'Unable to prepare container classification.';
        throw new Error(message);
      }

      const template = {
        id: data.next_id,
        item_code: '',
        tote_classification: '',
        flush_tote: '',
        waste_rag: '',
        hose_color: '',
        tank_classification: '',
        isNew: true,
      };

      const row = this.buildRow(template);
      this.tableBody.prepend(row);
      this.attachRowEvents(row);
      this.refreshAutofillOptions();
      this.enterEditMode(row);
    } catch (error) {
      console.error(error);
      alert(error.message);
    } finally {
      this.addButton.disabled = false;
      this.addButton.innerHTML = originalText;
    }
  }

  async handleDelete(row) {
    if (row.dataset.isNew === 'true') {
      row.remove();
      if (this.activeRow === row) {
        this.activeRow = null;
      }
      this.refreshAutofillOptions();
      return;
    }

    const classificationId = row.dataset.classificationId;
    if (!classificationId) {
      return;
    }

    const itemInput = row.querySelector('[data-field="item_code"] [data-is-input="true"]');
    const itemDisplay = itemInput ? itemInput.value.trim() : row.querySelector('[data-field="item_code"]').textContent.trim();
    const label = itemDisplay || `ID ${classificationId}`;

    const confirmDelete = window.confirm(`Delete container classification ${label}? This cannot be undone.`);
    if (!confirmDelete) {
      return;
    }

    const saveButton = row.querySelector('.save-row-btn');
    const cancelButton = row.querySelector('.cancel-row-btn');
    const deleteButton = row.querySelector('.delete-row-btn');

    [saveButton, cancelButton, deleteButton].forEach((btn) => {
      if (btn) btn.disabled = true;
    });

    try {
      const url = new URL(`${API_ENDPOINT_BASE}${classificationId}/delete/`, window.location.origin);
      const response = await fetch(url.toString(), {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({}),
      });

      let data;
      try {
        data = await response.json();
      } catch (error) {
        throw new Error('Unexpected response from the server.');
      }

      if (!response.ok || data.status !== 'success') {
        const message = data.error || 'Unable to delete container classification.';
        throw new Error(message);
      }

      row.remove();
      if (this.activeRow === row) {
        this.activeRow = null;
      }
      this.refreshAutofillOptions();
    } catch (error) {
      console.error(error);
      alert(error.message);
    } finally {
      [saveButton, cancelButton, deleteButton].forEach((btn) => {
        if (btn) btn.disabled = false;
      });
    }
  }

  buildRow(classification) {
    const row = document.createElement('tr');
    row.className = 'filterableRow';
    if (classification.id != null) {
      row.dataset.classificationId = classification.id;
    }
    if (classification.isNew) {
      row.dataset.isNew = 'true';
    }

    row.innerHTML = `
      <td data-field="item_code" class="text-break"></td>
      <td data-field="tote_classification" class="text-break"></td>
      <td data-field="flush_tote" class="text-break"></td>
      <td data-field="waste_rag" class="text-break"></td>
      <td data-field="hose_color" class="text-break"></td>
      <td data-field="tank_classification" class="text-break"></td>
      <td data-field="actions" class="text-center">
        <button type="button" class="btn btn-sm btn-outline-primary edit-row-btn" title="Edit">
          <i class="fas fa-edit"></i>
        </button>
      </td>
    `;

    const assignments = {
      item_code: normalizeItemCode(classification.item_code || ''),
      tote_classification: classification.tote_classification || '',
      flush_tote: classification.flush_tote || '',
      waste_rag: classification.waste_rag || '',
      hose_color: classification.hose_color || '',
      tank_classification: classification.tank_classification || '',
    };

    Object.entries(assignments).forEach(([field, value]) => {
      const cell = row.querySelector(`[data-field="${field}"]`);
      if (!cell) {
        return;
      }
      cell.dataset.value = value;
      if (field === 'tank_classification') {
        cell.innerHTML = renderDisplayCell(field, value);
        if (!cell.innerHTML) {
          cell.textContent = value;
        }
      } else {
        cell.textContent = value;
      }
    });

    return row;
  }

  attachRowEvents(row) {
    const editButton = row.querySelector('.edit-row-btn');
    if (editButton) {
      editButton.addEventListener('click', (event) => this.enterEditMode(event.currentTarget.closest('tr')));
    }
  }
}

function init() {
  document.addEventListener('DOMContentLoaded', () => {
    new ContainerClassificationTable();
  });
}

init();
