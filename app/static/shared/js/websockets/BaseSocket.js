const DEFAULT_RECONNECT = {
    initialDelay: 1000,
    multiplier: 1.5,
    maxDelay: 10000,
};

function generateClientToken() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
        return crypto.randomUUID();
    }
    return `ws_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
}

export class BaseSocket {
    constructor({
        resolveUrl,
        protocols,
        autoConnect = true,
        heartbeatIntervalMs = 30000,
        reconnect = {},
        parse = JSON.parse,
        serializer = JSON.stringify,
        onOpen,
        onClose,
        onMessage,
        onError,
        onStatusChange,
    } = {}) {
        if (!resolveUrl) {
            throw new Error('BaseSocket requires a resolveUrl function or URL');
        }

        this.resolveUrl = typeof resolveUrl === 'function' ? resolveUrl : () => resolveUrl;
        this.protocols = protocols;
        this.heartbeatIntervalMs = heartbeatIntervalMs;
        this.reconnectConfig = {
            ...DEFAULT_RECONNECT,
            ...reconnect,
        };
        this.parse = parse;
        this.serialize = serializer;
        this.onOpen = onOpen;
        this.onClose = onClose;
        this.onMessage = onMessage;
        this.onError = onError;
        this.onStatusChange = onStatusChange;

        this.senderToken = generateClientToken();
        this._shouldReconnect = autoConnect;
        this._reconnectAttempts = 0;
        this._reconnectTimer = null;
        this._heartbeatTimer = null;
        this._isClosing = false;
        this.socket = null;

        this._boundHandleOpen = this._handleOpen.bind(this);
        this._boundHandleMessage = this._handleMessage.bind(this);
        this._boundHandleClose = this._handleClose.bind(this);
        this._boundHandleError = this._handleError.bind(this);

        if (autoConnect) {
            this.connect();
        }
    }

    connect() {
        const url = this.resolveUrl();
        if (!url) {
            throw new Error('BaseSocket.resolveUrl returned an empty URL');
        }

        this.currentUrl = url;
        this._shouldReconnect = true;
        this._isClosing = false;

        try {
            this.socket = new WebSocket(url, this.protocols);
        } catch (error) {
            this._handleError(error);
            this._scheduleReconnect();
            return;
        }

        this._attachSocketListeners();
        this._updateStatus('connecting');
    }

    disconnect({ code = 1000, reason = 'client closing' } = {}) {
        this._shouldReconnect = false;
        this._isClosing = true;
        this._clearReconnectTimer();
        this._clearHeartbeat();
        if (this.socket && this.socket.readyState <= WebSocket.CLOSING) {
            try {
                this.socket.close(code, reason);
            } catch (error) {
                console.warn('Error closing websocket', error);
            }
        }
    }

    destroy() {
        this.disconnect();
        this.onOpen = null;
        this.onClose = null;
        this.onMessage = null;
        this.onError = null;
        this.onStatusChange = null;
    }

    reconnectNow() {
        this._clearReconnectTimer();
        if (this.socket) {
            try {
                this.socket.close();
            } catch (error) {
                console.warn('Error closing socket before reconnect', error);
            }
        }
        this.connect();
    }

    sendJson(payload, { includeSenderToken = true } = {}) {
        if (!this.socket) {
            throw new Error('WebSocket is not initialized');
        }
        if (this.socket.readyState !== WebSocket.OPEN) {
            throw new Error('WebSocket is not open');
        }

        const withSenderToken = includeSenderToken
            ? { ...payload, senderToken: this.senderToken }
            : payload;

        this.socket.send(this.serialize(withSenderToken));
    }

    sendIfOpen(payload, options) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.sendJson(payload, options);
            return true;
        }
        return false;
    }

    handleMessage() {
        // Override in subclass
    }

    _attachSocketListeners() {
        if (!this.socket) {
            return;
        }
        this.socket.addEventListener('open', this._boundHandleOpen);
        this.socket.addEventListener('message', this._boundHandleMessage);
        this.socket.addEventListener('close', this._boundHandleClose);
        this.socket.addEventListener('error', this._boundHandleError);
    }

    _detachSocketListeners() {
        if (!this.socket) {
            return;
        }
        this.socket.removeEventListener('open', this._boundHandleOpen);
        this.socket.removeEventListener('message', this._boundHandleMessage);
        this.socket.removeEventListener('close', this._boundHandleClose);
        this.socket.removeEventListener('error', this._boundHandleError);
    }

    _handleOpen(event) {
        this._reconnectAttempts = 0;
        this._clearReconnectTimer();
        this._setupHeartbeat();
        this._updateStatus('connected');
        if (typeof this.onOpen === 'function') {
            this.onOpen(event);
        }
    }

    _handleMessage(event) {
        let payload = event.data;
        if (typeof payload === 'string') {
            try {
                payload = this.parse(payload);
            } catch (error) {
                console.warn('Failed to parse WebSocket message', error);
                return;
            }
        }

        if (payload && payload.senderToken && payload.senderToken === this.senderToken) {
            return;
        }

        if (typeof this.onMessage === 'function') {
            this.onMessage(payload, event);
        }

        if (typeof this.handleMessage === 'function') {
            this.handleMessage(payload, event);
        }
    }

    _handleClose(event) {
        this._clearHeartbeat();
        this._detachSocketListeners();

        if (typeof this.onClose === 'function') {
            this.onClose(event);
        }

        if (!this._isClosing && this._shouldReconnect) {
            this._updateStatus('disconnected');
            this._scheduleReconnect();
        } else {
            this._updateStatus('closed');
        }
    }

    _handleError(error) {
        if (typeof this.onError === 'function') {
            this.onError(error);
        } else {
            console.error('WebSocket error', error);
        }
        this._updateStatus('error');
    }

    _setupHeartbeat() {
        this._clearHeartbeat();
        if (!this.heartbeatIntervalMs) {
            return;
        }
        this._heartbeatTimer = setInterval(() => {
            if (!this.socket) {
                return;
            }
            if (this.socket.readyState === WebSocket.OPEN) {
                try {
                    this.socket.send(this.serialize({ action: 'ping', timestamp: Date.now() }));
                } catch (error) {
                    console.warn('Heartbeat ping failed, scheduling reconnect', error);
                    this._scheduleReconnect(true);
                }
            }
        }, this.heartbeatIntervalMs);
    }

    _clearHeartbeat() {
        if (this._heartbeatTimer) {
            clearInterval(this._heartbeatTimer);
            this._heartbeatTimer = null;
        }
    }

    _scheduleReconnect(force = false) {
        if (!this._shouldReconnect && !force) {
            return;
        }

        this._clearReconnectTimer();
        this._reconnectAttempts += 1;
        const delay = Math.min(
            this.reconnectConfig.initialDelay * Math.pow(this.reconnectConfig.multiplier, this._reconnectAttempts - 1),
            this.reconnectConfig.maxDelay,
        );

        this._reconnectTimer = setTimeout(() => {
            if (!this._shouldReconnect) {
                return;
            }
            this.connect();
        }, delay);
    }

    _clearReconnectTimer() {
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
            this._reconnectTimer = null;
        }
    }

    _updateStatus(status) {
        if (typeof this.onStatusChange === 'function') {
            this.onStatusChange(status);
        }
        this.status = status;
    }
}
