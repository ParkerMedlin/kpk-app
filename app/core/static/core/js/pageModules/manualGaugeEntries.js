import { FilterForm } from '../objects/lookupFormObjects.js';

const MEASUREMENT_DECIMALS = 3;
const GALLON_DECIMALS = 2;

function getCsrfToken() {
  const csrfInput = document.querySelector('#manual-gauge-csrf input[name="csrfmiddlewaretoken"]');
  if (csrfInput && csrfInput.value) {
    return csrfInput.value;
  }
  const cookieValue = (`; ${document.cookie}`).split('; csrftoken=');
  if (cookieValue.length === 2) {
    return cookieValue.pop().split(';').shift();
  }
  return '';
}

function formatNumber(value, decimals) {
  if (!Number.isFinite(value)) {
    return '';
  }
  const factor = 10 ** decimals;
  const rounded = Math.round(value * factor) / factor;
  return rounded.toFixed(decimals).replace(/\.?0+$/, '');
}

class ManualGaugeRow {
  constructor(rowElement, app) {
    this.row = rowElement;
    this.app = app;
    this.deadInput = this.row.querySelector('[data-field="dead_space"]');
    this.fullInput = this.row.querySelector('[data-field="full_space"]');
    this.gallonsInput = this.row.querySelector('[data-field="gallons"]');
    this.saveButton = this.row.querySelector('.save-row-btn');
    this.resetButton = this.row.querySelector('.reset-row-btn');
    this.statusNode = this.row.querySelector('.save-status');

    this.maxInches = this._toNumber(rowElement.dataset.maxInches);
    this.gallonsPerInch = this._toNumber(rowElement.dataset.gallonsPerInch);
    this.updateUrl = rowElement.dataset.updateUrl;
    this.csrfToken = getCsrfToken();

    this.savingPromise = null;
    this.isSaving = false;

    this.lastSaved = {
      dead: this._getInputValue(this.deadInput),
      full: this._getInputValue(this.fullInput),
    };

    this.registerEvents();
    this.recalculate();
    this.markDirty();
  }

  registerEvents() {
    if (this.deadInput) {
      this.deadInput.addEventListener('input', () => this.handleInput('dead_space'));
      this.deadInput.addEventListener('blur', () => this.normalizeField(this.deadInput, MEASUREMENT_DECIMALS));
    }
    if (this.fullInput) {
      this.fullInput.addEventListener('input', () => this.handleInput('full_space'));
      this.fullInput.addEventListener('blur', () => this.normalizeField(this.fullInput, MEASUREMENT_DECIMALS));
    }
    if (this.saveButton) {
      this.saveButton.addEventListener('click', () => {
        this.save();
      });
    }
    if (this.resetButton) {
      this.resetButton.addEventListener('click', () => this.reset());
    }
  }

  _toNumber(value) {
    if (value === undefined || value === null || value === '') {
      return null;
    }
    const numberValue = Number(value);
    return Number.isFinite(numberValue) ? numberValue : null;
  }

  _getInputValue(input) {
    if (!input) {
      return '';
    }
    return input.value.trim();
  }

  normalizeField(input, decimals) {
    if (!input) {
      return;
    }
    const numericValue = this._toNumber(input.value);
    if (numericValue === null) {
      input.value = '';
      return;
    }
    input.value = formatNumber(numericValue, decimals);
  }

  handleInput(changedField) {
    this.recalculate(changedField);
    this.markDirty();
  }

