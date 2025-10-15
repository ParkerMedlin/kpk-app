import { BaseSocket } from '../../../shared/js/websockets/BaseSocket.js';
import { StateCache } from '../../../shared/js/websockets/StateCache.js';
import { sanitizeForJson } from '../../../shared/js/websockets/helpers.js';

export class SpecSheetSocket extends BaseSocket {
    constructor({
        specId,
        resolveUrl,
        onStatusChange,
        onError,
        onSpecSheetUpdate,
        onInitialState,
    } = {}) {
        const target = SpecSheetSocket._resolveConnectionTarget({ specId, resolveUrl });
        super({
            resolveUrl: target.resolveUrl,
            onStatusChange,
            onError: (error) => {
                console.error('SpecSheetSocket error:', error);
                if (typeof onError === 'function') {
                    onError(error);
                }
            },
        });

        this.specId = target.specId;
        this.stateCache = new StateCache(5);
        this.onSpecSheetUpdate = onSpecSheetUpdate;
        this.onInitialState = onInitialState;

        window.SpecSheetSocketInstance = this;
    }

    static _resolveConnectionTarget({ specId, resolveUrl } = {}) {
        const resolvedSpecId = (specId || '').trim();
        if (!resolvedSpecId) {
            throw new Error('SpecSheetSocket requires a specId');
        }

        if (typeof resolveUrl === 'function') {
            return {
                specId: resolvedSpecId,
                resolveUrl,
            };
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return {
            specId: resolvedSpecId,
            resolveUrl: () =>
                `${protocol}//${host}/ws/spec_sheet/${encodeURIComponent(resolvedSpecId)}/`,
        };
    }

    handleMessage(payload) {
        if (!payload || typeof payload !== 'object') {
            return;
        }

        if (payload.type === 'initial_state') {
            this._applyInitialState(payload.events);
            return;
        }

        if (payload.type !== 'spec_sheet_update') {
            return;
        }

        const sanitized = this._recordState(payload.state);
        this._notifyUpdate(sanitized);
    }

    broadcastState(state) {
        const sanitized = this._recordState(state);
        return this.sendIfOpen({ state: sanitized });
    }

    getCurrentState() {
        return this.stateCache.getState();
    }

    _applyInitialState(events = []) {
        if (!Array.isArray(events) || events.length === 0) {
            return;
        }
        this.stateCache.loadSnapshot(events);
        const latest = events[events.length - 1];
        if (!latest || !latest.data) {
            return;
        }
        const sanitized = sanitizeForJson(latest.data);
        this.stateCache.setState(sanitized);
        this._notifyInitialState(sanitized);
    }

    _recordState(state) {
        const sanitized = sanitizeForJson(state || {});
        this.stateCache.recordEvent({
            event: 'spec_sheet_update',
            data: sanitized,
        });
        this.stateCache.setState(sanitized);
        return sanitized;
    }

    _notifyUpdate(state) {
        if (typeof this.onSpecSheetUpdate === 'function') {
            this.onSpecSheetUpdate(state);
        }
    }

    _notifyInitialState(state) {
        if (typeof this.onInitialState === 'function') {
            this.onInitialState(state);
        } else if (typeof this.onSpecSheetUpdate === 'function') {
            this.onSpecSheetUpdate(state);
        }
    }
}
