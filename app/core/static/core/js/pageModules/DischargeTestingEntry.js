const API_ENDPOINT = '/core/api/discharge-testing/';
const MATERIAL_SEARCH_ENDPOINT = '/core/api/discharge-material-search/';
const PH_CHECK_ENDPOINT = '/core/api/discharge-material-ph-check/';
const ACID_BASE_TYPES = ['Acid', 'Base'];
const PH_EXEMPT_TYPES = ['Oil', 'Polish'];

const DEFAULT_PH_MIN = 5.1;
const DEFAULT_PH_MAX = 10.9;

function normalizeText(value) {
  return (value || '').toString().trim();
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

function isPhInRange(value, minValue, maxValue) {
  return Number.isFinite(value) && value >= minValue && value <= maxValue;
}

function debounce(fn, delay) {
  let timeoutId;
  return (...args) => {
    window.clearTimeout(timeoutId);
    timeoutId = window.setTimeout(() => fn(...args), delay);
  };
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

function showToast(type, title, message, delay = 4000) {
  const toastId = `discharge-testing-entry-toast-${Date.now()}`;
  const bgClass = type === 'success'
    ? 'bg-success'
    : type === 'warning'
      ? 'bg-warning text-dark'
      : type === 'info'
        ? 'bg-info text-dark'
        : 'bg-danger';
  const iconClass = type === 'success'
    ? 'fa-check-circle'
    : type === 'warning'
      ? 'fa-exclamation-triangle'
      : type === 'info'
        ? 'fa-info-circle'
        : 'fa-exclamation-circle';

  document.querySelectorAll('.discharge-testing-entry-toast').forEach((el) => el.remove());

  const toastHtml = `
    <div id="${toastId}" class="toast-container discharge-testing-entry-toast position-fixed top-0 end-0 p-3" style="z-index: 1090;">
      <div class="toast show ${bgClass} text-white" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="toast-header ${bgClass} text-white border-0">
          <i class="fas ${iconClass} me-2"></i>
          <strong class="me-auto">${title}</strong>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">${message}</div>
      </div>
    </div>
  `;

  document.body.insertAdjacentHTML('beforeend', toastHtml);
  const toastElement = document.querySelector(`#${toastId} .toast`);

  const removeToast = () => {
    const container = document.getElementById(toastId);
    if (container) {
      container.remove();
    }
  };

  if (window.bootstrap?.Toast && toastElement) {
    const toast = new window.bootstrap.Toast(toastElement, { delay, autohide: true });
    toast.show();
    toastElement.addEventListener('hidden.bs.toast', removeToast, { once: true });
  } else {
    setTimeout(removeToast, delay);
  }
}

class DischargeTestingEntryPage {
  constructor() {
    this.root = document.getElementById('discharge-testing-entry-app');
    if (!this.root) {
      return;
    }

    this.form = document.getElementById('discharge-testing-entry-form');
    this.submitButton = document.getElementById('discharge-testing-entry-submit');
    this.resetButton = document.getElementById('discharge-testing-entry-reset');

    this.dischargeSource = document.getElementById('discharge-testing-entry-discharge-source');
    this.dischargeType = document.getElementById('discharge-testing-entry-discharge-type');
    this.samplingPersonnel = document.getElementById('discharge-testing-entry-sampling-personnel');
    this.initialPh = document.getElementById('discharge-testing-entry-initial-ph');
    this.finalPh = document.getElementById('discharge-testing-entry-final-ph');
    this.actionRequired = document.getElementById('discharge-testing-entry-action-required');
    this.finalDisposition = document.getElementById('discharge-testing-entry-final-disposition');
    this.dischargeMaterialGroup = this.form
      ? this.form.querySelector('[data-role="discharge-material-group"]')
      : null;
    this.dischargeMaterialInput = document.getElementById('discharge-testing-entry-discharge-material');
    this.dischargeMaterialCode = document.getElementById('discharge-testing-entry-discharge-material-code');
    this.dischargeMaterialResults = document.getElementById('discharge-testing-entry-discharge-material-results');
    this.phAlert = document.getElementById('discharge-testing-entry-ph-alert');
    this.phFieldsGroup = this.form ? this.form.querySelector('[data-role="ph-fields-group"]') : null;
    this.hideMaterialResults();
    this.actionRequiredGroup = this.form
      ? this.form.querySelector('[data-role="action-required-group"]')
      : null;

    this.phMin = Number.parseFloat(this.root.dataset.phMin) || DEFAULT_PH_MIN;
    this.phMax = Number.parseFloat(this.root.dataset.phMax) || DEFAULT_PH_MAX;

    this.isSubmitting = false;
    this.submitButtonHtml = this.submitButton ? this.submitButton.innerHTML : '';

    this.registerEvents();
    this.syncActionRequired();
    this.syncMaterialFieldVisibility();
    this.syncPhFieldsVisibility();
  }

  registerEvents() {
    if (this.form) {
      this.form.addEventListener('submit', (event) => this.handleSubmit(event));
      this.form.addEventListener('reset', () => this.handleReset());
    }

    if (this.initialPh) {
      this.initialPh.addEventListener('input', () => this.handleInitialPhInput());
      this.initialPh.addEventListener('blur', () => this.handleInitialPhInput());
    }

    if (this.finalPh) {
      this.finalPh.addEventListener('input', () => this.handleFinalPhInput());
      this.finalPh.addEventListener('blur', () => this.handleFinalPhInput());
    }

    if (this.dischargeType) {
      this.dischargeType.addEventListener('change', () => {
        this.syncMaterialFieldVisibility();
        this.syncPhFieldsVisibility();
      });
    }

    if (this.dischargeMaterialInput) {
      const debouncedSearch = debounce(() => this.searchMaterials(), 250);
      this.dischargeMaterialInput.addEventListener('input', () => {
        if (this.dischargeMaterialCode) {
          this.dischargeMaterialCode.value = '';
        }
        this.clearFieldFeedback(this.dischargeMaterialInput);
        debouncedSearch();
      });
    }

    if (this.dischargeMaterialResults) {
      this.dischargeMaterialResults.addEventListener('click', (event) => {
        const target = event.target.closest('[data-role="discharge-material-option"]');
        if (!target) {
          return;
        }
        event.preventDefault();
        const value = target.dataset.value || '';
        const label = target.dataset.label || '';
        if (this.dischargeMaterialInput) {
          this.dischargeMaterialInput.value = label;
        }
        if (this.dischargeMaterialCode) {
          this.dischargeMaterialCode.value = value;
        }
        this.clearFieldFeedback(this.dischargeMaterialInput);
        this.checkPhActiveComponent(value);
        this.hideMaterialResults();
      });
    }

    document.addEventListener('click', (event) => {
      if (!this.dischargeMaterialResults) {
        return;
      }
      if (this.dischargeMaterialGroup && this.dischargeMaterialGroup.contains(event.target)) {
        return;
      }
      this.hideMaterialResults();
    });

    [
      this.dischargeSource,
      this.dischargeType,
      this.samplingPersonnel,
      this.actionRequired,
      this.finalDisposition,
      this.dischargeMaterialInput,
    ].forEach((input) => {
      if (!input) {
        return;
      }
      input.addEventListener('input', () => this.clearFieldFeedback(input));
      input.addEventListener('change', () => this.clearFieldFeedback(input));
    });
  }

  clearFieldFeedback(input) {
    if (!input) {
      return;
    }
    input.classList.remove('is-invalid', 'is-valid', 'border-warning');
    const feedback = this.form?.querySelector(`[data-feedback-for="${input.id}"]`);
    if (feedback) {
      feedback.remove();
    }
  }

  setFieldFeedback(input, message, variant = 'error') {
    if (!input) {
      return;
    }
    this.clearFieldFeedback(input);
    if (!message) {
      return;
    }
    const feedback = document.createElement('div');
    feedback.dataset.feedbackFor = input.id || '';

    if (variant === 'success') {
      input.classList.add('is-valid');
      feedback.className = 'valid-feedback';
    } else if (variant === 'warning') {
      input.classList.add('border-warning');
      feedback.className = 'form-text text-warning';
    } else {
      input.classList.add('is-invalid');
      feedback.className = 'invalid-feedback';
    }

    feedback.textContent = message;
    input.insertAdjacentElement('afterend', feedback);
  }

  syncActionRequired() {
    const initialParsed = parsePhValue(this.initialPh ? this.initialPh.value : '');
    const initialValue = initialParsed.error ? null : initialParsed.value;
    const outOfRange = initialValue !== null && !isPhInRange(initialValue, this.phMin, this.phMax);
    if (this.actionRequired) {
      this.actionRequired.required = outOfRange;
      if (outOfRange) {
        this.actionRequired.setAttribute('aria-required', 'true');
      } else {
        this.actionRequired.removeAttribute('aria-required');
      }
    }
  }

  syncMaterialFieldVisibility() {
    if (!this.dischargeMaterialGroup) {
      return;
    }
    const dischargeTypeValue = this.dischargeType ? this.dischargeType.value : '';
    // Material field hidden — kept for potential reactivation
    const shouldShow = false;
    if (!shouldShow) {
      if (this.dischargeMaterialInput) {
        this.dischargeMaterialInput.value = '';
      }
      if (this.dischargeMaterialCode) {
        this.dischargeMaterialCode.value = '';
      }
      this.clearFieldFeedback(this.dischargeMaterialInput);
      this.hideMaterialResults();
      this.hidePhAlert();
    }
  }

  syncPhFieldsVisibility() {
    if (!this.phFieldsGroup) {
      return;
    }
    const dischargeTypeValue = this.dischargeType ? this.dischargeType.value : '';
    const shouldHide = PH_EXEMPT_TYPES.includes(dischargeTypeValue);
    this.phFieldsGroup.style.display = shouldHide ? 'none' : '';

    if (shouldHide) {
      if (this.initialPh) {
        this.initialPh.value = '';
        this.initialPh.required = false;
        this.initialPh.removeAttribute('aria-required');
      }
      if (this.finalPh) {
        this.finalPh.value = '';
      }
      if (this.actionRequired) {
        this.actionRequired.value = '';
        this.actionRequired.required = false;
        this.actionRequired.removeAttribute('aria-required');
      }
      this.clearFieldFeedback(this.initialPh);
      this.clearFieldFeedback(this.finalPh);
      this.clearFieldFeedback(this.actionRequired);
      return;
    }

    if (this.initialPh) {
      this.initialPh.required = true;
      this.initialPh.setAttribute('aria-required', 'true');
    }
    this.syncActionRequired();
  }

  hideMaterialResults() {
    if (!this.dischargeMaterialResults) {
      return;
    }
    this.dischargeMaterialResults.innerHTML = '';
    this.dischargeMaterialResults.style.display = 'none';
  }

  renderMaterialResults(results) {
    if (!this.dischargeMaterialResults) {
      return;
    }
    this.dischargeMaterialResults.innerHTML = '';
    this.dischargeMaterialResults.style.display = 'block';
    this.dischargeMaterialResults.classList.add('list-group', 'mt-1');

    if (!Array.isArray(results) || results.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'list-group-item text-muted';
      empty.textContent = 'No matches';
      this.dischargeMaterialResults.appendChild(empty);
      return;
    }

    results.forEach((result) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'list-group-item list-group-item-action';
      item.dataset.role = 'discharge-material-option';
      item.dataset.value = result.value || '';
      item.dataset.label = result.label || '';
      item.textContent = result.label || result.value || '';
      this.dischargeMaterialResults.appendChild(item);
    });
  }

  showPhAlert(componentCode, componentDesc) {
    if (!this.phAlert) {
      return;
    }
    const desc = normalizeText(componentDesc);
    let message = `pH-affecting material detected: ${componentCode}`;
    if (desc) {
      message = `${message}: ${desc}`;
    }
    this.phAlert.textContent = message;
    this.phAlert.style.display = 'block';
  }

  hidePhAlert() {
    if (!this.phAlert) {
      return;
    }
    this.phAlert.style.display = 'none';
    this.phAlert.textContent = '';
  }

  async checkPhActiveComponent(materialCode) {
    const code = normalizeText(materialCode);
    if (!code) {
      if (typeof this.hidePhAlert === 'function') {
        this.hidePhAlert();
      }
      return;
    }

    try {
      const data = await this.requestJson(
        `${PH_CHECK_ENDPOINT}?code=${encodeURIComponent(code)}`,
        {
          method: 'GET',
          credentials: 'same-origin',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
          },
        },
      );
      const componentCode = normalizeText(data.ph_active_component);
      const componentDesc = normalizeText(data.ph_active_component_desc);
      if (componentCode) {
        if (typeof this.showPhAlert === 'function') {
          this.showPhAlert(componentCode, componentDesc);
        }
      } else if (typeof this.hidePhAlert === 'function') {
        this.hidePhAlert();
      }
    } catch (error) {
      console.error(error);
      if (typeof this.hidePhAlert === 'function') {
        this.hidePhAlert();
      }
    }
  }

  async searchMaterials() {
    if (!this.dischargeMaterialInput) {
      return;
    }
    const term = normalizeText(this.dischargeMaterialInput.value);
    if (term.length < 2) {
      this.hideMaterialResults();
      return;
    }

    try {
      const data = await this.requestJson(
        `${MATERIAL_SEARCH_ENDPOINT}?q=${encodeURIComponent(term)}`,
        {
          method: 'GET',
          credentials: 'same-origin',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
          },
        },
      );
      this.renderMaterialResults(data.results || []);
    } catch (error) {
      console.error(error);
      this.hideMaterialResults();
    }
  }

  handleInitialPhInput() {
    if (!this.initialPh) {
      return;
    }
    const parsed = parsePhValue(this.initialPh.value);

    if (parsed.error) {
      this.setFieldFeedback(this.initialPh, parsed.error, 'error');
      this.syncActionRequired();
      return;
    }

    if (parsed.value === null) {
      this.clearFieldFeedback(this.initialPh);
      this.syncActionRequired();
      return;
    }

    if (!isPhInRange(parsed.value, this.phMin, this.phMax)) {
      this.setFieldFeedback(
        this.initialPh,
        `Initial pH is outside ${this.phMin} - ${this.phMax}. Action is required.`,
        'warning',
      );
    } else {
      this.setFieldFeedback(this.initialPh, '', 'success');
      this.clearFieldFeedback(this.initialPh);
      this.initialPh.classList.add('is-valid');
    }

    this.syncActionRequired();
  }

  handleFinalPhInput() {
    if (!this.finalPh) {
      return;
    }
    const parsed = parsePhValue(this.finalPh.value);
    const initialParsed = parsePhValue(this.initialPh ? this.initialPh.value : '');
    const initialValue = initialParsed.error ? null : initialParsed.value;

    if (parsed.error) {
      this.setFieldFeedback(this.finalPh, parsed.error, 'error');
      return;
    }

    if (parsed.value === null) {
      this.clearFieldFeedback(this.finalPh);
      return;
    }

    if (initialValue === null) {
      this.setFieldFeedback(this.finalPh, 'Initial pH must be recorded before final pH.', 'error');
      return;
    }

    if (!isPhInRange(parsed.value, this.phMin, this.phMax)) {
      this.setFieldFeedback(
        this.finalPh,
        `Final pH must be between ${this.phMin} and ${this.phMax}.`,
        'error',
      );
      return;
    }

    this.clearFieldFeedback(this.finalPh);
    this.finalPh.classList.add('is-valid');
  }

  applyValidationErrors(errors) {
    if (!errors || typeof errors !== 'object') {
      return;
    }
    Object.entries(errors).forEach(([field, message]) => {
      let input = null;
      if (field === 'discharge_source') {
        input = this.dischargeSource;
      } else if (field === 'discharge_type') {
        input = this.dischargeType;
      } else if (field === 'sampling_personnel_id' || field === 'sampling_personnel_name') {
        input = this.samplingPersonnel;
      } else if (field === 'initial_pH') {
        input = this.initialPh;
      } else if (field === 'action_required') {
        input = this.actionRequired;
      } else if (field === 'final_pH') {
        input = this.finalPh;
      } else if (field === 'final_disposition') {
        input = this.finalDisposition;
      } else if (field === 'discharge_material_code') {
        input = this.dischargeMaterialInput;
      }

      if (!input) {
        return;
      }

      const errorMessage = Array.isArray(message) ? message.join(' ') : message;
      this.setFieldFeedback(input, errorMessage, 'error');
    });
  }

  collectPayload() {
    const dischargeSource = normalizeText(this.dischargeSource ? this.dischargeSource.value : '');
    const dischargeType = normalizeText(this.dischargeType ? this.dischargeType.value : '');
    const samplingPersonnelId = normalizeText(this.samplingPersonnel ? this.samplingPersonnel.value : '');
    const samplingPersonnelLabel = normalizeText(
      this.samplingPersonnel?.selectedOptions?.[0]?.textContent,
    );
    const samplingPersonnelName = samplingPersonnelId ? samplingPersonnelLabel : '';
    let actionRequired = normalizeText(this.actionRequired ? this.actionRequired.value : '');
    const finalDisposition = normalizeText(this.finalDisposition ? this.finalDisposition.value : '');
    const dischargeMaterialCode = normalizeText(
      this.dischargeMaterialCode ? this.dischargeMaterialCode.value : '',
    );

    const isOilType = PH_EXEMPT_TYPES.includes(dischargeType);
    let initialParsed = { value: null };
    let finalParsed = { value: null };
    if (!isOilType) {
      initialParsed = parsePhValue(this.initialPh ? this.initialPh.value : '');
      finalParsed = parsePhValue(this.finalPh ? this.finalPh.value : '');
    }

    const errors = {};

    if (!dischargeSource) {
      errors.discharge_source = 'Discharge source is required.';
    }
    if (!dischargeType) {
      errors.discharge_type = 'Discharge type is required.';
    }
    if (!samplingPersonnelId) {
      errors.sampling_personnel_id = 'Sampling personnel is required.';
    }
    if (ACID_BASE_TYPES.includes(dischargeType) && !dischargeMaterialCode) {
      // discharge_material_code validation disabled (fields hidden)
    }

    if (!isOilType) {
      if (initialParsed.error) {
        errors.initial_pH = initialParsed.error;
      } else if (initialParsed.value === null) {
        errors.initial_pH = 'Initial pH is required.';
      }
      if (finalParsed.error) {
        errors.final_pH = finalParsed.error;
      }
    }

    const initialValue = initialParsed.error ? null : initialParsed.value;
    const finalValue = finalParsed.error ? null : finalParsed.value;

    if (!isOilType) {
      if (!finalParsed.error && finalValue !== null && initialValue === null) {
        errors.final_pH = 'Initial pH must be recorded before final pH.';
      }
      const initialOutOfRange =
        initialValue !== null && !isPhInRange(initialValue, this.phMin, this.phMax);

      // action_required validation disabled (field hidden)

      if (finalValue !== null && !isPhInRange(finalValue, this.phMin, this.phMax)) {
        errors.final_pH = `Final pH must be between ${this.phMin} and ${this.phMax}.`;
      }
    } else {
      actionRequired = '';
    }

    if (Object.keys(errors).length > 0) {
      this.applyValidationErrors(errors);
      const firstErrorField = Object.keys(errors)[0];
      const firstInput = {
        discharge_source: this.dischargeSource,
        discharge_type: this.dischargeType,
        sampling_personnel_id: this.samplingPersonnel,
        initial_pH: this.initialPh,
        action_required: this.actionRequired,
        final_pH: this.finalPh,
        final_disposition: this.finalDisposition,
        discharge_material_code: this.dischargeMaterialInput,
      }[firstErrorField];
      if (firstInput && typeof firstInput.focus === 'function') {
        firstInput.focus();
      }
      return null;
    }

    return {
      discharge_source: dischargeSource,
      discharge_type: dischargeType,
      sampling_personnel_id: samplingPersonnelId,
      sampling_personnel_name: samplingPersonnelName,
      initial_pH: initialValue,
      discharge_material_code: dischargeMaterialCode,
      action_required: actionRequired,
      final_pH: finalValue,
      final_disposition: finalDisposition,
    };
  }

  async requestJson(url, options = {}) {
    let response;
    try {
      response = await fetch(url, options);
    } catch (error) {
      throw new Error('Network error. Please try again.');
    }

    let data;
    try {
      data = await response.json();
    } catch (error) {
      throw new Error('Unexpected response from the server.');
    }

    if (!response.ok || data.status === 'error') {
      const error = new Error(extractErrorMessage(data));
      error.payload = data;
      throw error;
    }

    return data;
  }

  setSubmitting(isSubmitting) {
    this.isSubmitting = isSubmitting;
    if (!this.submitButton) {
      return;
    }
    if (isSubmitting) {
      this.submitButton.disabled = true;
      this.submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Submitting...';
    } else {
      this.submitButton.disabled = false;
      this.submitButton.innerHTML = this.submitButtonHtml;
    }
  }

  resetForm() {
    this.clearFieldFeedback(this.dischargeSource);
    this.clearFieldFeedback(this.dischargeType);
    this.clearFieldFeedback(this.samplingPersonnel);
    this.clearFieldFeedback(this.initialPh);
    this.clearFieldFeedback(this.finalPh);
    this.clearFieldFeedback(this.actionRequired);
    this.clearFieldFeedback(this.finalDisposition);
    this.clearFieldFeedback(this.dischargeMaterialInput);
    if (this.dischargeMaterialInput) {
      this.dischargeMaterialInput.value = '';
    }
    if (this.dischargeMaterialCode) {
      this.dischargeMaterialCode.value = '';
    }
    this.hideMaterialResults();
    this.hidePhAlert();
    this.syncActionRequired();
    this.syncMaterialFieldVisibility();
    this.syncPhFieldsVisibility();
    if (this.dischargeSource && typeof this.dischargeSource.focus === 'function') {
      this.dischargeSource.focus();
    }
  }

  handleReset() {
    window.setTimeout(() => this.resetForm(), 0);
  }

  async handleSubmit(event) {
    event.preventDefault();
    if (this.isSubmitting) {
      return;
    }

    if (!this.form) {
      return;
    }

    this.syncActionRequired();
    const payload = this.collectPayload();
    if (!payload) {
      return;
    }

    this.setSubmitting(true);

    try {
      await this.requestJson(API_ENDPOINT, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify(payload),
      });

      showToast('success', 'Discharge Testing Entry', 'Entry saved.');
      if (this.form) {
        this.form.reset();
      } else {
        this.resetForm();
      }
    } catch (error) {
      console.error(error);
      if (error.payload && error.payload.errors) {
        this.applyValidationErrors(error.payload.errors);
      }
      showToast('error', 'Unable to save', error.message || 'Unable to save entry.');
    } finally {
      this.setSubmitting(false);
    }
  }
}

function init() {
  document.addEventListener('DOMContentLoaded', () => {
    new DischargeTestingEntryPage();
  });
}

init();
