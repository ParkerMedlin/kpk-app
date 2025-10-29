import { FilterForm } from '../objects/lookupFormObjects.js';

const API_ENDPOINT_BASE = '/core/api/container-classification/';
const CREATE_ENDPOINT = `${API_ENDPOINT_BASE}create/`;
const NEXT_ID_ENDPOINT = `${API_ENDPOINT_BASE}next-id/`;

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
  const inputType = field === 'tank_classification' ? 'textarea' : 'input';
  const input = document.createElement(inputType);
  input.className = 'form-control form-control-sm';
  if (inputType === 'textarea') {
    input.rows = 3;
  }
  input.value = value ?? '';
  input.dataset.field = field;
  input.dataset.isInput = 'true';
  if (field === 'item_code') {
    input.placeholder = 'ITEMCODE';
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

  const response = await fetch(url.toString(), {
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
    const message = data.error || (data.errors && JSON.stringify(data.errors)) || 'Unable to update container classification.';
    throw new Error(message);
  }

  return data;
}

async function createClassification(payload) {
  const response = await fetch(CREATE_ENDPOINT, {
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

    new FilterForm({
      ignoreSelectors: ['[data-is-input="true"]'],
    });

    this.init();
  }

  init() {
    if (!this.table || !this.tableBody) {
      return;
    }

    this.table.querySelectorAll('.filterableRow').forEach((row) => this.attachRowEvents(row));

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
      data[field] = cell.dataset.value ?? cell.textContent.trim();
    });
    return data;
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
      cell.innerHTML = '';
      cell.appendChild(input);
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

    row.classList.remove('table-warning');
    delete row.dataset.snapshot;
    this.activeRow = null;
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
      const value = input.value.trim();
      const originalValue = originalSnapshot[field] || '';
      if (value !== originalValue) {
        payload[field] = value;
      }
    });

    if (!Object.keys(payload).length) {
      this.exitEditMode(row, row.dataset.snapshot);
      return;
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
        response = await createClassification({
          item_code: payload.item_code ?? row.querySelector('[data-field="item_code"] [data-is-input="true"]').value.trim(),
          tote_classification: payload.tote_classification ?? row.querySelector('[data-field="tote_classification"] [data-is-input="true"]').value.trim(),
          hose_color: payload.hose_color ?? row.querySelector('[data-field="hose_color"] [data-is-input="true"]').value.trim(),
          tank_classification: payload.tank_classification ?? row.querySelector('[data-field="tank_classification"] [data-is-input="true"]').value.trim(),
        });
      } else {
        response = await saveRow(classificationId, payload);
      }

      const classification = response.classification;
      const snapshot = {
        item_code: classification.item_code || '',
        tote_classification: classification.tote_classification || '',
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
      this.attachRowEvents(row);
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
        hose_color: '',
        tank_classification: '',
        isNew: true,
      };

      const row = this.buildRow(template);
      this.tableBody.prepend(row);
      this.attachRowEvents(row);
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
      <td data-field="hose_color" class="text-break"></td>
      <td data-field="tank_classification" class="text-break"></td>
      <td data-field="actions" class="text-center">
        <button type="button" class="btn btn-sm btn-outline-primary edit-row-btn" title="Edit">
          <i class="fas fa-edit"></i>
        </button>
      </td>
    `;

    const assignments = {
      item_code: classification.item_code || '',
      tote_classification: classification.tote_classification || '',
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
