import { FilterForm } from '../objects/lookupFormObjects.js';

const API_ENDPOINT_BASE = '/core/api/purchasing-alias/';
const CREATE_ENDPOINT = `${API_ENDPOINT_BASE}create/`;
const NEXT_ID_ENDPOINT = `${API_ENDPOINT_BASE}next-id/`;

const appContainer = document.getElementById('purchasing-alias-records-app');
const supplyType = appContainer ? appContainer.dataset.supplyType || null : null;
const supplyTypeLabel = appContainer ? appContainer.dataset.supplyTypeLabel || '' : '';
let supplyTypeChoices = [];
let supplyTypeMap = {};
const VENDOR_DATALIST_ID = 'purchasing-alias-vendor-options';

if (appContainer) {
  const choicesId = appContainer.dataset.supplyTypeChoicesId;
  if (choicesId) {
    const choicesNode = document.getElementById(choicesId);
    if (choicesNode) {
      try {
        supplyTypeChoices = JSON.parse(choicesNode.textContent) || [];
      } catch (error) {
        console.warn('Unable to parse supply type choices JSON.', error);
        supplyTypeChoices = [];
      }
    }
  }
}
if (Array.isArray(supplyTypeChoices)) {
  supplyTypeMap = supplyTypeChoices.reduce((acc, entry) => {
    const [value, label] = entry;
    acc[value] = label;
    return acc;
  }, {});
}


const vendorValueStore = (() => {
  let container = appContainer || document.body;
  const values = new Set();
  let datalist = null;

  function ensureContainer() {
    return container || document.body;
  }

  function ensureDatalist() {
    if (datalist) {
      return datalist;
    }
    const existing = document.getElementById(VENDOR_DATALIST_ID);
    if (existing) {
      datalist = existing;
      return datalist;
    }
    datalist = document.createElement('datalist');
    datalist.id = VENDOR_DATALIST_ID;
    ensureContainer().appendChild(datalist);
    return datalist;
  }

  function syncDatalist() {
    const list = ensureDatalist();
    list.innerHTML = '';
    const fragment = document.createDocumentFragment();
    Array.from(values)
      .sort((a, b) => a.localeCompare(b))
      .forEach((value) => {
        const option = document.createElement('option');
        option.value = value;
        fragment.appendChild(option);
      });
    list.appendChild(fragment);
  }

  function add(name) {
    const normalized = (name || '').trim();
    if (!normalized || values.has(normalized)) {
      return;
    }
    values.add(normalized);
    syncDatalist();
  }

  function loadInitialFromTable(table) {
    if (!table) {
      return;
    }
    const names = new Set();
    table.querySelectorAll('tbody [data-field="vendor"]').forEach((cell) => {
      const text = cell.textContent ? cell.textContent.trim() : '';
      if (text) {
        names.add(text);
      }
    });
    if (!names.size) {
      return;
    }
    let mutated = false;
    names.forEach((value) => {
      if (!values.has(value)) {
        values.add(value);
        mutated = true;
      }
    });
    if (mutated) {
      syncDatalist();
    }
  }

  function setContainer(element) {
    container = element || document.body;
    if (datalist && datalist.parentElement !== container) {
      container.appendChild(datalist);
    }
  }

  return {
    ensureDatalist,
    setContainer,
    add,
    loadInitialFromTable,
    get listId() {
      return VENDOR_DATALIST_ID;
    },
  };
})();

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
  if (field === 'supply_type') {
    const select = document.createElement('select');
    select.className = 'form-select form-select-sm';
    select.dataset.field = field;
    select.dataset.isInput = 'true';
    supplyTypeChoices.forEach(([optionValue, optionLabel]) => {
      const option = document.createElement('option');
      option.value = optionValue;
      option.textContent = optionLabel;
      if (optionValue === value) {
        option.selected = true;
      }
      select.appendChild(option);
    });
    return select;
  }

  if (field === 'monthly_audit_needed') {
    const wrapper = document.createElement('div');
    wrapper.className = 'form-check d-flex justify-content-center m-0';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'form-check-input';
    checkbox.checked = Boolean(value);
    checkbox.dataset.field = field;
    checkbox.dataset.isInput = 'true';
    wrapper.appendChild(checkbox);
    return wrapper;
  }
  if (field === 'vendor') {
    const input = document.createElement('input');
    input.className = 'form-control form-control-sm';
    input.value = value ?? '';
    input.dataset.field = field;
    input.dataset.isInput = 'true';
    vendorValueStore.ensureDatalist();
    input.setAttribute('list', vendorValueStore.listId);
    input.setAttribute('autocomplete', 'off');
    if (value) {
      vendorValueStore.add(value);
    }
    return input;
  }

  const input = document.createElement(field === 'vendor_description' || field === 'blending_notes' ? 'textarea' : 'input');
  input.className = 'form-control form-control-sm';
  input.value = value ?? '';
  input.dataset.field = field;
  input.dataset.isInput = 'true';
  if (field === 'vendor_description' || field === 'blending_notes') {
    input.rows = 3;
  }
  return input;
}

