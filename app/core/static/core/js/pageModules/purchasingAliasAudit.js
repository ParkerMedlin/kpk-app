const API_ENDPOINT = '/core/api/purchasing-alias-audit/';

function getCsrfFromCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(';').shift();
  }
  return '';
}

function getCsrfToken() {
  const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
  if (csrfInput && csrfInput.value) {
    return csrfInput.value;
  }
  const cookieToken = getCsrfFromCookie('csrftoken');
  if (cookieToken) {
    return cookieToken;
  }
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta) {
    return meta.getAttribute('content');
  }
  const hiddenInput = document.getElementById('csrf-token-value');
  if (hiddenInput) {
    return hiddenInput.value;
  }
  return '';
}

async function markAliasAudited(aliasId, shouldCount) {
  const response = await fetch(API_ENDPOINT, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
      'X-Requested-With': 'XMLHttpRequest',
    },
    body: JSON.stringify({ alias_id: aliasId, is_counted: shouldCount }),
  });

  let data;
  try {
    data = await response.json();
  } catch (error) {
    throw new Error('Unexpected response from the server.');
  }

  if (!response.ok || data.status !== 'success') {
    throw new Error(data.error || 'Unable to update audit status.');
  }

  return data;
}

function updateRowDisplay(row, payload) {
  const lastAuditSpan = row.querySelector('.last-audit-date');
  if (lastAuditSpan) {
    lastAuditSpan.textContent = payload.last_audit_date_formatted || payload.last_audit_date || lastAuditSpan.dataset.defaultLabel || '-';
  }

  const auditCell = row.querySelector('.audit-cell');
  if (auditCell) {
    auditCell.classList.toggle('is-counted', Boolean(payload.counted_this_month));
  }
}

function bindCheckboxes() {
  const container = document.getElementById('purchasing-alias-audit-app');
  if (!container) {
    return;
  }

  const checkboxes = container.querySelectorAll('.audit-checkbox');
  checkboxes.forEach((checkbox) => {
    const initialState = checkbox.dataset.counted === 'true';
    checkbox.checked = initialState;

    const cell = checkbox.closest('td');
    if (cell) {
      cell.classList.add('audit-cell');
      cell.classList.toggle('is-counted', initialState);
    }

    checkbox.addEventListener('change', async (event) => {
      const target = event.currentTarget;
      const aliasId = target.dataset.aliasId;
      const previousState = target.dataset.counted === 'true';
      const shouldCount = target.checked;

      if (!aliasId) {
        alert('Unable to determine which purchasing alias to update.');
        target.checked = previousState;
        return;
      }

      target.disabled = true;
      try {
        const result = await markAliasAudited(aliasId, shouldCount);
        const row = target.closest('tr');
        if (row) {
          updateRowDisplay(row, result);
        }
        target.dataset.counted = result.counted_this_month ? 'true' : 'false';
        target.dataset.lastAuditDate = result.last_audit_date || '';
        target.checked = result.counted_this_month;
      } catch (error) {
        console.error(error);
        alert(error.message);
        target.checked = previousState;
      } finally {
        target.disabled = false;
      }
    });
  });
}

document.addEventListener('DOMContentLoaded', bindCheckboxes);
