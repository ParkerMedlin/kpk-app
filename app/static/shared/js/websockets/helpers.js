export function buildWebSocketUrl(path, identifier = '') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const sanitizedPath = path.replace(/^\/+/, '').replace(/\/+$/, '');
    const sanitizedIdentifier = String(identifier || '')
        .replace(/^\/+/, '')
        .replace(/\/+$/, '');

    const fullPath = sanitizedIdentifier
        ? `${sanitizedPath}/${encodeURIComponent(sanitizedIdentifier)}`
        : sanitizedPath;

    return `${protocol}//${host}/${fullPath}/`;
}

export function extractUniqueIdFromUrl(url) {
    if (!url) {
        return null;
    }
    try {
        const parsed = new URL(url, window.location.origin);
        const segments = parsed.pathname.split('/').filter(Boolean);
        return segments.length ? decodeURIComponent(segments[segments.length - 1]) : null;
    } catch (error) {
        console.warn('extractUniqueIdFromUrl failed', error);
        return null;
    }
}

export function sanitizeForJson(value) {
    if (value === undefined) {
        return null;
    }
    if (typeof value === 'function') {
        return value.toString();
    }
    if (Array.isArray(value)) {
        return value.map(sanitizeForJson);
    }
    if (value && typeof value === 'object') {
        return Object.entries(value).reduce((acc, [key, val]) => {
            acc[key] = sanitizeForJson(val);
            return acc;
        }, {});
    }
    return value;
}

export function debounce(fn, wait = 300) {
    let timeoutId;
    return function debounced(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn.apply(this, args), wait);
    };
}

export function safeJsonParse(value, fallback = null) {
    try {
        return JSON.parse(value);
    } catch (error) {
        return fallback;
    }
}

export function updateConnectionIndicator(status, elementId = 'connectionStatusIndicator') {
    const indicator = document.getElementById(elementId);
    if (!indicator) {
        return;
    }

    indicator.className = status;
    const iconSpan = indicator.querySelector('span');
    if (iconSpan) {
        iconSpan.innerHTML = status === 'connected' ? '&#10003;' : '&#10007;';
    }
    const iconHtml = iconSpan ? iconSpan.outerHTML : '';
    const label = status === 'connected' ? 'Connected' : 'Disconnected';
    indicator.innerHTML = `${iconHtml} ${label}`;
}
