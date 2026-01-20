const API_BASE = '/core/api/flush-totes/';

const STATUS_LABELS = {
  approved: 'Approved',
  needs_action: 'Needs Action',
  pending: 'Pending',
};

const STATUS_CLASSES = {
  approved: 'bg-success',
  needs_action: 'bg-warning text-dark',
  pending: 'bg-secondary',
};

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

function buildStatusBadge(status) {
  const label = STATUS_LABELS[status] || 'Pending';
  const classes = STATUS_CLASSES[status] || STATUS_CLASSES.pending;
  return `<span class="badge ${classes} text-uppercase">${escapeHtml(label)}</span>`;
}

class FlushTotesPage {
  constructor() {
    this.root = document.getElementById('flush-totes-app');
    if (!this.root) {
      return;
    }
    this.table = document.getElementById('flush-tote-table');
    this.tableBody = this.table ? this.table.querySelector('tbody') : null;
    this.createForm = document.getElementById('flush-tote-create-form');
    this.createButton = document.getElementById('flush-tote-create-btn');
    this.productionLineSelect = document.getElementById('flush-tote-production-line');
    this.flushTypeSelect = document.getElementById('flush-tote-flush-type');
    this.connectionBanner = document.getElementById('flush-tote-connection-banner');

    this.isLineRole = this.root.dataset.roleLine === 'true';
    this.isLabRole = this.root.dataset.roleLab === 'true';
    this.canEdit = this.isLineRole || this.isLabRole;

    this.optionSets = {
      production_line: this.extractSelectOptions(this.productionLineSelect),
      flush_type: this.extractSelectOptions(this.flushTypeSelect),
    };

    this.activeRow = null;

    this.init();
  }

  init() {
    this.setupConnectionBanner();

    if (this.tableBody) {
      this.tableBody.querySelectorAll('tr.flush-tote-row').forEach((row) => {
        this.normalizeRowTimestamps(row);
        this.attachRowEvents(row);
      });
    }

    if (this.createForm) {
      this.createForm.addEventListener('submit', (event) => this.handleCreate(event));
    }
  }

  setupConnectionBanner() {
    if (!this.connectionBanner) {
      return;
    }
    const toggle = () => {
      if (navigator.onLine) {
        this.setConnectionBanner(false);
      } else {
        this.setConnectionBanner(true);
      }
    };
    window.addEventListener('offline', () => this.setConnectionBanner(true));
    window.addEventListener('online', () => this.setConnectionBanner(false));
    toggle();
  }

  setConnectionBanner(show) {
    if (!this.connectionBanner) {
      return;
    }
    if (show) {
      this.connectionBanner.classList.remove('d-none');
    } else {
      this.connectionBanner.classList.add('d-none');
    }
  }

