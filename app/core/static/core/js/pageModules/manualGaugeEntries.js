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

  getMeasurementDetails() {
    const labelCell = this.row.querySelector('[data-field="tank_label"]');
    return {
      label: labelCell ? labelCell.textContent.trim() : '',
      dead: this._getInputValue(this.deadInput),
      full: this._getInputValue(this.fullInput),
      gallons: this._getInputValue(this.gallonsInput),
    };
  }

  updateButtonStates() {
    const dirty = this.row.dataset.dirty === 'true';
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
    this.shareButton = document.getElementById('shareManualGaugesBtn');
    this.copyButton = document.getElementById('copyManualGaugesBtn');
    this.showingAll = false;

    this.applyDefaultVisibility();
    this.registerLifecycleEvents();
    this.registerDisplayControls();
    this.configureShareOrCopyButtons();
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

  configureShareOrCopyButtons() {
    const canShare = typeof navigator.share === 'function';

    if (canShare) {
      if (this.copyButton) {
        this.copyButton.style.display = 'none';
      }
      if (this.shareButton) {
        this.shareButton.style.display = '';
        this.shareButton.addEventListener('click', () => {
          this.handleShareMeasurements();
        });
      }
    } else {
      if (this.shareButton) {
        this.shareButton.style.display = 'none';
      }
      if (this.copyButton) {
        this.copyButton.style.display = '';
        this.copyButton.addEventListener('click', () => {
          this.handleCopyToClipboard();
        });
      }
    }
  }

  async handleCopyToClipboard() {
    if (!this.copyButton) {
      return;
    }

    const summary = this.buildMeasurementsSummary();
    if (!summary) {
      this.setStatus('No visible rows have measurements to copy.', 'neutral');
      return;
    }

    const { text, count } = summary;
    const saveResult = await this.handleSaveAll({ suppressButtonToggle: true });

    if (saveResult && saveResult.failures) {
      // If some rows failed to save, surface the issue but still allow copying the existing data.
      this.setStatus(
        `${saveResult.failures} row${saveResult.failures === 1 ? '' : 's'} failed to save before copying.`,
        'error'
      );
    }

    this.copyButton.disabled = true;
    this.copyButton.setAttribute('aria-busy', 'true');

    const successMessage = `Copied ${count} measurement${count === 1 ? '' : 's'} to clipboard.`;
    try {
      if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        await navigator.clipboard.writeText(text);
        alert(successMessage);
      } else {
        const fallbackSucceeded = this.fallbackCopy(text);
        if (fallbackSucceeded) {
          alert(successMessage);
        } else {
          this.setStatus(
            'Copy is not supported on this device. The measurements were shown so you can copy manually.',
            'error'
          );
        }
      }
    } catch (error) {
      const fallbackSucceeded = this.fallbackCopy(text);
      if (fallbackSucceeded) {
        this.setStatus(successMessage, 'success');
      } else {
        this.setStatus('Unable to copy measurements on this device.', 'error');
      }
    } finally {
      this.copyButton.disabled = false;
      this.copyButton.removeAttribute('aria-busy');
    }
  }

  buildMeasurementsSummary() {
    const rowsWithValues = this.rows.filter(
      (row) => this.isRowVisible(row) && row.hasMeasurementValues()
    );

    if (!rowsWithValues.length) {
      return null;
    }

    const timestamp = new Date().toLocaleString();
    const lines = rowsWithValues.map((row) => {
      const { label, full } = row.getMeasurementDetails();
      const name = label || 'Tank';
      return `${name} - Full ${full} in`;
    });

    const text = [`Manual Tank Measurements (${timestamp})`, '', ...lines].join('\n');

    return {
      text,
      count: rowsWithValues.length,
    };
  }

  isRowVisible(rowInstance) {
    if (!rowInstance || !rowInstance.row) {
      return false;
    }
    const element = rowInstance.row;
    const hasDisplay = element.offsetParent !== null;
    const hasVisibility =
      element.style.visibility !== 'hidden' && element.style.display !== 'none';
    return hasDisplay && hasVisibility;
  }

  fallbackCopy(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    textarea.style.pointerEvents = 'none';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);

    let succeeded = false;
    try {
      textarea.focus();
      textarea.select();
      succeeded = document.execCommand('copy');
    } catch (error) {
      succeeded = false;
    } finally {
      document.body.removeChild(textarea);
    }

    if (succeeded) {
      return true;
    }

    try {
      window.prompt('Copy these measurements:', text);
      return true;
    } catch (error) {
      return false;
    }
  }

  async handleShareMeasurements() {
    if (!this.shareButton) {
      return;
    }

    if (typeof navigator.share !== 'function') {
      this.setStatus('Sharing is not supported on this device.', 'error');
      return;
    }

    const summary = this.buildMeasurementsSummary();
    if (!summary) {
      this.setStatus('No visible rows have measurements to share.', 'neutral');
      return;
    }

    const { text, count } = summary;
    const saveResult = await this.handleSaveAll({ suppressButtonToggle: true, silent: true });
    const hadSaveFailures = Boolean(saveResult && saveResult.failures);

    if (hadSaveFailures) {
      this.setStatus(
        `${saveResult.failures} row${saveResult.failures === 1 ? '' : 's'} failed to save before sharing.`,
        'error'
      );
    }

    this.shareButton.disabled = true;
    this.shareButton.setAttribute('aria-busy', 'true');

    try {
      await navigator.share({
        title: 'Manual Tank Measurements',
        text,
      });
      if (!hadSaveFailures) {
        this.setStatus(`Shared ${count} measurement${count === 1 ? '' : 's'}.`, 'success');
      }
    } catch (error) {
      if (error && error.name === 'AbortError') {
        this.setStatus('Share cancelled.', 'neutral');
      } else {
        this.setStatus('Unable to open share sheet on this device.', 'error');
      }
    } finally {
      this.shareButton.disabled = false;
      this.shareButton.removeAttribute('aria-busy');
    }
  }

  async handleSaveAll(options = {}) {
    const {
      silent = false,
    } = options;

    const candidateRows = this.rows.filter((row) => row.hasMeasurementValues());
    if (!candidateRows.length) {
      if (!silent) {
        this.setStatus('No rows have measurements to save.', 'neutral');
      }
      return {
        attempted: 0,
        saved: 0,
        failures: 0,
      };
    }

    if (!silent) {
      this.setStatus(
        `Saving ${candidateRows.length} row${candidateRows.length === 1 ? '' : 's'}…`,
        'neutral'
      );
    }

    const savePromises = candidateRows
      .map((row) => row.save())
      .filter((promise) => promise && typeof promise.then === 'function');

    if (!savePromises.length) {
      if (!silent) {
        this.setStatus('No pending changes on rows with measurements.', 'neutral');
      }
      return {
        attempted: candidateRows.length,
        saved: 0,
        failures: 0,
      };
    }

    const results = await Promise.allSettled(savePromises);
    const failures = results.filter((result) => result.status === 'rejected').length;
    const saved = candidateRows.length - failures;

    if (!silent) {
      if (failures) {
        this.setStatus(
          `${failures} row${failures === 1 ? '' : 's'} failed to save.`,
          'error'
        );
      } else {
        this.setStatus('All rows saved.', 'success');
      }
    }

    return {
      attempted: candidateRows.length,
      saved,
      failures,
    };
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