  recalculate(changedField = null) {
    const deadValue = this._toNumber(this._getInputValue(this.deadInput));
    const fullValue = this._toNumber(this._getInputValue(this.fullInput));

    if (changedField === 'dead_space') {
      if (deadValue === null) {
        this._setInputValue(this.fullInput, '');
      } else if (this.maxInches !== null) {
        const computedFull = this.maxInches - deadValue;
        if (computedFull >= 0) {
          this._setInputValue(this.fullInput, formatNumber(computedFull, MEASUREMENT_DECIMALS));
        } else {
          this._setInputValue(this.fullInput, '');
          this.setStatus('Dead space exceeds max height.', 'error');
        }
      }
    } else if (changedField === 'full_space') {
      if (fullValue === null) {
        this._setInputValue(this.deadInput, '');
      } else if (this.maxInches !== null) {
        const computedDead = this.maxInches - fullValue;
        if (computedDead >= 0) {
          this._setInputValue(this.deadInput, formatNumber(computedDead, MEASUREMENT_DECIMALS));
        } else {
          this._setInputValue(this.deadInput, '');
          this.setStatus('Full space exceeds max height.', 'error');
        }
      }
    }

    const updatedFull = this._toNumber(this._getInputValue(this.fullInput));
    if (this.gallonsInput) {
      if (updatedFull !== null && this.gallonsPerInch !== null) {
        const gallons = updatedFull * this.gallonsPerInch;
        this._setInputValue(this.gallonsInput, formatNumber(gallons, GALLON_DECIMALS));
      } else {
        this._setInputValue(this.gallonsInput, '');
      }
    }
  }

  _setInputValue(input, value) {
    if (!input) {
      return;
    }
    input.value = value;
  }

  markDirty() {
    const isDirty = this.isDirty();
    this.row.dataset.dirty = isDirty ? 'true' : 'false';
    if (this.statusNode && !this.isSaving) {
      if (!isDirty) {
        this.setStatus('', 'neutral');
      } else if (!this.statusNode.textContent) {
        this.setStatus('Unsaved changes.', 'neutral');
      }
    }
    this.updateButtonStates();
  }

  isDirty() {
    const deadNow = this._getInputValue(this.deadInput);
    const fullNow = this._getInputValue(this.fullInput);
    return deadNow !== this.lastSaved.dead || fullNow !== this.lastSaved.full;
  }

  hasMeasurementValues() {
    const deadValue = this._toNumber(this._getInputValue(this.deadInput));
    const fullValue = this._toNumber(this._getInputValue(this.fullInput));
    return deadValue !== null && fullValue !== null;
  }

  updateButtonStates() {
    const dirty = this.row.dataset.dirty === 'true';
    if (this.saveButton) {
      this.saveButton.disabled = !dirty || this.isSaving;
    }
    if (this.resetButton) {
      this.resetButton.disabled = !dirty || this.isSaving;
    }
  }

  setStatus(message, tone = 'neutral') {
    if (!this.statusNode) {
      return;
    }
    this.statusNode.textContent = message || '';
    this.statusNode.classList.remove('text-success', 'text-danger', 'text-muted');
    if (!message) {
      this.statusNode.classList.add('text-muted');
      return;
    }
    if (tone === 'success') {
      this.statusNode.classList.add('text-success');
    } else if (tone === 'error') {
      this.statusNode.classList.add('text-danger');
    } else {
      this.statusNode.classList.add('text-muted');
    }
  }

  buildPayload() {
    const payload = {};
    const deadValue = this._getInputValue(this.deadInput);
    const fullValue = this._getInputValue(this.fullInput);

    if (deadValue !== this.lastSaved.dead) {
      payload.dead_space = deadValue === '' ? null : deadValue;
    }
    if (fullValue !== this.lastSaved.full) {
      payload.full_space = fullValue === '' ? null : fullValue;
    }

    return Object.keys(payload).length ? payload : null;
  }