function renderDisplayCell(field, value) {
  if (field === 'supply_type') {
    const label = supplyTypeMap[value] || value || '';
    return label ? escapeHtml(label) : '';
  }
  if (field === 'monthly_audit_needed') {
    return value ? '<span class="badge bg-success">Yes</span>' : '<span class="badge bg-secondary">No</span>';
  }
  if (field === 'link') {
    if (!value) {
      return '';
    }
    const escaped = escapeHtml(value);
    return `<a href="${escaped}" class="btn btn-sm btn-outline-primary" target="_blank" rel="noopener" title="${escaped}"><i class="fas fa-link"></i><span class="visually-hidden">Open link</span></a>`;
  }
  return value ? escapeHtml(value) : '';
}

async function saveRow(aliasId, payload, requestConfig = {}) {
  const url = new URL(`${API_ENDPOINT_BASE}${aliasId}/`, window.location.origin);
  if (requestConfig.supplyType) {
    url.searchParams.set('supply_type', requestConfig.supplyType);
  }

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
    const message = data.error || (data.errors && JSON.stringify(data.errors)) || 'Unable to update purchasing alias.';
    throw new Error(message);
  }

  return data;
}

class PurchasingAliasTable {
  constructor() {
    this.activeRow = null;
    this.table = document.getElementById('displayTable');
    this.tableBody = this.table ? this.table.querySelector('tbody') : null;
    this.addButton = document.getElementById('add-alias-btn');
    this.config = {
      supplyType,
      supplyTypeLabel,
      supplyTypeChoices,
    };
    vendorValueStore.setContainer(appContainer || document.body);
    vendorValueStore.ensureDatalist();
    vendorValueStore.loadInitialFromTable(this.table);

    new FilterForm({
      ignoreSelectors: ['[data-is-input="true"]']
    });
    this.init();
  }

