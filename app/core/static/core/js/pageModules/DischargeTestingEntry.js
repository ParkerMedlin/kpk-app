const API_ENDPOINT = '/core/api/discharge-testing/';

const STATUS_LABELS = {
  approved: 'Approved',
  needs_action: 'Needs Action',
  pending: 'Pending',
};

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
    this.flushType = document.getElementById('discharge-testing-entry-flush-type');
    this.linePersonnel = document.getElementById('discharge-testing-entry-line-personnel');
    this.initialPh = document.getElementById('discharge-testing-entry-initial-ph');
    this.finalPh = document.getElementById('discharge-testing-entry-final-ph');
    this.actionRequired = document.getElementById('discharge-testing-entry-action-required');
    this.actionRequiredGroup = this.form
      ? this.form.querySelector('[data-role="action-required-group"]')
      : null;

    this.phMin = Number.parseFloat(this.root.dataset.phMin) || DEFAULT_PH_MIN;
    this.phMax = Number.parseFloat(this.root.dataset.phMax) || DEFAULT_PH_MAX;

    this.isSubmitting = false;
    this.submitButtonHtml = this.submitButton ? this.submitButton.innerHTML : '';

    this.registerEvents();
    this.syncActionRequired();
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

    [
      this.dischargeSource,
      this.flushType,
      this.linePersonnel,
      this.actionRequired,
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
    const actionHasValue = normalizeText(this.actionRequired ? this.actionRequired.value : '') !== '';
    const outOfRange = initialValue !== null && !isPhInRange(initialValue, this.phMin, this.phMax);
    const shouldShow = outOfRange || actionHasValue;

    if (this.actionRequiredGroup) {
      this.actionRequiredGroup.classList.toggle('d-none', !shouldShow);
    }
    if (this.actionRequired) {
      this.actionRequired.required = outOfRange;
      if (outOfRange) {
        this.actionRequired.setAttribute('aria-required', 'true');
      } else {
        this.actionRequired.removeAttribute('aria-required');
      }
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
      } else if (field === 'flush_type') {
        input = this.flushType;
      } else if (field === 'line_personnel_name') {
        input = this.linePersonnel;
      } else if (field === 'initial_pH') {
        input = this.initialPh;
      } else if (field === 'action_required') {
        input = this.actionRequired;
      } else if (field === 'final_pH') {
        input = this.finalPh;
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
    const flushType = normalizeText(this.flushType ? this.flushType.value : '');
    const linePersonnel = normalizeText(this.linePersonnel ? this.linePersonnel.value : '');
    const actionRequired = normalizeText(this.actionRequired ? this.actionRequired.value : '');

    const initialParsed = parsePhValue(this.initialPh ? this.initialPh.value : '');
    const finalParsed = parsePhValue(this.finalPh ? this.finalPh.value : '');

    const errors = {};

    if (!dischargeSource) {
      errors.discharge_source = 'Discharge source is required.';
    }
    if (!flushType) {
      errors.flush_type = 'Flush type is required.';
    }
    if (!linePersonnel) {
      errors.line_personnel_name = 'Line personnel name is required.';
    }

    if (initialParsed.error) {
      errors.initial_pH = initialParsed.error;
    }
    if (finalParsed.error) {
      errors.final_pH = finalParsed.error;
    }

    const initialValue = initialParsed.error ? null : initialParsed.value;
    const finalValue = finalParsed.error ? null : finalParsed.value;

    if (!finalParsed.error && finalValue !== null && initialValue === null) {
      errors.final_pH = 'Initial pH must be recorded before final pH.';
    }
    const initialOutOfRange =
      initialValue !== null && !isPhInRange(initialValue, this.phMin, this.phMax);

    if (initialOutOfRange && !actionRequired) {
      errors.action_required = 'Action details are required when initial pH is out of range.';
    }

    if (finalValue !== null && !isPhInRange(finalValue, this.phMin, this.phMax)) {
      errors.final_pH = `Final pH must be between ${this.phMin} and ${this.phMax}.`;
    }

    if (Object.keys(errors).length > 0) {
      this.applyValidationErrors(errors);
      const firstErrorField = Object.keys(errors)[0];
      const firstInput = {
        discharge_source: this.dischargeSource,
        flush_type: this.flushType,
        line_personnel_name: this.linePersonnel,
        initial_pH: this.initialPh,
        action_required: this.actionRequired,
        final_pH: this.finalPh,
      }[firstErrorField];
      if (firstInput && typeof firstInput.focus === 'function') {
        firstInput.focus();
      }
      return null;
    }

    return {
      discharge_source: dischargeSource,
      flush_type: flushType,
      line_personnel_name: linePersonnel,
      initial_pH: initialValue,
      action_required: actionRequired,
      final_pH: finalValue,
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
    if (this.form) {
      this.form.reset();
    }
    this.clearFieldFeedback(this.dischargeSource);
    this.clearFieldFeedback(this.flushType);
    this.clearFieldFeedback(this.linePersonnel);
    this.clearFieldFeedback(this.initialPh);
    this.clearFieldFeedback(this.finalPh);
    this.clearFieldFeedback(this.actionRequired);
    this.syncActionRequired();
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
      const response = await this.requestJson(API_ENDPOINT, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify(payload),
      });

      const tote = response.tote || {};
      const toastType = status === 'approved' ? 'success' : status === 'needs_action' ? 'warning' : 'info';
      const message = `Entry saved. Status: ${statusLabel}.`;

      showToast(toastType, 'Flush Tote Entry', message);
      this.resetForm();
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