  async save(options = {}) {
    if (!this.updateUrl) {
      return null;
    }

    if (this.isSaving) {
      return this.savingPromise;
    }

    const payload = this.buildPayload();
    if (!payload) {
      this.row.dataset.dirty = 'false';
      this.updateButtonStates();
      return null;
    }

    const { keepalive = false, silent = false } = options;

    const requestInit = {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(payload),
    };

    if (keepalive) {
      requestInit.keepalive = true;
    }

    this.isSaving = true;
    this.updateButtonStates();
    if (!silent) {
      this.setStatus('Saving…', 'neutral');
      this.app.setStatus('Saving changes…');
    }

    this.savingPromise = fetch(this.updateUrl, requestInit)
      .then(async (response) => {
        let data;
        try {
          data = await response.json();
        } catch (error) {
          throw new Error('Unexpected response from server.');
        }

        if (!response.ok || data.status !== 'success') {
          throw new Error((data && data.error) || 'Unable to save measurement.');
        }

        this.applyServerValues(data.gauge);
        this.lastSaved = {
          dead: this._getInputValue(this.deadInput),
          full: this._getInputValue(this.fullInput),
        };
        this.row.dataset.dirty = 'false';
        this.updateButtonStates();

        if (!silent) {
          this.setStatus('Saved.', 'success');
          this.app.setStatus('All changes saved.', 'success');
        }

        return data;
      })
      .catch((error) => {
        if (!silent) {
          this.setStatus(error.message, 'error');
          this.app.setStatus(error.message, 'error');
        }
        throw error;
      })
      .finally(() => {
        this.isSaving = false;
        this.updateButtonStates();
      });

    return this.savingPromise;
  }

  applyServerValues(serverGauge) {
    if (!serverGauge) {
      return;
    }

    if (Object.prototype.hasOwnProperty.call(serverGauge, 'dead_space') && this.deadInput) {
      this._setInputValue(
        this.deadInput,
        serverGauge.dead_space != null ? serverGauge.dead_space : ''
      );
    }
    if (Object.prototype.hasOwnProperty.call(serverGauge, 'full_space') && this.fullInput) {
      this._setInputValue(
        this.fullInput,
        serverGauge.full_space != null ? serverGauge.full_space : ''
      );
    }
    if (Object.prototype.hasOwnProperty.call(serverGauge, 'gallons') && this.gallonsInput) {
      this._setInputValue(
        this.gallonsInput,
        serverGauge.gallons != null ? serverGauge.gallons : ''
      );
    }
  }

  reset() {
    if (this.isSaving) {
      return;
    }
    if (this.deadInput) {
      this._setInputValue(this.deadInput, this.lastSaved.dead);
    }
    if (this.fullInput) {
      this._setInputValue(this.fullInput, this.lastSaved.full);
    }
    this.recalculate();
    this.markDirty();
    this.setStatus('Reverted.', 'neutral');
  }
}

class ManualGaugeApp {
  constructor(appElement) {
    this.appElement = appElement;
    this.statusNode = document.getElementById('manual-gauge-status');
    this.rows = Array.from(document.querySelectorAll('.manual-gauge-row')).map(
      (row) => new ManualGaugeRow(row, this)
    );

    const tableId = this.appElement.dataset.tableId || 'manualGaugeTable';
    this.filter = new FilterForm({
      tableSelector: `#${tableId}`,
      rowSelector: 'tr.manual-gauge-row',
      ignoreSelectors: ['input', 'button'],
    });

    this.defaultPrefixes = ['M', 'F', 'N'];
    this.showAllButton = document.getElementById('showAllTanksBtn');
    this.saveAllButton = document.getElementById('saveAllManualGaugesBtn');
    this.showingAll = false;

    this.applyDefaultVisibility();
    this.registerLifecycleEvents();
    this.registerDisplayControls();
    this.registerSaveAllHandler();
  }