  init() {
    if (!this.table) {
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
      if (field === 'supply_type') {
        data[field] = cell.dataset.supplyTypeCode || cell.textContent.trim();
        return;
      }
      if (field === 'monthly_audit_needed') {
        const badge = cell.querySelector('.badge');
        data[field] = badge ? badge.textContent.trim().toLowerCase() === 'yes' : false;
        return;
      }
      data[field] = cell.textContent.trim();
    });
    return data;
  }

  enterEditMode(row) {
    if (!row) {
      return;
    }

    if (this.activeRow && this.activeRow !== row) {
      const currentData = this.getRowSnapshot(this.activeRow);
      const aliasIdentifier = currentData.vendor_part_number || `ID ${this.activeRow.dataset.aliasId}`;
      const abandon = window.confirm(`You have unsaved changes on ${aliasIdentifier}. Abandon them?`);
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
      const value = snapshot[field];
      const input = buildInput(field, value);
      cell.innerHTML = '';
      cell.appendChild(input);
    });

    this.activeRow = row;
    const firstInput = row.querySelector('[data-field] .form-control, [data-field] .form-check-input');
    if (firstInput) {
      firstInput.focus();
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
      const value = snapshot[field];
      if (field === 'supply_type') {
        cell.dataset.supplyTypeCode = value || '';
      }
      cell.innerHTML = renderDisplayCell(field, value);
      if (field === 'vendor') {
        vendorValueStore.add(value);
      }
    });

    row.classList.remove('table-warning');
    delete row.dataset.snapshot;
    this.activeRow = null;
  }

  async handleSave(row) {
    const aliasId = row.dataset.aliasId;
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
      if (input.type === 'checkbox') {
        value = input.checked;
      } else {
        value = input.value.trim();
      }

      const originalValue = originalSnapshot[field];
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
    [saveButton, cancelButton, deleteButton].forEach((btn) => { if (btn) btn.disabled = true; });

    const originalSaveContent = saveButton ? saveButton.innerHTML : '';
    if (saveButton) {
      saveButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
    }

    try {
      let response;
      let resolvedAliasId = aliasId;
      if (isNew && !Object.prototype.hasOwnProperty.call(payload, 'supply_type')) {
        payload.supply_type = this.config.supplyType;
      }
      if (isNew) {
        response = await this.createAlias(payload);
        if (response && response.alias && response.alias.id != null) {
          resolvedAliasId = response.alias.id;
        }
      } else {
        response = await saveRow(aliasId, payload, { supplyType: this.config.supplyType });
        if (response && response.alias && response.alias.id != null) {
          resolvedAliasId = response.alias.id;
        } else if (response && response.alias_id != null) {
          resolvedAliasId = response.alias_id;
        }
      }
      const snapshot = {
        supply_type: response.alias.supply_type,
        blending_notes: response.alias.blending_notes,
        vendor: response.alias.vendor,
        vendor_part_number: response.alias.vendor_part_number,
        vendor_description: response.alias.vendor_description,
        link: response.alias.link,
        monthly_audit_needed: response.alias.monthly_audit_needed,
      };
      const movedOutOfView = Boolean(
        response.alias.supply_type && response.alias.supply_type !== this.config.supplyType
      );

      this.exitEditMode(row, JSON.stringify(snapshot));
      if (resolvedAliasId != null) {
        row.dataset.aliasId = String(resolvedAliasId);
      }
      if (isNew) {
        delete row.dataset.isNew;
      }
      if (movedOutOfView) {
        row.remove();
        this.activeRow = null;
        window.alert('Alias moved to a different supply type and has been removed from this list.');
        return;
      }
      this.attachRowEvents(row);
    } catch (error) {
      console.error(error);
      alert(error.message);
      [saveButton, cancelButton, deleteButton].forEach((btn) => { if (btn) btn.disabled = false; });
      if (saveButton) {
        saveButton.innerHTML = originalSaveContent;
      }
      return;
    }

    if (saveButton) {
      saveButton.innerHTML = originalSaveContent;
    }
    [saveButton, cancelButton, deleteButton].forEach((btn) => { if (btn) btn.disabled = false; });
  }

  async createAlias(payload) {
    const url = new URL(CREATE_ENDPOINT, window.location.origin);
    if (this.config.supplyType) {
      url.searchParams.set('supply_type', this.config.supplyType);
    }
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
      const message = data.error || (data.errors && JSON.stringify(data.errors)) || 'Unable to create purchasing alias.';
      throw new Error(message);
    }

    return data;
  }

  attachRowEvents(row) {
    const editButton = row.querySelector('.edit-row-btn');
    if (editButton) {
      editButton.addEventListener('click', (event) => this.enterEditMode(event.currentTarget.closest('tr')));
    }
  }

  buildRow(alias) {
    const row = document.createElement('tr');
    row.className = 'filterableRow';
    row.dataset.aliasId = alias.id;
    if (alias.isNew) {
      row.dataset.isNew = 'true';
    }

    row.innerHTML = `
      <td data-field="supply_type" data-supply-type-code="${escapeHtml(alias.supply_type || '')}">${renderDisplayCell('supply_type', alias.supply_type || '')}</td>
      <td data-field="blending_notes" class="text-break">${escapeHtml(alias.blending_notes || '')}</td>
      <td data-field="vendor">${escapeHtml(alias.vendor || '')}</td>
      <td data-field="vendor_part_number">${escapeHtml(alias.vendor_part_number || '')}</td>
      <td data-field="vendor_description" class="text-break">${escapeHtml(alias.vendor_description || '')}</td>
      <td data-field="link" class="text-break">${renderDisplayCell('link', alias.link || '')}</td>
      <td data-field="monthly_audit_needed" class="text-center">${renderDisplayCell('monthly_audit_needed', alias.monthly_audit_needed)}</td>
      <td>N/A</td>
      <td class="text-center" data-field="actions">
        <button type="button" class="btn btn-sm btn-outline-primary edit-row-btn" title="Edit">
          <i class="fas fa-edit"></i>
        </button>
      </td>
    `;

    return row;
  }

  async handleAdd() {
    if (!this.tableBody || !this.addButton) {
      return;
    }

    if (this.activeRow) {
      const currentData = this.getRowSnapshot(this.activeRow);
      const identifier = currentData.vendor_part_number || `ID ${this.activeRow.dataset.aliasId}`;
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
        const message = data.error || 'Unable to prepare purchasing alias.';
        throw new Error(message);
      }

      const aliasTemplate = {
        id: data.next_id,
        supply_type: this.config.supplyType,
        vendor: '',
        vendor_part_number: '',
        vendor_description: '',
        link: '',
        blending_notes: '',
        monthly_audit_needed: false,
        isNew: true,
      };

      const row = this.buildRow(aliasTemplate);
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

    const aliasId = row.dataset.aliasId;
    if (!aliasId) {
      return;
    }

    const vendorInput = row.querySelector('[data-field="vendor"] [data-is-input="true"]');
    const vendorDisplay = vendorInput ? vendorInput.value.trim() : row.querySelector('[data-field="vendor"]').textContent.trim();
    const partInput = row.querySelector('[data-field="vendor_part_number"] [data-is-input="true"]');
    const partDisplay = partInput ? partInput.value.trim() : row.querySelector('[data-field="vendor_part_number"]').textContent.trim();
    const label = vendorDisplay || partDisplay || `ID ${aliasId}`;

    const confirmDelete = window.confirm(`Delete purchasing alias ${label}? This cannot be undone.`);
    if (!confirmDelete) {
      return;
    }

    const saveButton = row.querySelector('.save-row-btn');
    const cancelButton = row.querySelector('.cancel-row-btn');
    const deleteButton = row.querySelector('.delete-row-btn');

    [saveButton, cancelButton, deleteButton].forEach((btn) => { if (btn) btn.disabled = true; });

    try {
      const url = new URL(`${API_ENDPOINT_BASE}${aliasId}/delete/`, window.location.origin);
      if (this.config.supplyType) {
        url.searchParams.set('supply_type', this.config.supplyType);
      }
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
        const message = data.error || 'Unable to delete purchasing alias.';
        throw new Error(message);
      }

      row.remove();
      if (this.activeRow === row) {
        this.activeRow = null;
      }
    } catch (error) {
      console.error(error);
      alert(error.message);
      [saveButton, cancelButton, deleteButton].forEach((btn) => { if (btn) btn.disabled = false; });
      return;
    }

    [saveButton, cancelButton, deleteButton].forEach((btn) => { if (btn) btn.disabled = false; });
  }
}

function init() {
  document.addEventListener('DOMContentLoaded', () => {
    new PurchasingAliasTable();
  });
}

init();