  extractSelectOptions(selectEl) {
    if (!selectEl) {
      return [];
    }
    return Array.from(selectEl.options).map((option) => ({
      value: option.value,
      label: option.textContent,
    }));
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
      status: row.dataset.status || 'pending',
      initial_updated_at: row.dataset.initialUpdatedAt || '',
      final_updated_at: row.dataset.finalUpdatedAt || '',
    };
    row.querySelectorAll('[data-field]').forEach((cell) => {
      const field = cell.dataset.field;
      if (!field || field === 'actions') {
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

  createSelect(field, value) {
    const select = document.createElement('select');
    select.className = 'form-select form-select-sm';
    select.dataset.field = field;
    select.dataset.isInput = 'true';

    const options = [...(this.optionSets[field] || [])];
    const valueSet = new Set(options.map((option) => option.value));
    if (value && !valueSet.has(value)) {
      options.unshift({ value, label: value });
    }

    options.forEach((option) => {
      const optionEl = document.createElement('option');
      optionEl.value = option.value;
      optionEl.textContent = option.label;
      select.appendChild(optionEl);
    });

    select.value = value || '';
    return select;
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

  enterEditMode(row) {
    if (!this.canEdit || !row) {
      return;
    }

    if (this.activeRow && this.activeRow !== row) {
      const currentData = this.getRowSnapshot(this.activeRow);
      const identifier = currentData.flush_type || `ID ${this.activeRow.dataset.toteId}`;
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
      if (!field || field === 'date' || field === 'approval_status' || field === 'line_personnel_name' || field === 'lab_technician_name') {
        return;
      }

      const editGroup = cell.dataset.editGroup;
      const canEditField =
        (editGroup === 'line' && this.isLineRole) ||
        (editGroup === 'lab' && this.isLabRole);

      if (!canEditField) {
        return;
      }

      const currentValue = cell.dataset.value ?? '';
      let input;
      if (field === 'production_line' || field === 'flush_type') {
        input = this.createSelect(field, currentValue);
      } else if (field === 'action_required') {
        input = this.createTextarea(field, currentValue);
      } else {
        input = this.createTextInput(field, currentValue, {
          type: 'number',
          step: '0.01',
          inputMode: 'decimal',
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
      this.setConnectionBanner(true);
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

    this.setConnectionBanner(false);
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

    if (this.isLineRole) {
      const lineSelect = row.querySelector('[data-field="production_line"] [data-is-input="true"]');
      const flushSelect = row.querySelector('[data-field="flush_type"] [data-is-input="true"]');

      if (lineSelect) {
        const value = normalizeText(lineSelect.value);
        if (value !== normalizeText(snapshot.production_line)) {
          payload.production_line = value;
          updatedFields.push('production_line');
        }
      }
      if (flushSelect) {
        const value = normalizeText(flushSelect.value);
        if (value !== normalizeText(snapshot.flush_type)) {
          payload.flush_type = value;
          updatedFields.push('flush_type');
        }
      }
    }

    let initialParsed = { value: null };
    let finalParsed = { value: null };

    if (this.isLabRole) {
      const initialInput = row.querySelector('[data-field="initial_pH"] [data-is-input="true"]');
      const actionInput = row.querySelector('[data-field="action_required"] [data-is-input="true"]');
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
        throw new Error('Unable to determine which flush tote to update.');
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

  async handleCreate(event) {
    event.preventDefault();
    if (!this.createButton) {
      return;
    }

    const productionLine = this.productionLineSelect ? this.productionLineSelect.value : '';
    const flushType = this.flushTypeSelect ? this.flushTypeSelect.value : '';

    if (!productionLine || !flushType) {
      alert('Production line and flush type are required.');
      return;
    }

    const originalHtml = this.createButton.innerHTML;
    this.createButton.disabled = true;
    this.createButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Creating...';

    try {
      const response = await this.requestJson(API_BASE, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({
          production_line: productionLine,
          flush_type: flushType,
        }),
      });

      const tote = response.tote || {};
      this.insertRow(tote);
      if (this.productionLineSelect) {
        this.productionLineSelect.value = '';
      }
      if (this.flushTypeSelect) {
        this.flushTypeSelect.value = '';
      }
    } catch (error) {
      console.error(error);
      alert(error.message);
    } finally {
      this.createButton.disabled = false;
      this.createButton.innerHTML = originalHtml;
    }
  }

  insertRow(tote) {
    if (!this.tableBody) {
      return;
    }
    const placeholder = this.tableBody.querySelector('tr:not(.flush-tote-row)');
    if (placeholder && placeholder.querySelector('td[colspan]')) {
      placeholder.remove();
    }
    const row = this.buildRow(tote);
    this.tableBody.prepend(row);
    this.attachRowEvents(row);
  }

  buildRow(tote) {
    const row = document.createElement('tr');
    row.className = 'flush-tote-row';
    row.innerHTML = `
      <td data-field="date"><div class="fw-semibold"></div></td>
      <td data-field="production_line" data-edit-group="line"></td>
      <td data-field="flush_type" data-edit-group="line"></td>
      <td data-field="initial_pH" data-edit-group="lab"></td>
      <td data-field="action_required" data-edit-group="lab" class="text-break"></td>
      <td data-field="final_pH" data-edit-group="lab"></td>
      <td data-field="approval_status"></td>
      <td data-field="line_personnel_name"></td>
      <td data-field="lab_technician_name"></td>
      <td data-field="actions" class="text-center"></td>
    `;

    this.applyRowData(row, tote, { initialize: true });
    return row;
  }

  applyRowData(row, tote, options = {}) {
    const data = {
      id: tote.id ?? row.dataset.toteId ?? null,
      date: tote.date ?? row.querySelector('[data-field="date"]')?.dataset?.value ?? '',
      production_line: tote.production_line ?? '',
      flush_type: tote.flush_type ?? '',
      initial_pH: tote.initial_pH ?? '',
      action_required: tote.action_required ?? '',
      final_pH: tote.final_pH ?? '',
      approval_status: tote.approval_status ?? row.dataset.status ?? 'pending',
      line_personnel_name: tote.line_personnel_name ?? '',
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
    row.dataset.status = data.approval_status;
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

    this.setTextCell(row, 'production_line', data.production_line);
    this.setTextCell(row, 'flush_type', data.flush_type);

    this.setPhCell(row, 'initial_pH', data.initial_pH, data.lab_technician_name, initialUpdatedAt, 'initial');
    this.setTextCell(row, 'action_required', data.action_required, true);
    this.setPhCell(row, 'final_pH', data.final_pH, data.lab_technician_name, finalUpdatedAt, 'final');

    const statusCell = row.querySelector('[data-field="approval_status"]');
    if (statusCell) {
      statusCell.dataset.value = data.approval_status;
      statusCell.innerHTML = buildStatusBadge(data.approval_status);
    }

    this.setTextCell(row, 'line_personnel_name', data.line_personnel_name);
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
}

function init() {
  document.addEventListener('DOMContentLoaded', () => {
    new FlushTotesPage();
  });
}

init();
