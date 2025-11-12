import { BaseSocket } from '../../../shared/js/websockets/BaseSocket.js';
import { StateCache } from '../../../shared/js/websockets/StateCache.js';
import { sanitizeForJson } from '../../../shared/js/websockets/helpers.js';

export class PullStatusSocket extends BaseSocket {
    constructor({ prodLine, resolveUrl, onStatusChange, onError, onPullStatusUpdate } = {}) {
        const target = PullStatusSocket._resolveConnectionTarget({ prodLine, resolveUrl });
        super({
            resolveUrl: target.resolveUrl,
            onStatusChange,
            onError: (error) => {
                console.error('PullStatusSocket error:', error);
                if (typeof onError === 'function') {
                    onError(error);
                }
            },
        });

        this.prodLine = target.prodLine;
        this.stateCache = new StateCache();
        this.onPullStatusUpdate = onPullStatusUpdate;

        window.PullStatusSocketInstance = this;
    }

    static _resolveConnectionTarget({ prodLine, resolveUrl } = {}) {
        const resolvedProdLine = (prodLine || '').replace(/\s+/g, '_');
        if (!resolvedProdLine) {
            throw new Error('PullStatusSocket requires a production line identifier');
        }

        if (typeof resolveUrl === 'function') {
            return {
                prodLine: resolvedProdLine,
                resolveUrl,
            };
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const encodedProdLine = encodeURIComponent(resolvedProdLine);
        return {
            prodLine: resolvedProdLine,
            resolveUrl: () =>
                `${protocol}//${host}/ws/pull-status/${encodedProdLine}/`,
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

        if (payload.type !== 'pull_status_update') {
            return;
        }

        this._recordEvent(payload);
        this._notifyUpdate(payload);
    }

    toggleItem(itemCode, isPulled) {
        if (!itemCode) {
            throw new Error('PullStatusSocket.toggleItem requires an itemCode');
        }
        return this.sendIfOpen({
            itemCode,
            isPulled: Boolean(isPulled),
        });
    }

    _applyInitialState(events = []) {
        if (!Array.isArray(events) || events.length === 0) {
            return;
        }
        this.stateCache.loadSnapshot(events);
        events.forEach((entry) => {
            if (!entry || entry.event !== 'pull_status_update' || !entry.data) {
                return;
            }
            this._notifyUpdate({
                type: entry.event,
                ...entry.data,
            });
        });
    }

    _recordEvent(payload) {
        this.stateCache.recordEvent({
            event: payload.type,
            data: sanitizeForJson({
                itemCode: payload.itemCode,
                isPulled: payload.isPulled,
            }),
        });
    }

    _notifyUpdate(payload) {
        if (typeof this.onPullStatusUpdate === 'function') {
            this.onPullStatusUpdate(payload);
        }
    }
}
