export class StateCache {
    constructor(limit = 25) {
        this.limit = limit;
        this.events = [];
        this.state = null;
    }

    loadSnapshot(events = []) {
        if (!Array.isArray(events)) {
            return;
        }
        this.events = events.slice(-this.limit);
    }

    recordEvent(event) {
        if (!event) {
            return;
        }
        this.events.push(event);
        if (this.events.length > this.limit) {
            this.events = this.events.slice(-this.limit);
        }
    }

    setState(state) {
        this.state = state;
    }

    getState() {
        return this.state;
    }

    getEvents() {
        return [...this.events];
    }

    clear() {
        this.events = [];
        this.state = null;
    }
}