  registerLifecycleEvents() {
    window.addEventListener('beforeunload', () => {
      this.autoSave({ keepalive: true, silent: true });
    });

    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        this.autoSave({ keepalive: true, silent: true });
      }
    });
  }

  autoSave(options = {}) {
    this.rows
      .filter((row) => row.isDirty())
      .forEach((row) => {
        row.save(options);
      });
  }

  setStatus(message, tone = 'neutral') {
    if (!this.statusNode) {
      return;
    }
    this.statusNode.textContent = message || '';
    this.statusNode.classList.remove('text-success', 'text-danger', 'text-muted');
    if (!message) {
      this.statusNode.classList.add('text-muted');
      return;
    }
    if (tone === 'success') {
      this.statusNode.classList.add('text-success');
    } else if (tone === 'error') {
      this.statusNode.classList.add('text-danger');
    } else {
      this.statusNode.classList.add('text-muted');
    }
  }

  registerDisplayControls() {
    if (!this.showAllButton) {
      return;
    }

    this.updateShowAllButtonState();

    this.showAllButton.addEventListener('click', () => {
      if (this.showingAll) {
        this.showingAll = false;
        this.applyDefaultVisibility();
      } else {
        this.showingAll = true;
        this.showAllRows();
      }
      this.updateShowAllButtonState();
    });
  }

  applyDefaultVisibility() {
    this.rows.forEach((row) => {
      const label = this.getNormalizedLabel(row.row);
      const shouldShow = this.passesDefaultFilter(label);
      row.row.style.display = shouldShow ? '' : 'none';
      row.row.classList.toggle('chosen', shouldShow);
    });
  }

  showAllRows() {
    this.rows.forEach((row) => {
      row.row.style.display = '';
      row.row.classList.add('chosen');
    });
  }

  updateShowAllButtonState() {
    if (!this.showAllButton) {
      return;
    }
    const label = this.showingAll ? 'Show Only M/F/N' : 'Show All Tanks';
    this.showAllButton.textContent = label;
    this.showAllButton.setAttribute('aria-pressed', this.showingAll ? 'true' : 'false');
  }

  getNormalizedLabel(rowElement) {
    const label =
      rowElement.dataset.tankLabelDisplay ||
      (rowElement.querySelector('[data-field="tank_label"]') || {}).textContent ||
      '';
    return label.trim().toUpperCase();
  }

  registerSaveAllHandler() {
    if (!this.saveAllButton) {
      return;
    }

    this.saveAllButton.addEventListener('click', () => {
      this.handleSaveAll();
    });
  }

  async handleSaveAll() {
    if (!this.saveAllButton) {
      return;
    }

    const candidateRows = this.rows.filter((row) => row.hasMeasurementValues());
    if (!candidateRows.length) {
      this.setStatus('No rows have measurements to save.', 'neutral');
      return;
    }

    this.saveAllButton.disabled = true;
    this.saveAllButton.setAttribute('aria-busy', 'true');
    this.setStatus(
      `Saving ${candidateRows.length} row${candidateRows.length === 1 ? '' : 's'}…`,
      'neutral'
    );

    try {
      const savePromises = candidateRows
        .map((row) => row.save())
        .filter((promise) => promise && typeof promise.then === 'function');

      if (!savePromises.length) {
        this.setStatus('No pending changes on rows with measurements.', 'neutral');
        return;
      }

      const results = await Promise.allSettled(savePromises);
      const failures = results.filter((result) => result.status === 'rejected');

      if (failures.length) {
        this.setStatus(
          `${failures.length} row${failures.length === 1 ? '' : 's'} failed to save.`,
          'error'
        );
      } else {
        this.setStatus('All rows saved.', 'success');
      }
    } finally {
      this.saveAllButton.disabled = false;
      this.saveAllButton.removeAttribute('aria-busy');
    }
  }

  passesDefaultFilter(label) {
    if (!label) {
      return false;
    }
    const firstChar = label.charAt(0);
    if (!this.defaultPrefixes.includes(firstChar)) {
      return false;
    }

    if (label.length === 1) {
      return true;
    }

    const secondChar = label.charAt(1);
    return /[\s\d-]/.test(secondChar);
  }
}

function boot() {
  const appElement = document.getElementById('manual-gauges-app');
  if (!appElement) {
    return;
  }
  // eslint-disable-next-line no-new
  new ManualGaugeApp(appElement);
}

document.addEventListener('DOMContentLoaded', boot);
