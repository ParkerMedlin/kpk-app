import { BaseSocket } from '../../../shared/js/websockets/BaseSocket.js';
import { StateCache } from '../../../shared/js/websockets/StateCache.js';
import {
    buildWebSocketUrl,
    sanitizeForJson,
    updateConnectionIndicator,
} from '../../../shared/js/websockets/helpers.js';
import { fetchLotRecordRow } from './lotNumbers/lotNumberFunctions.js';

const STATE_EVENT_LIMIT = 50;

function updateConnectionStatus(status) {
    const normalized =
        status === 'connected' ? 'connected' : status === 'connecting' ? 'connecting' : 'disconnected';
    updateConnectionIndicator(normalized);
}

export class BlendScheduleSocket extends BaseSocket {
    constructor(options = {}) {
        const scheduleContext = BlendScheduleSocket._resolveContext(options.context);
        const resolveUrl =
            typeof options.resolveUrl === 'function'
                ? options.resolveUrl
                : () => buildWebSocketUrl('ws/blend_schedule', scheduleContext);

        super({
            resolveUrl,
            heartbeatIntervalMs: options.heartbeatIntervalMs ?? 30000,
            reconnect: options.reconnect,
            onStatusChange: (status) => {
                updateConnectionStatus(status);
                if (typeof options.onStatusChange === 'function') {
                    options.onStatusChange(status);
                }
                if (status === 'connected') {
                    this.reconnectAttempts = 0;
                }
            },
            onError: (error) => {
                console.error('BlendScheduleSocket error:', error);
                updateConnectionStatus('disconnected');
                if (typeof options.onError === 'function') {
                    options.onError(error);
                }
            },
        });

        this.scheduleContext = scheduleContext;
        this.options = options;
        this.stateCache = new StateCache(STATE_EVENT_LIMIT);
        this.isNavigating = false;
        this.isDragging = false;
        this.rowTemplateCache = {};
        this.reconnectAttempts = 0;

        this.setupNavigationDetection();

        window.blendScheduleSocket = this;
        window.blendScheduleWS = this;
    }

    static _resolveContext(context) {
        if (context && context !== 'undefined') {
            return context;
        }
        return BlendScheduleSocket._detectContextFromUrl(window.location.href);
    }

    static _detectContextFromUrl(url) {
        if (!url) {
            return 'all';
        }
        if (url.includes('blend-area=Desk_1')) return 'Desk_1';
        if (url.includes('blend-area=Desk_2')) return 'Desk_2';
        if (url.includes('blend-area=LET_Desk')) return 'LET_Desk';
        if (url.includes('blend-area=Hx')) return 'Hx';
        if (url.includes('blend-area=Dm')) return 'Dm';
        if (url.includes('blend-area=Totes')) return 'Totes';
        if (url.includes('blend-area=Pails')) return 'Pails';
        if (url.includes('blend-area=all')) return 'all';
        if (url.includes('/drumschedule') || url.includes('drum')) return 'Dm';
        if (url.includes('/horixschedule') || url.includes('horix')) return 'Hx';
        if (url.includes('/deskoneschedule') || (url.includes('desk') && url.includes('one'))) return 'Desk_1';
        if (url.includes('/desktwoschedule') || (url.includes('desk') && url.includes('two'))) return 'Desk_2';
        if (url.includes('/toteschedule') || url.includes('tote')) return 'Totes';
        if (url.includes('/allschedules') || url.includes('all')) return 'all';
        return 'all';
    }

    setupNavigationDetection() {
        // Detect when user is navigating away from page
        window.addEventListener('beforeunload', () => {
            this.isNavigating = true;
        });
        
        // Detect when page is being hidden (tab switch, navigation, etc.)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.isNavigating = true;
            } else {
                // Re-enable after a short delay when page becomes visible again
                setTimeout(() => {
                    this.isNavigating = false;
                }, 1000);
            }
        });
        
        // Detect page load completion to re-enable processing
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                setTimeout(() => {
                    this.isNavigating = false;
                }, 2000); // Give page time to fully load
            });
        } else {
            // Page already loaded
            setTimeout(() => {
                this.isNavigating = false;
            }, 1000);
        }
    }

    _findTemplateRow(tableBody, excludeBlendId) {
        const areaKey = this._getTableAreaKey(tableBody);
        const rows = Array.from(tableBody.querySelectorAll('tr[data-blend-id]')).filter((row) => {
            const rowId = row.getAttribute('data-blend-id');
            return rowId !== String(excludeBlendId);
        });

        const candidateRows = rows.filter((row) => this._isTemplateCandidateRow(row));

        if (candidateRows.length) {
            const actionRow = candidateRows.find((row) => row.querySelector('.generate-excel-macro-trigger'));
            if (actionRow) {
                this._cacheTemplateRow(areaKey, actionRow);
                return actionRow;
            }

            const dropdownRow = candidateRows.find((row) => row.querySelector('.lot-number-cell .dropdown'));
            if (dropdownRow) {
                this._cacheTemplateRow(areaKey, dropdownRow);
                return dropdownRow;
            }

            this._cacheTemplateRow(areaKey, candidateRows[0]);
            return candidateRows[0];
        }

        const cachedTemplate = this._getCachedTemplateRow(areaKey);
        if (cachedTemplate) {
            return cachedTemplate;
        }

        const globalTemplate = this._getGlobalTemplateRow(areaKey, excludeBlendId);
        if (globalTemplate) {
            return globalTemplate;
        }

        const anyStoredTemplate = this._getAnyCachedTemplateRow();
        if (anyStoredTemplate) {
            return anyStoredTemplate;
        }

        return rows[0] || null;
    }

    _ensureEditLotButton(row, lotRecordId) {
        const editLotButton = row?.querySelector('.editLotButton');
        if (!editLotButton) {
            return;
        }

        if (lotRecordId) {
            editLotButton.dataset.lotId = lotRecordId;
        } else {
            delete editLotButton.dataset.lotId;
            return;
        }

        if (editLotButton.dataset.editLotBound === 'true' || editLotButton.dataset.editLotBound === 'pending') {
            return;
        }

        editLotButton.dataset.editLotBound = 'pending';
        import('../objects/buttonObjects.js')
            .then(({ EditLotNumButton }) => {
                new EditLotNumButton(editLotButton);
                editLotButton.dataset.editLotBound = 'true';
            })
            .catch((error) => {
                console.error('Failed to initialize EditLotNumButton:', error);
                delete editLotButton.dataset.editLotBound;
            });
    }

    handleMessage(message) {
        if (!message || typeof message !== 'object') {
            return;
        }

        if (message.type === 'initial_state') {
            this._handleInitialReplay(message.events);
            return;
        }

        if (message.type === 'pong') {
            return;
        }

        if (message.type !== 'blend_schedule_update') {
            console.warn('Unknown message type:', message.type);
            return;
        }

        // Skip processing if page is navigating to prevent duplicates
        if (this.isNavigating) {
            return;
        }

        const updateType = message.update_type;
        const updateData = message.data || {};

        this._recordEvent(updateType, updateData);
        this._applyUpdate(updateType, updateData);
    }

    _handleInitialReplay(events = []) {
        if (!Array.isArray(events) || events.length === 0) {
            return;
        }

        this.stateCache.loadSnapshot(events);
        for (const entry of events) {
            if (!entry || typeof entry !== 'object') {
                continue;
            }
            this._applyUpdate(entry.event, entry.data || {});
        }
    }

    _recordEvent(updateType, updateData) {
        if (!this.stateCache || !updateType) {
            return;
        }
        const sanitized = sanitizeForJson(updateData || {});
        this.stateCache.recordEvent({
            event: updateType,
            data: sanitized,
        });
    }

    _applyUpdate(updateType, updateData) {
        if (!updateType) {
            return;
        }

        // 🎯 ENHANCED: Page-aware filtering with special handling for "all schedules" page
        const currentPageArea = this.getCurrentPageArea();
        const isLotRecordsPage = this.isLotRecordsPage();

        // Lot numbers page does not have reorder context; skip those events entirely
        if (isLotRecordsPage && updateType === 'schedule_reordered') {
            return;
        }

        let shouldProcess = false;

        if (isLotRecordsPage) {
            // Lot records view needs updates for every blend area
            shouldProcess = updateType !== 'schedule_reordered';
        } else if (currentPageArea === 'all') {
            // On "all schedules" page, process updates for desk areas only
            // (Desk_1, Desk_2, LET_Desk) but not other areas like Hx, Dm, Totes
            const deskAreas = ['Desk_1', 'Desk_2', 'LET_Desk'];

            if (updateType === 'blend_moved') {
                const oldArea = updateData.old_blend_area;
                const newArea = updateData.new_blend_area;
                shouldProcess = deskAreas.includes(oldArea) || deskAreas.includes(newArea);
            } else {
                const updateBlendArea = updateData.blend_area || updateData.new_blend_area;
                shouldProcess = deskAreas.includes(updateBlendArea);
            }
        } else if (updateType === 'blend_moved') {
            // For blend_moved, check both old and new areas
            const oldArea = updateData.old_blend_area;
            const newArea = updateData.new_blend_area;
            shouldProcess = currentPageArea === oldArea || currentPageArea === newArea;
        } else {
            // For other message types, use the standard blend_area
            const updateBlendArea = updateData.blend_area || updateData.new_blend_area;
            shouldProcess = currentPageArea === updateBlendArea;
        }

        if (!shouldProcess) {
            return;
        }

        switch (updateType) {
            case 'blend_status_changed':
                this.updateBlendStatus(updateData);
                break;
            case 'lot_updated':
                this.updateLotInfo(updateData);
                break;
            case 'blend_deleted':
                this.removeBlend(updateData);
                break;
            case 'new_blend_added':
                this.addBlend(updateData);
                break;
            case 'blend_moved':
                // Extra protection against duplicates during navigation
                if (this.isNavigating) {
                    return;
                }
                this.handleBlendMoved(updateData);
                break;
            case 'tank_updated':
                this.updateTankAssignment(updateData);
                break;
            case 'schedule_reordered':
                this.handleScheduleReorder(updateData);
                break;
            case 'test_message':
                alert(`Test WebSocket received: ${updateData.message}`);
                break;
            default:
                console.warn(`Unknown update type: ${updateType}`);
        }
    }

    _getTableAreaKey(tableBody) {
        if (!tableBody) {
            return this.getCurrentPageArea();
        }
        return (
            tableBody.dataset?.blendArea ||
            tableBody.dataset?.area ||
            tableBody.closest('table')?.dataset?.blendArea ||
            tableBody.closest('table')?.dataset?.area ||
            this.getCurrentPageArea()
        );
    }

    _isTemplateCandidateRow(row) {
        if (!row) {
            return false;
        }

        const classList = row.classList || [];
        if (classList.contains('NOTE') || classList.contains('scheduleNoteRow') || classList.contains('tableNoteRow')) {
            return false;
        }

        const lotCell = row.querySelector('.lot-number-cell');
        const quantityCell = row.querySelector('td.quantity-cell');

        if (!lotCell || !quantityCell) {
            return false;
        }

        // Ensure dropdown structure exists so cloning keeps controls intact
        if (!lotCell.querySelector('.dropdown')) {
            return false;
        }

        return true;
    }

    _cacheTemplateRow(areaKey, row) {
        if (!areaKey || !row) {
            return;
        }
        this.rowTemplateCache[areaKey] = row.cloneNode(true);
    }

    _getCachedTemplateRow(areaKey) {
        if (!areaKey) {
            return null;
        }
        const template = this.rowTemplateCache[areaKey];
        return template ? template.cloneNode(true) : null;
    }

    _getAnyCachedTemplateRow() {
        const keys = Object.keys(this.rowTemplateCache);
        if (!keys.length) {
            return null;
        }
        const template = this.rowTemplateCache[keys[0]];
        return template ? template.cloneNode(true) : null;
    }

    _buildRowForStructuredInsert(tableBody, data, targetBlendId, resolvedLotRecordId) {
        if (!tableBody) {
            return null;
        }

        const templateRow = this._findTemplateRow(tableBody, targetBlendId);
        let newRow = null;

        if (templateRow) {
            newRow = templateRow.cloneNode(true);
            this._resetClonedRowForReuse(newRow);
        } else {
            console.warn(
                '⚠️ Falling back to minimal structured row - no template available for area:',
                data?.new_blend_area || data?.blend_area || 'unknown'
            );
            newRow = this._buildFallbackStructuredRow();
        }

        if (!newRow) {
            return null;
        }

        if (targetBlendId !== undefined && targetBlendId !== null) {
            newRow.setAttribute('data-blend-id', targetBlendId);
            if (newRow.dataset) {
                newRow.dataset.blendId = String(targetBlendId);
            }
        } else {
            newRow.removeAttribute('data-blend-id');
            if (newRow.dataset && 'blendId' in newRow.dataset) {
                delete newRow.dataset.blendId;
            }
        }

        newRow.removeAttribute('data-schedule-entry-id');
        if (newRow.dataset) {
            delete newRow.dataset.scheduleEntryId;
        }

        this._applyRowClassesFromData(newRow, data);

        const checkbox = newRow.querySelector('input.rowCheckBox');
        if (checkbox) {
            checkbox.checked = false;
            if (resolvedLotRecordId) {
                checkbox.name = resolvedLotRecordId;
                checkbox.value = resolvedLotRecordId;
            } else {
                checkbox.removeAttribute('name');
                checkbox.removeAttribute('value');
            }

            if (data && Object.prototype.hasOwnProperty.call(data, 'item_code')) {
                if (data.item_code) {
                    checkbox.setAttribute('itemcode', data.item_code);
                } else {
                    checkbox.removeAttribute('itemcode');
                }
            }
        }

        return newRow;
    }

    _resetClonedRowForReuse(row) {
        if (!row) {
            return;
        }

        row.style.backgroundColor = '';
        row.removeAttribute('data-blend-id');
        row.removeAttribute('data-schedule-entry-id');

        if (row.dataset) {
            delete row.dataset.blendId;
            delete row.dataset.scheduleEntryId;
        }

        row.querySelectorAll('.edited-after-print-indicator').forEach((el) => el.remove());

        row.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
            checkbox.checked = false;
        });

        row.querySelectorAll('.blend-sheet-status').forEach((statusEl) => {
            statusEl.setAttribute('data-has-been-printed', 'false');
            statusEl.removeAttribute('data-record-id');
            statusEl.removeAttribute('data-print-history');
            statusEl.removeAttribute('data-bs-original-title');
            statusEl.innerHTML = '<em>Not Printed</em>';
        });

        row.querySelectorAll('.lot-number-cell').forEach((cell) => {
            cell.removeAttribute('lot-number');
        });
    }

    _buildFallbackStructuredRow() {
        const row = document.createElement('tr');
        row.classList.add('tableBodyRow');

        if (this.isLotRecordsPage()) {
            row.innerHTML = `
                <td class="text-center">
                    <input type="checkbox" class="rowCheckBox checkbox">
                </td>
                <td class="item-code-cell"></td>
                <td class="item-description-cell"></td>
                <td class="text-center lot-number-cell"></td>
                <td class="text-center quantity-cell"></td>
                <td class="text-center line-cell"></td>
                <td class="text-center run-date-cell"></td>
                <td class="text-center qty-oh-cell"></td>
                <td class="text-center date-entered-cell"></td>
                <td class="text-center blend-sheet-status-cell">
                    <span class="blend-sheet-status" data-has-been-printed="false"><em>Not Printed</em></span>
                </td>
                <td class="text-center schedule-status-cell">
                    <em>Not Scheduled</em>
                </td>
            `;
        } else {
            row.innerHTML = `
                <td class="orderCell text-center"></td>
                <td class="item-code-cell"></td>
                <td class="item-description-cell"></td>
                <td class="tank-cell">
                    <select class="tankSelect">
                        <option value="">--</option>
                    </select>
                </td>
                <td class="lot-number-cell"></td>
                <td class="quantity-cell"></td>
                <td class="text-center blend-sheet-status-cell">
                    <span class="blend-sheet-status" data-has-been-printed="false"><em>Not Printed</em></span>
                </td>
                <td class="run-date-cell"></td>
            `;
        }

        return row;
    }

    _applyRowClassesFromData(row, data) {
        if (!row || !data) {
            return;
        }

        const removableClasses = [
            'Desk_1Row',
            'Desk_2Row',
            'LET_DeskRow',
            'Desk_1',
            'Desk_2',
            'LET_Desk',
            'Hx',
            'Dm',
            'Totes',
            'Pails',
            'HxRow',
            'DmRow',
            'TotesRow',
            'NOTE',
            'priorityMessage',
        ];

        removableClasses.forEach((cls) => row.classList.remove(cls));

        if (data.row_classes) {
            data.row_classes
                .split(/\s+/)
                .filter(Boolean)
                .forEach((cls) => row.classList.add(cls));
        }

        const blendArea = data.new_blend_area || data.blend_area;
        const line = data.line;

        if (blendArea) {
            row.classList.add(blendArea);
            if (['Desk_1', 'Desk_2', 'LET_Desk', 'Hx', 'Dm', 'Totes', 'Pails'].includes(blendArea)) {
                row.classList.add(`${blendArea}Row`);
            }
        }

        if (line) {
            row.classList.add(`${line}Row`);
        }

        if (data.is_urgent) {
            row.classList.add('priorityMessage');
        }

        if (data.item_code === '******') {
            row.classList.add('NOTE');
        }

        if (data.item_code === '!!!!!') {
            row.classList.add('priorityMessage');
        }

        row.classList.add('tableBodyRow');
    }

    _applyScheduleNoteLayout(row, data) {
        if (!row) {
            return;
        }

        const lotNumber = (data && data.lot_number ? String(data.lot_number).trim() : '') || '******';
        const description = data?.item_description ?? '';

        const cells = Array.from(row.querySelectorAll('td'));
        if (cells.length >= 3) {
            const itemCodeCell = cells[1];
            const descriptionCell = cells[2];

            if (itemCodeCell) {
                itemCodeCell.textContent = data?.item_code || '******';
            }
            if (descriptionCell) {
                descriptionCell.textContent = description;
            }
        }

        const tankSelect = row.querySelector('.tankSelect');
        if (tankSelect) {
            const tankCell = tankSelect.closest('td') || tankSelect.parentElement;
            if (tankCell) {
                tankCell.textContent = '******';
            } else {
                tankSelect.remove();
            }
        }

        const lotCell = row.querySelector('.lot-number-cell');
        if (lotCell) {
            const dropdown = lotCell.querySelector('.dropdown');
            if (dropdown) {
                dropdown.remove();
            }
            lotCell.setAttribute('lot-number', lotNumber);
            lotCell.textContent = lotNumber;
        }

        const quantityCell = row.querySelector('.quantity-cell');
        if (quantityCell) {
            quantityCell.textContent = '';
        }

        // Ensure NOTE styling is always present for schedule notes
        row.classList.add('NOTE');

        // Schedule notes use a sentinel runtime so they sort last and stay obvious
        const runDateCell =
            row.querySelector('.run-date-cell') || row.querySelector('td[data-hour-short]');
        if (runDateCell) {
            runDateCell.textContent = '9999.0';
            runDateCell.setAttribute('data-hour-short', '9999.0');
        }

        const statusSpans = Array.from(row.querySelectorAll('.blend-sheet-status'));
        const statusCell =
            row.querySelector('.blend-sheet-status-cell') ||
            (statusSpans.length ? statusSpans[0].closest('td') : null);

        statusSpans.forEach((span) => {
            if (typeof bootstrap !== 'undefined') {
                const tooltipInstance = bootstrap.Tooltip.getInstance(span);
                if (tooltipInstance) {
                    tooltipInstance.dispose();
                }
            }
            span.remove();
        });

        if (statusCell) {
            statusCell.textContent = 'N/A';
        }

        row.querySelectorAll('.generate-excel-macro-trigger, .GHSLink, .blendLabelLink').forEach((el) => {
            el.remove();
        });
    }

    _getGlobalTemplateRow(areaKey, excludeBlendId) {
        const allRows = Array.from(document.querySelectorAll('tbody tr[data-blend-id]')).filter((row) => {
            return row.getAttribute('data-blend-id') !== String(excludeBlendId);
        });

        const candidate = allRows.find((row) => this._isTemplateCandidateRow(row));
        if (!candidate) {
            return null;
        }

        this._cacheTemplateRow(areaKey, candidate);
        return candidate;
    }

    updateBlendStatus(data) {
        const blendId = data.blend_id;
        
        const statusCell = document.querySelector(`tr[data-blend-id="${blendId}"] .blend-sheet-status, tr[data-blend-id="${blendId}"] .blend-sheet-status-cell .blend-sheet-status`);
        
        if (statusCell) {
            statusCell.setAttribute('data-has-been-printed', data.has_been_printed);
            statusCell.setAttribute('data-print-history', data.print_history_json || '[]');
            statusCell.innerHTML = data.last_print_event_str;
            
            if (data.was_edited_after_last_print) {
                statusCell.innerHTML += '<sup class="edited-after-print-indicator">!</sup>';
            }
            
            // Reinitialize tooltip for this specific element after status update
            this.initializeTooltipForElement(statusCell);
            
            statusCell.style.backgroundColor = '#ffffcc';
            setTimeout(() => {
                statusCell.style.backgroundColor = '';
            }, 2000);
        } else {
            console.warn(`No status cell found for blend_id: ${blendId}`);
        }
    }

    updateLotInfo(data) {
        console.log(data);
        const blendId = data.blend_id ?? data.new_blend_id ?? data.old_blend_id ?? null;
        const lotRecordId = data.lot_num_record_id ?? data.lot_id ?? null;
        let row = null;

        if (blendId !== null && blendId !== undefined) {
            row = document.querySelector(`tr[data-blend-id="${blendId}"]`) ??
                document.querySelector(`tr[data-schedule-entry-id="${blendId}"]`);
        }

        if (!row && lotRecordId !== null && lotRecordId !== undefined) {
            const statusEl = document.querySelector(
                `.blend-sheet-status[data-record-id="${lotRecordId}"]`
            );
            if (statusEl) {
                row = statusEl.closest('tr');
            }
        }

        if (!row && lotRecordId !== null && lotRecordId !== undefined) {
            const checkbox = document.querySelector(
                `input.rowCheckBox[name="${lotRecordId}"]`
            );
            if (checkbox) {
                row = checkbox.closest('tr');
            }
        }

        if (!row && data.lot_number) {
            const desiredLotNumber = String(data.lot_number).trim();
            const lotCells = Array.from(document.querySelectorAll('.lot-number-cell'));
            const matchCell = lotCells.find((cell) => {
                const attrValue = cell.getAttribute('lot-number');
                if (attrValue && attrValue.trim() === desiredLotNumber) {
                    return true;
                }
                const textValue = (cell.textContent || '').trim();
                return textValue === desiredLotNumber;
            });
            if (matchCell) {
                row = matchCell.closest('tr');
            }
        }

        if (!row) {
            const contextParts = [];
            if (blendId !== null && blendId !== undefined) {
                contextParts.push(`blend_id: ${blendId}`);
            }
            if (lotRecordId !== null && lotRecordId !== undefined) {
                contextParts.push(`lot_record_id: ${lotRecordId}`);
            }
            if (data.lot_number) {
                contextParts.push(`lot_number: ${data.lot_number}`);
            }
            console.warn(`No row found for ${contextParts.join(', ') || 'lot update payload'}`);
            return;
        }

        if (blendId !== null && blendId !== undefined) {
            row.setAttribute('data-blend-id', blendId);
            row.dataset.blendId = String(blendId);
        }

        const isScheduleNote = data.item_code === '******';
        if (isScheduleNote) {
            this._applyScheduleNoteLayout(row, data);
            return;
        }

        const lotNumber = data.lot_number ?? '';
        const itemCode = data.item_code ?? '';
        const itemDescription = data.item_description ?? '';
        const line = data.line ?? '';
        const blendArea = data.blend_area ?? '';
        const rawRunDate = data.run_date ?? '';
        const runDate = rawRunDate && rawRunDate !== 'null' && rawRunDate !== 'None' ? rawRunDate : '';
        const rawQuantity = data.quantity;
        const deskLines = ['Desk_1', 'Desk_2', 'LET_Desk'];
        const isDeskContext = deskLines.includes(line) || deskLines.includes(blendArea) || (!line && !blendArea);
        let numericQuantity = NaN;

        const lotCell = row.querySelector('.lot-number-cell');
        if (lotCell) {
            if (lotNumber) {
                lotCell.setAttribute('lot-number', lotNumber);
            } else {
                lotCell.removeAttribute('lot-number');
            }

            const lotTextNode = Array.from(lotCell.childNodes).find((node) => node.nodeType === Node.TEXT_NODE);
            if (lotTextNode) {
                lotTextNode.textContent = lotNumber || '';
            }

            lotCell.style.backgroundColor = '#ccffcc';
            setTimeout(() => {
                lotCell.style.backgroundColor = '';
            }, 2000);
        }

        const quantityCell = row.querySelector('td.quantity-cell');
        if (quantityCell) {
            if (rawQuantity !== undefined && rawQuantity !== null && rawQuantity !== '') {
                numericQuantity = parseFloat(rawQuantity);
                if (!Number.isNaN(numericQuantity)) {
                    const formatted = numericQuantity.toFixed(isDeskContext ? 1 : 0);
                    quantityCell.textContent = isDeskContext ? `${formatted} gal` : formatted;
                } else {
                    quantityCell.textContent = '0.0 gal';
                }
            }

            quantityCell.style.backgroundColor = '#ccffff';
            setTimeout(() => {
                quantityCell.style.backgroundColor = '';
            }, 2000);
        }

        const macroButton = row.querySelector('.generate-excel-macro-trigger');
        if (macroButton) {
            if (itemCode) {
                macroButton.dataset.itemCode = itemCode;
            } else {
                delete macroButton.dataset.itemCode;
            }

            if (itemDescription) {
                macroButton.dataset.itemDescription = itemDescription;
            } else {
                delete macroButton.dataset.itemDescription;
            }

            if (lotNumber) {
                macroButton.dataset.lotNumber = lotNumber;
            } else {
                delete macroButton.dataset.lotNumber;
            }

            if (!Number.isNaN(numericQuantity)) {
                macroButton.dataset.lotQuantity = numericQuantity.toString();
            } else if (rawQuantity !== undefined) {
                macroButton.dataset.lotQuantity = `${rawQuantity}`;
            } else {
                delete macroButton.dataset.lotQuantity;
            }

            if (line || blendArea) {
                macroButton.dataset.line = line || blendArea || '';
            } else {
                delete macroButton.dataset.line;
            }

            if (runDate) {
                macroButton.dataset.runDate = runDate;
            } else {
                delete macroButton.dataset.runDate;
            }
        }

        const ghsLink = row.querySelector('.GHSLink');
        if (ghsLink) {
            if (lotNumber) {
                ghsLink.setAttribute('lotNum', lotNumber);
            } else {
                ghsLink.removeAttribute('lotNum');
            }
            if (itemCode) {
                ghsLink.setAttribute('itemCode', itemCode);
            } else {
                ghsLink.removeAttribute('itemCode');
            }
        }

        const blendLabelLink = row.querySelector('.blendLabelLink');
        if (blendLabelLink) {
            if (lotNumber) {
                blendLabelLink.dataset.lotNumber = lotNumber;
            } else {
                delete blendLabelLink.dataset.lotNumber;
            }
            if (!Number.isNaN(numericQuantity)) {
                blendLabelLink.dataset.lotQuantity = numericQuantity.toString();
            } else if (rawQuantity !== undefined) {
                blendLabelLink.dataset.lotQuantity = `${rawQuantity}`;
            } else {
                delete blendLabelLink.dataset.lotQuantity;
            }
        }

        const lotNumButton = row.querySelector('.lotNumButton');
        if (lotNumButton) {
            if (line || blendArea) {
                lotNumButton.dataset.line = line || blendArea || '';
            } else {
                delete lotNumButton.dataset.line;
            }
            lotNumButton.dataset.itemcode = itemCode || '';
            lotNumButton.dataset.desc = itemDescription || '';
            if (!Number.isNaN(numericQuantity)) {
                lotNumButton.dataset.totalqty = numericQuantity.toString();
            } else if (rawQuantity !== undefined) {
                lotNumButton.dataset.totalqty = `${rawQuantity}`;
            } else {
                delete lotNumButton.dataset.totalqty;
            }
            if (runDate) {
                let formattedRunDate = runDate;
                const existingRunDate = lotNumButton.dataset.rundate || '';
                const shouldFormatAsMDY = existingRunDate.includes('/') && runDate.includes('-');
                if (shouldFormatAsMDY) {
                    const parsedDate = new Date(runDate);
                    if (!Number.isNaN(parsedDate.getTime())) {
                        const month = String(parsedDate.getMonth() + 1).padStart(2, '0');
                        const day = String(parsedDate.getDate()).padStart(2, '0');
                        const year = parsedDate.getFullYear();
                        formattedRunDate = `${month}/${day}/${year}`;
                    }
                }
                lotNumButton.dataset.rundate = formattedRunDate;
            } else {
                delete lotNumButton.dataset.rundate;
            }
        }

        if (this.isLotRecordsPage()) {
            this._updateScheduleStatusDropdown(row, blendArea);
        }
        this._ensureEditLotButton(row, data.lot_num_record_id || data.lot_id);
    }

    updateTankAssignment(data) {
        if (this.isLotRecordsPage()) {
            return;
        }

        const blendId = data.blend_id;
        const newTank = data.new_tank;
        const lotNumber = data.lot_number;
        
        // Find the row by blend_id
        const row = document.querySelector(`tr[data-blend-id="${blendId}"]`);
        if (!row) {
            console.warn(`⚠️ Could not find row for blend_id: ${blendId}`);
            return;
        }
        
        // Find the tank select dropdown in this row
        const tankSelect = row.querySelector('.tankSelect');
        if (!tankSelect) {
            console.warn(`⚠️ Could not find tank select dropdown for blend_id: ${blendId}`);
            return;
        }
        
        // Update the selected value - handle null/None properly
        if (newTank && newTank !== 'null' && newTank !== 'None') {
            tankSelect.value = newTank;
        } else {
            // No tank assigned - set to empty which should select the default "no selection" option
            tankSelect.value = '';
            
            // If that doesn't work, try to find and select the first option (usually the default)
            if (tankSelect.selectedIndex === -1 && tankSelect.options.length > 0) {
                tankSelect.selectedIndex = 0;
            }
        }
        
        // Add visual feedback to show the change
        tankSelect.style.backgroundColor = '#fff3cd'; // Light yellow
        tankSelect.style.transition = 'background-color 2s ease';
        
        setTimeout(() => {
            tankSelect.style.backgroundColor = '';
        }, 2000);
        
        // Optional: Show a subtle notification
        this.showTankUpdateNotification(lotNumber, data.old_tank, newTank);
    }

    showTankUpdateNotification(lotNumber, oldTank, newTank) {
        if (this.isLotRecordsPage()) {
            return;
        }

        // Create a subtle notification
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 4px;
            padding: 8px 12px;
            color: #856404;
            font-size: 14px;
            z-index: 9999;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            transition: opacity 0.3s ease;
        `;
        
        // Format tank names for display
        const displayOldTank = oldTank || 'None';
        const displayNewTank = newTank || 'None';
        
        notification.innerHTML = `
            <strong>Tank Updated:</strong> Lot ${lotNumber}<br>
            <small>${displayOldTank} → ${displayNewTank}</small>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove notification after 3 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    // Desk schedule tables should drop deleted blends entirely, but the lot numbers page
    // keeps the record and merely clears its schedule metadata.
    removeBlend(data) {
        const blendId = data?.blend_id ?? null;
        const lotRecordId = data?.lot_num_record_id ?? data?.lot_id ?? null;
        const lotNumber = data?.lot_number ?? null;
        const blendArea = data?.blend_area ?? data?.line ?? '';

        if (this.isLotRecordsPage()) {
            this._handleBlendDeletedOnLotRecords(data);
            return;
        }

        const isLotOptionalArea = ['Hx', 'Dm', 'Totes'].includes(String(blendArea));

        let row = null;

        if (blendId !== null && blendId !== undefined) {
            row =
                document.querySelector(`tr[data-blend-id="${blendId}"]`) ??
                document.querySelector(`tr[data-schedule-entry-id="${blendId}"]`);
        }

        if (!row && lotRecordId !== null && lotRecordId !== undefined) {
            const statusEl = document.querySelector(
                `.blend-sheet-status[data-record-id="${lotRecordId}"]`
            );
            if (statusEl) {
                row = statusEl.closest('tr');
            }
        }

        if (!row && lotRecordId !== null && lotRecordId !== undefined) {
            const checkbox = document.querySelector(
                `input.rowCheckBox[name="${lotRecordId}"]`
            );
            if (checkbox) {
                row = checkbox.closest('tr');
            }
        }

        if (!row && lotNumber) {
            const desiredLot = String(lotNumber).trim();
            const lotCells = Array.from(document.querySelectorAll('.lot-number-cell'));
            const matchCell = lotCells.find((cell) => {
                const attrValue = cell.getAttribute('lot-number');
                if (attrValue && attrValue.trim() === desiredLot) {
                    return true;
                }
                const textValue = (cell.textContent || '').trim();
                return textValue === desiredLot;
            });
            if (matchCell) {
                row = matchCell.closest('tr');
            }
        }

        if (!row) {
            console.warn(
                `⚠️ blend_deleted received but no matching row found for`,
                {
                    blendId,
                    lotRecordId,
                    lotNumber,
                    blendArea,
                }
            );
            return;
        }

        if (isLotOptionalArea) {
            this._markRowAsLotMissing(row);
            return;
        }

        row.style.backgroundColor = '#ffcccc';
        setTimeout(() => {
            row.remove();
        }, 1000);
    }

    _markRowAsLotMissing(row) {
        if (!row) {
            return;
        }

        row.classList.remove('problemRow');
        row.classList.add('noLotNumRow');

        const lotCell = row.querySelector('.lot-number-cell');
        if (lotCell) {
            lotCell.removeAttribute('lot-number');
            lotCell.textContent = 'Not found.';
        }

        const statusSpans = row.querySelectorAll('.blend-sheet-status');
        statusSpans.forEach((span) => {
            if (typeof bootstrap !== 'undefined') {
                const tooltipInstance = bootstrap.Tooltip.getInstance(span);
                if (tooltipInstance) {
                    tooltipInstance.dispose();
                }
            }
        });

        const statusCell =
            (statusSpans.length ? statusSpans[0].closest('td') : null) ||
            row.querySelector('.blend-sheet-status-cell');
        if (statusCell) {
            statusCell.innerHTML = 'N/A';
        }

        row.querySelectorAll('.blend-sheet-status').forEach((span) => span.remove());

        const macroButtons = row.querySelectorAll('.generate-excel-macro-trigger');
        macroButtons.forEach((btn) => btn.remove());

        const blendLabelLinks = row.querySelectorAll('.blendLabelLink');
        blendLabelLinks.forEach((link) => link.remove());

        const checkbox = row.querySelector('input.rowCheckBox');
        if (checkbox) {
            checkbox.checked = false;
            checkbox.removeAttribute('name');
            checkbox.removeAttribute('value');
        }

        row.removeAttribute('data-blend-id');
        row.removeAttribute('data-schedule-entry-id');
        if (row.dataset) {
            delete row.dataset.blendId;
            delete row.dataset.scheduleEntryId;
        }

        row.style.backgroundColor = '#ffe8a1';
        row.style.transition = 'background-color 2s ease';
        setTimeout(() => {
            row.style.backgroundColor = '';
        }, 2000);
    }

    _handleBlendDeletedOnLotRecords(data) {
        const blendId = data?.blend_id;
        const lotNumber = data?.lot_number;
        const lotRecordId = data?.lot_num_record_id ?? data?.lot_id;

        let row = null;

        if (blendId !== undefined && blendId !== null) {
            row = document.querySelector(`tr[data-blend-id="${blendId}"]`);
        }

        if (!row && lotRecordId !== undefined && lotRecordId !== null) {
            const statusMatch = document.querySelector(
                `.blend-sheet-status[data-record-id="${lotRecordId}"]`
            );
            if (statusMatch) {
                row = statusMatch.closest('tr');
            }
        }

        if (!row && lotNumber) {
            const normalizedLot = String(lotNumber).trim();
            const lotCell = Array.from(document.querySelectorAll('.lot-number-cell')).find(
                (cell) =>
                    cell.getAttribute('lot-number') === normalizedLot ||
                    (cell.textContent || '').trim() === normalizedLot
            );
            if (lotCell) {
                row = lotCell.closest('tr');
            }
        }

        if (!row) {
            console.warn('⚠️ Lot records delete received but no matching row found', data);
            return;
        }

        const hardDeleteFlags = [
            data?.lot_num_record_deleted,
            data?.lot_record_deleted,
            data?.record_was_deleted,
        ];
        const isHardDelete = hardDeleteFlags.some((flag) => {
            if (flag === undefined || flag === null) {
                return false;
            }
            if (typeof flag === 'string') {
                return flag.toLowerCase() === 'true';
            }
            return Boolean(flag);
        });

        if (isHardDelete) {
            const statusSpans = row.querySelectorAll('.blend-sheet-status');
            statusSpans.forEach((span) => {
                if (typeof bootstrap !== 'undefined') {
                    const tooltipInstance = bootstrap.Tooltip.getInstance(span);
                    if (tooltipInstance) {
                        tooltipInstance.dispose();
                    }
                }
            });

            row.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
            row.style.opacity = '0';
            row.style.transform = 'scale(0.98)';

            setTimeout(() => {
                if (row.parentNode) {
                    row.parentNode.removeChild(row);
                }
            }, 250);
            return;
        }

        // Drop desk styling/ids so the row is treated as unscheduled.
        const removableClasses = ['Desk_1Row', 'Desk_2Row', 'LET_DeskRow', 'Desk_1', 'Desk_2', 'LET_Desk'];
        removableClasses.forEach((cls) => row.classList.remove(cls));

        row.removeAttribute('data-blend-id');
        row.removeAttribute('data-schedule-entry-id');
        delete row.dataset.blendId;

        const lotCell = row.querySelector('.lot-number-cell');
        if (lotCell && lotNumber) {
            lotCell.setAttribute('lot-number', lotNumber);
        }

        let scheduleCell = row.querySelector('td.schedule-status-cell');
        if (!scheduleCell) {
            const managementLink = row.querySelector('a[href*="schedule-management-request"]');
            if (managementLink) {
                scheduleCell = managementLink.closest('td');
            }
        }

        if (!scheduleCell) {
            const textCenterCells = Array.from(row.querySelectorAll('td.text-center')).filter(
                (cell) => !cell.classList.contains('blend-sheet-status-cell')
            );
            if (textCenterCells.length) {
                scheduleCell = textCenterCells[textCenterCells.length - 1];
            }
        }

        if (scheduleCell) {
            scheduleCell.innerHTML = '<em>Not Scheduled</em>';
        }

        row.style.backgroundColor = '#ffe8a1';
        row.style.transition = 'background-color 2s ease';
        setTimeout(() => {
            row.style.backgroundColor = '';
        }, 2000);
    }

    async addBlend(data) {
        const htmlRow = data.html_row;
        const blendArea = data.blend_area || data.new_blend_area;
        const lotRecordId = data.lot_num_record_id || data.lot_id;
        const isLotRecordsPage = this.isLotRecordsPage();

        if (isLotRecordsPage && !lotRecordId) {
            console.debug('📝 Ignoring schedule-only addition on lot numbers page (no lot record id present).');
            return;
        }

        if (isLotRecordsPage && lotRecordId) {
            try {
                const rowData = await fetchLotRecordRow(lotRecordId);
                const tableBody = this.getTableBodyForArea(blendArea);
                
                if (!tableBody) {
                    console.warn(`⚠️ Could not find table body for lot numbers page`);
                    return;
                }

                const rawHtml = (rowData?.html ?? '').trim();
                if (!rawHtml) {
                    console.warn(`⚠️ Received empty lot record HTML for lot ID: ${lotRecordId}`);
                    return;
                }

                const template = document.createElement('template');
                template.innerHTML = rawHtml;

                const isTableRow = (node) =>
                    node &&
                    node.nodeType === Node.ELEMENT_NODE &&
                    typeof node.tagName === 'string' &&
                    node.tagName.toLowerCase() === 'tr';

                let candidateRows = Array.from(template.content.children).filter(isTableRow);

                if (!candidateRows.length) {
                    candidateRows = Array.from(template.content.querySelectorAll('tr')).map((row) =>
                        row.cloneNode(true)
                    );
                }

                const rowsToInsert = candidateRows.filter(isTableRow);

                if (!rowsToInsert.length) {
                    console.warn(`⚠️ No <tr> nodes found in lot record HTML for lot ID: ${lotRecordId}`);
                    return;
                }

                const rowsToRemove = new Set();
                if (lotRecordId) {
                    const statusRow = tableBody
                        .querySelector(`.blend-sheet-status[data-record-id="${lotRecordId}"]`)
                        ?.closest('tr');
                    if (statusRow) {
                        rowsToRemove.add(statusRow);
                    }

                    const editButtonRow = tableBody
                        .querySelector(`.editLotButton[data-lot-id="${lotRecordId}"]`)
                        ?.closest('tr');
                    if (editButtonRow) {
                        rowsToRemove.add(editButtonRow);
                    }
                }

                rowsToRemove.forEach((row) => row?.remove());

                const fragment = document.createDocumentFragment();
                rowsToInsert.forEach((row) => fragment.appendChild(row));

                const firstInsertedRow = rowsToInsert[0] || null;
                const insertionAnchor = tableBody.firstElementChild;
                tableBody.insertBefore(fragment, insertionAnchor || null);

                rowsToInsert.forEach((row) => {
                    row.style.backgroundColor = '#ccffcc';
                    row.style.transition = 'background-color 2s ease';
                    setTimeout(() => {
                        row.style.backgroundColor = '';
                    }, 2000);

                    this.initializeTooltipsForRow(row);
                    this._ensureEditLotButton(row, lotRecordId);
                    if (typeof window.attachLotRecordDeleteHandler === 'function') {
                        window.attachLotRecordDeleteHandler(row);
                    }
                });
                
                if (firstInsertedRow) {
                    firstInsertedRow.scrollIntoView({
                        behavior: 'smooth',
                        block: 'center',
                        inline: 'nearest'
                    });
                }

                console.log(`✅ Added server-rendered lot record row for lot ID: ${lotRecordId}`);
                return;
            } catch (error) {
                console.error(`❌ Failed to fetch server-rendered row for lot ID ${lotRecordId}:`, error);
                // Fall through to legacy handling
            }
        }
        
        // 🎯 ENHANCED: Handle both HTML row format (legacy) and structured data format (new)
        if (htmlRow) {
            // Legacy HTML row format
            const currentPageArea = this.getCurrentPageArea();
            if (currentPageArea === blendArea || currentPageArea === 'all') {
                const tableBody = this.getTableBodyForArea(blendArea);
                if (tableBody) {
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = htmlRow;
                    const newRow = tempDiv.firstElementChild;
                    
                    tableBody.appendChild(newRow);
                    if (typeof window.attachLotRecordDeleteHandler === 'function') {
                        window.attachLotRecordDeleteHandler(newRow);
                    }
                    
                    newRow.style.backgroundColor = '#ccffff';
                    setTimeout(() => {
                        newRow.style.backgroundColor = '';
                    }, 2000);
                }
            }
        } else if (data.new_blend_id) {
            // 🎯 NEW: Structured data format - use the same logic as addBlendRowToTable
            const currentPageArea = this.getCurrentPageArea();
            if (currentPageArea === blendArea || currentPageArea === 'all') {
                this.addBlendRowToTable(data);
            }
        } else if (data.blend_id) {
            const normalizedData = {
                ...data,
                new_blend_id: data.blend_id,
                new_blend_area: blendArea,
            };
            const currentPageArea = this.getCurrentPageArea();
            if (currentPageArea === blendArea || currentPageArea === 'all') {
                this.addBlendRowToTable(normalizedData);
            }
        } else {
            console.warn('⚠️ addBlend received data without html_row or structured format:', data);
        }
    }

    handleBlendMoved(data) {
        const currentPageArea = this.getCurrentPageArea();
        const isLotRecordsPage = this.isLotRecordsPage();

        if (isLotRecordsPage) {
            this._handleBlendMovedOnLotRecords(data);
            return;
        }

        // Remove blend from old area
        const oldBlendId = data.old_blend_id;
        const oldBlendArea = data.old_blend_area;
        
        if (currentPageArea === oldBlendArea || currentPageArea === 'all') {
            const oldRow = document.querySelector(`tr[data-blend-id="${oldBlendId}"]`);
            
            if (oldRow) {
                oldRow.remove();
            } else {
                console.warn(`⚠️ Could not find old row with data-blend-id="${oldBlendId}"`);
            }
        }
        
        // Add blend to new area (only if we're viewing the destination area)
        const newBlendArea = data.new_blend_area;
        
        if (currentPageArea === newBlendArea || currentPageArea === 'all') {
            // Add the new row to the table
            this.addBlendRowToTable(data);
            
            // Create a subtle notification that blend moved here
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 4px;
                padding: 8px 12px;
                color: #155724;
                font-size: 14px;
                z-index: 9999;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                transition: opacity 0.3s ease;
            `;
            notification.innerHTML = `
                <strong>Blend moved:</strong> ${data.item_code} (Lot ${data.lot_number})
            `;
            
            document.body.appendChild(notification);
            
            // Auto-remove notification after 3 seconds
            setTimeout(() => {
                notification.style.opacity = '0';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }, 3000);
        }
    }

    _handleBlendMovedOnLotRecords(data) {
        const oldBlendId = data.old_blend_id;
        const newBlendId = data.new_blend_id ?? data.blend_id ?? oldBlendId;
        const newBlendArea = data.new_blend_area || data.blend_area || '';
        const lotRecordId = data.lot_num_record_id || data.lot_id;

        const findRowForBlend = (blendId) => {
            if (blendId === null || blendId === undefined) {
                return null;
            }
            return (
                document.querySelector(`tr[data-blend-id="${blendId}"]`) ??
                document.querySelector(`tr[data-schedule-entry-id="${blendId}"]`)
            );
        };

        let row = findRowForBlend(oldBlendId);
        if (!row && newBlendId !== oldBlendId) {
            row = findRowForBlend(newBlendId);
        }

        if (!row) {
            console.warn(`⚠️ Lot records move fallback - no row found for blend_id="${oldBlendId}"`);
            return;
        }

        row.setAttribute('data-blend-id', newBlendId);
        row.dataset.blendId = String(newBlendId);

        if (row.hasAttribute('data-schedule-entry-id')) {
            row.setAttribute('data-schedule-entry-id', newBlendId);
        }

        const deskRowClasses = ['Desk_1Row', 'Desk_2Row', 'LET_DeskRow', 'Desk_1', 'Desk_2', 'LET_Desk'];
        deskRowClasses.forEach((cls) => row.classList.remove(cls));

        if (newBlendArea) {
            row.classList.add(`${newBlendArea}Row`);
        }

        const statusElements = row.querySelectorAll('.blend-sheet-status');
        const resolvedLotRecordId =
            lotRecordId ||
            (statusElements.length
                ? statusElements[0].getAttribute('data-record-id')
                : null) ||
            newBlendId;

        statusElements.forEach((statusEl) => {
            statusEl.setAttribute('data-record-id', resolvedLotRecordId);
        });

        const managementLinks = row.querySelectorAll('a[href*="schedule-management-request"]');
        managementLinks.forEach((link) => {
            const href = link.getAttribute('href');
            if (!href) {
                return;
            }

            let updatedHref = href;

            if (data.old_blend_area && newBlendArea) {
                updatedHref = updatedHref.replace(
                    `/switch-schedules/${data.old_blend_area}/`,
                    `/switch-schedules/${newBlendArea}/`
                );
            }

            if (oldBlendId && newBlendId) {
                updatedHref = updatedHref.replace(
                    new RegExp(`/${oldBlendId}(?=\\?|$)`),
                    `/${newBlendId}`
                );
            }

            link.setAttribute('href', updatedHref);
        });

        this._updateLotRecordsLineCell(row, data.line || newBlendArea);

        const normalizedData = {
            ...data,
            blend_id: newBlendId,
            blend_area: newBlendArea,
        };
        this.updateLotInfo(normalizedData);

        if (
            data.has_been_printed !== undefined ||
            data.last_print_event_str !== undefined ||
            data.print_history_json !== undefined
        ) {
            this.updateBlendStatus({
                blend_id: newBlendId,
                has_been_printed: data.has_been_printed,
                last_print_event_str: data.last_print_event_str,
                print_history_json: data.print_history_json,
                was_edited_after_last_print: data.was_edited_after_last_print,
            });
        }

        this.initializeTooltipsForRow(row);
        this._positionLotRecordsRow(row, { preserveExistingOrder: true });
        this._removeDuplicateLotRows(row, newBlendId, resolvedLotRecordId);

        row.style.backgroundColor = '#d4edda';
        row.style.transition = 'background-color 2s ease';
        setTimeout(() => {
            row.style.backgroundColor = '';
        }, 2000);
    }

    _updateLotRecordsLineCell(row, lineValue) {
        if (!row) {
            return;
        }

        const cells = Array.from(row.querySelectorAll('td'));
        if (!cells.length) {
            return;
        }

        const hasCheckbox = !!cells[0]?.querySelector('input[type="checkbox"]');
        const lineIndex = hasCheckbox ? 5 : 4;
        const lineCell = cells[lineIndex];

        if (lineCell) {
            lineCell.textContent = lineValue || '';
        }
    }

    _updateScheduleStatusDropdown(row, blendArea) {
        if (!row) {
            return;
        }

        const managementLinks = Array.from(
            row.querySelectorAll('a[href*="schedule-management-request"]')
        );
        if (!managementLinks.length) {
            return;
        }

        const dropdown = managementLinks[0].closest('.dropdown');
        if (!dropdown) {
            return;
        }

        const button = dropdown.querySelector('button.dropdown-toggle');
        if (button && blendArea) {
            button.textContent = blendArea;
        }

        const viewLink = dropdown.querySelector('a[href*="/core/blend-schedule"]');
        if (viewLink && blendArea) {
            viewLink.setAttribute(
                'href',
                `/core/blend-schedule?blend-area=${encodeURIComponent(blendArea)}`
            );
            viewLink.textContent = `View ${blendArea} Schedule`;
        }

        if (!managementLinks.length) {
            return;
        }

        const blendId =
            row.getAttribute('data-schedule-entry-id') ||
            row.getAttribute('data-blend-id') ||
            button?.getAttribute('data-blend-id');

        const extractedTargets = managementLinks
            .map((link) => {
                const text = link.textContent || '';
                const match = text.match(/Switch To\s+([A-Za-z0-9_]+)/i);
                if (match && match[1]) {
                    return match[1];
                }
                try {
                    const url = new URL(link.getAttribute('href'), window.location.origin);
                    const candidate = url.searchParams.get('switch-to');
                    if (candidate) {
                        return candidate;
                    }
                } catch (error) {
                    console.warn('⚠️ Unable to parse switch target from link:', error);
                }
                return null;
            })
            .filter(Boolean);

        const knownTargets = ['Desk_1', 'Desk_2', 'LET_Desk'];
        const candidateTargets = Array.from(
            new Set([...extractedTargets, ...knownTargets])
        ).filter((area) => area && area !== blendArea);

        const targetsToUse = candidateTargets.slice(0, managementLinks.length);

        managementLinks.forEach((link) => {
            const targetArea = targetsToUse.shift();
            if (!blendArea || !targetArea || targetArea === blendArea) {
                link.style.display = 'none';
                return;
            }
            link.style.display = '';

            const href = link.getAttribute('href');
            if (!href) {
                return;
            }

            link.textContent = `Switch To ${targetArea}`;

            try {
                const url = new URL(href, window.location.origin);
                url.pathname = `/core/schedule-management-request/switch-schedules/${blendArea}/${blendId || ''}`;
                url.searchParams.set('switch-to', targetArea);
                link.setAttribute('href', url.pathname + url.search);
            } catch (error) {
                console.warn('⚠️ Failed to rebuild schedule-management URL:', error);
            }
        });
    }

    _refreshLotRecordsRow(row, data, blendId, lotRecordId) {
        if (!row) {
            return;
        }

        const normalizedBlendId = blendId || data.new_blend_id || data.blend_id;
        const resolvedLotRecordId = lotRecordId || data.lot_num_record_id || data.lot_id;
        const targetArea = data.new_blend_area || data.blend_area;

        row.setAttribute('data-blend-id', normalizedBlendId);
        row.dataset.blendId = String(normalizedBlendId);

        if (row.hasAttribute('data-schedule-entry-id')) {
            row.setAttribute('data-schedule-entry-id', normalizedBlendId);
        }

        this._updateLotRecordsLineCell(row, data.line || targetArea);

        const normalizedData = {
            ...data,
            blend_id: normalizedBlendId,
            blend_area: targetArea,
        };

        this.updateLotInfo(normalizedData);
        if (
            data.has_been_printed !== undefined ||
            data.last_print_event_str !== undefined ||
            data.print_history_json !== undefined
        ) {
            this.updateBlendStatus({
                blend_id: normalizedBlendId,
                has_been_printed: data.has_been_printed,
                last_print_event_str: data.last_print_event_str,
                print_history_json: data.print_history_json,
                was_edited_after_last_print: data.was_edited_after_last_print,
            });
        }

        this.initializeTooltipsForRow(row);
        this.initializeTankSelectForRow(row);
        this._positionLotRecordsRow(row, { preserveExistingOrder: true });
        this._removeDuplicateLotRows(row, normalizedBlendId, resolvedLotRecordId);
        if (typeof window.attachLotRecordDeleteHandler === 'function') {
            window.attachLotRecordDeleteHandler(row);
        }

        row.style.backgroundColor = '#cce5ff';
        row.style.transition = 'background-color 2s ease';
        setTimeout(() => {
            row.style.backgroundColor = '';
        }, 2000);
    }

    _positionLotRecordsRow(row, options = {}) {
        if (!row) {
            return;
        }

        const { preserveExistingOrder = false } = options;
        if (preserveExistingOrder) {
            return;
        }

        const tableBody = row.closest('tbody');
        if (!tableBody) {
            return;
        }

        const firstRow = tableBody.firstElementChild;
        if (firstRow && firstRow !== row) {
            tableBody.insertBefore(row, firstRow);
        } else if (!firstRow) {
            tableBody.appendChild(row);
        }
    }

    _removeDuplicateLotRows(preferredRow, blendId, lotRecordId) {
        if (!preferredRow) {
            return;
        }

        const tableBody = preferredRow.closest('tbody');
        if (!tableBody) {
            return;
        }

        const rowsByBlend = blendId
            ? Array.from(tableBody.querySelectorAll(`tr[data-blend-id="${blendId}"]`))
            : [];

        const rowsByRecord = lotRecordId
            ? Array.from(
                  tableBody.querySelectorAll(
                      `.blend-sheet-status[data-record-id="${lotRecordId}"]`
                  )
              ).map((el) => el.closest('tr'))
            : [];

        const candidateRows = [...rowsByBlend, ...rowsByRecord].filter(Boolean);
        const uniqueRows = candidateRows.filter(
            (row, index, arr) => arr.indexOf(row) === index
        );

        if (uniqueRows.length <= 1) {
            return;
        }

        let rowToKeep = null;
        if (preferredRow && uniqueRows.includes(preferredRow)) {
            rowToKeep = preferredRow;
        }

        if (!rowToKeep) {
            rowToKeep =
                uniqueRows.find((row) => row.querySelector('.rowCheckBox')) ||
                uniqueRows.find((row) => row.querySelector('input[type="checkbox"]')) ||
                uniqueRows[0];
        }

        uniqueRows.forEach((row) => {
            if (row !== rowToKeep) {
                row.remove();
            }
        });
    }

    addBlendRowToTable(data) {
        const targetArea = data.new_blend_area || data.blend_area;
        const targetBlendId = data.new_blend_id || data.blend_id;
        const lotRecordId = data.lot_num_record_id || data.lot_id;
        const resolvedLotRecordId = lotRecordId || targetBlendId;
        const tableBody = this.getTableBodyForArea(targetArea);
        
        if (!tableBody) {
            console.error(`❌ Could not find table body for area: ${targetArea}`);
            return;
        }
        
        // Check if row already exists to prevent duplicates
        let duplicateRow = targetBlendId
            ? tableBody.querySelector(`tr[data-blend-id="${targetBlendId}"]`)
            : null;

        if (!duplicateRow && lotRecordId) {
            const statusMatch = tableBody.querySelector(
                `.blend-sheet-status[data-record-id="${lotRecordId}"]`
            );
            if (statusMatch) {
                duplicateRow = statusMatch.closest('tr');
            }
        }

        const isScheduleNote = data.item_code === '******';

        if (duplicateRow) {
            if (this.isLotRecordsPage()) {
                this._refreshLotRecordsRow(
                    duplicateRow,
                    data,
                    targetBlendId,
                    lotRecordId
                );
            } else {
                // Update the existing row's tank selection
                const existingTankSelect = duplicateRow.querySelector('.tankSelect');
                if (existingTankSelect) {
                    if (isScheduleNote) {
                        this._applyRowClassesFromData(duplicateRow, data);
                        const tankCell = existingTankSelect.closest('td') || existingTankSelect.parentElement;
                        if (tankCell) {
                            tankCell.textContent = '******';
                        } else {
                            existingTankSelect.remove();
                        }
                        this._applyScheduleNoteLayout(duplicateRow, data);
                        return;
                    }
                    // Handle tank assignment - null/empty means no tank selected (empty dropdown)
                    if (
                        data.tank !== undefined &&
                        data.tank !== null &&
                        data.tank !== '' &&
                        data.tank !== 'null' &&
                        data.tank !== 'None'
                    ) {
                        existingTankSelect.value = data.tank;
                        
                        // Add visual confirmation that tank was preserved
                        existingTankSelect.style.backgroundColor = '#d4edda'; // Light green
                        existingTankSelect.style.transition = 'background-color 2s ease';
                        setTimeout(() => {
                            existingTankSelect.style.backgroundColor = '';
                        }, 2000);
                    } else {
                        // No tank assigned - set to empty which should select the default "no selection" option
                        existingTankSelect.value = '';
                        
                        // If that doesn't work, try to find and select the first option (usually the default)
                        if (existingTankSelect.selectedIndex === -1 && existingTankSelect.options.length > 0) {
                            existingTankSelect.selectedIndex = 0;
                        }
                        
                        // Add visual confirmation that "None" was selected
                        existingTankSelect.style.backgroundColor = '#f8f9fa'; // Light gray
                        existingTankSelect.style.transition = 'background-color 2s ease';
                        setTimeout(() => {
                            existingTankSelect.style.backgroundColor = '';
                        }, 2000);
                    }
                } else {
                    if (!isScheduleNote) {
                        console.warn(`⚠️ Could not find tank select dropdown in existing row`);
                    } else {
                        this._applyRowClassesFromData(duplicateRow, data);
                        this._applyScheduleNoteLayout(duplicateRow, data);
                        return;
                    }
                }
            }
            
            return; // Exit after updating existing row
        }

        // Build a fresh row for insertion (clone template or fallback)
        const newRow = this._buildRowForStructuredInsert(
            tableBody,
            data,
            targetBlendId,
            resolvedLotRecordId
        );

        if (!newRow) {
            console.error('❌ Failed to construct structured row for payload:', data);
            return;
        }

        if (data.order !== undefined && data.order !== null) {
            const orderCell = newRow.querySelector('.orderCell') || newRow.querySelector('td:first-child');
            if (orderCell) {
                orderCell.textContent = data.order;
            }
        }

        // Ensure Manage... dropdown links target the new blend id/area (desk schedules)
        if (!this.isLotRecordsPage()) {
            this._rewriteManagementLinks(newRow, targetArea, targetBlendId);
        }

        if (!this.isLotRecordsPage()) {
            const cells = Array.from(newRow.querySelectorAll('td'));
            if (cells.length >= 3) {
                const itemCodeCell = cells[1];
                if (itemCodeCell) {
                    itemCodeCell.textContent = data.item_code || '';
                }

                const descriptionCell = cells[2];
                if (descriptionCell) {
                    descriptionCell.textContent = data.item_description || '';
                }
            }

            const tankSelect = newRow.querySelector('.tankSelect');
            if (tankSelect) {
                if (isScheduleNote) {
                    const tankCell = tankSelect.closest('td') || tankSelect.parentElement;
                    if (tankCell) {
                        tankCell.textContent = '******';
                    } else {
                        tankSelect.remove();
                    }
                } else {
                    const desiredTank = data.tank;
                    if (desiredTank && !['null', 'None', ''].includes(desiredTank)) {
                        tankSelect.value = desiredTank;
                        if (tankSelect.value !== desiredTank) {
                            const existingOption = Array.from(tankSelect.options).find(
                                (option) => option.value === desiredTank || option.text === desiredTank
                            );
                            if (!existingOption) {
                                const option = document.createElement('option');
                                option.value = desiredTank;
                                option.textContent = desiredTank;
                                tankSelect.appendChild(option);
                            }
                            tankSelect.value = desiredTank;
                        }
                    } else {
                        tankSelect.value = '';
                        if (tankSelect.selectedIndex === -1 && tankSelect.options.length > 0) {
                            tankSelect.selectedIndex = 0;
                        }
                    }
                }
            }

            if (isScheduleNote) {
                this._applyScheduleNoteLayout(newRow, data);
            }
        }

        // Re-apply row classes after layout tweaks to ensure styling is correct
        this._applyRowClassesFromData(newRow, data);

        // Find the correct position to insert the row based on order
        const existingRows = Array.from(tableBody.querySelectorAll('tr[data-blend-id]'));
        let insertPosition = existingRows.length; // Default to end
        
        for (let i = 0; i < existingRows.length; i++) {
            const existingOrderCell = existingRows[i].querySelector('td:first-child, .orderCell');
            const existingOrder = parseInt(existingOrderCell?.textContent || '999', 10);
            if (data.order < existingOrder) {
                insertPosition = i;
                break;
            }
        }
        
        // Insert the row at the correct position
        if (insertPosition >= existingRows.length) {
            tableBody.appendChild(newRow);
        } else {
            tableBody.insertBefore(newRow, existingRows[insertPosition]);
        }

        if (typeof window.attachLotRecordDeleteHandler === 'function') {
            window.attachLotRecordDeleteHandler(newRow);
        }
        
        // Add visual feedback - blue highlight that fades to normal
        newRow.style.backgroundColor = '#cce5ff';
        newRow.style.transition = 'background-color 2s ease';
        
        setTimeout(() => {
            newRow.style.backgroundColor = '';
        }, 2000);
        
        const normalizedBlendId = data.new_blend_id || data.blend_id;

        // Ensure inline datasets reflect the new payload
        const lotInfoPayload = {
            blend_id: normalizedBlendId,
            lot_number: data.lot_number,
            item_code: data.item_code,
            item_description: data.item_description,
            quantity: data.quantity,
            line: data.line,
            blend_area: data.new_blend_area || data.blend_area,
            run_date: data.run_date,
            lot_num_record_id: data.lot_num_record_id || data.lot_id,
            lot_id: data.lot_num_record_id || data.lot_id,
            has_been_printed: data.has_been_printed,
            last_print_event_str: data.last_print_event_str,
            print_history_json: data.print_history_json,
            was_edited_after_last_print: data.was_edited_after_last_print
        };
        this.updateLotInfo(lotInfoPayload);

        if (
            normalizedBlendId !== undefined &&
            (data.has_been_printed !== undefined ||
                data.last_print_event_str !== undefined ||
                data.print_history_json !== undefined)
        ) {
            this.updateBlendStatus({
                blend_id: normalizedBlendId,
                has_been_printed: data.has_been_printed ?? false,
                last_print_event_str:
                    data.last_print_event_str !== undefined
                        ? data.last_print_event_str
                        : '<em>Not Printed</em>',
                print_history_json: data.print_history_json ?? '[]',
                was_edited_after_last_print: data.was_edited_after_last_print
            });
        }

        const statusElements = newRow.querySelectorAll('.blend-sheet-status');
        statusElements.forEach((statusEl) => {
            if (resolvedLotRecordId) {
                statusEl.setAttribute('data-record-id', resolvedLotRecordId);
            } else {
                statusEl.removeAttribute('data-record-id');
            }
        });

        // Initialize tooltips for the new row's status elements
        this.initializeTooltipsForRow(newRow);
        
        // 🚰 Initialize tank selection event handlers for the new row
        if (!isScheduleNote) {
            this.initializeTankSelectForRow(newRow);
        }
        
        if (this.isLotRecordsPage()) {
            this._positionLotRecordsRow(newRow);
            this._removeDuplicateLotRows(newRow, targetBlendId, resolvedLotRecordId);
        }
        
        // Scroll the new row into view
        newRow.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center',
            inline: 'nearest'
        });
    }

    /**
     * Rebuilds schedule-management links (Manage... dropdown) on a newly cloned desk row
     * so they point at the correct blend id/area instead of the template row's values.
     */
    _rewriteManagementLinks(row, blendArea, blendId) {
        if (!row || !blendArea || !blendId) {
            return;
        }

        const links = row.querySelectorAll('a[href*="schedule-management-request"]');
        links.forEach((link) => {
            const href = link.getAttribute('href');
            if (!href) {
                return;
            }

            try {
                const url = new URL(href, window.location.origin);
                const pathParts = url.pathname.split('/').filter(Boolean);
                // Expected pattern: /core/schedule-management-request/<request_type>/<blend_area>/<blend_id>
                const requestType = pathParts[pathParts.length - 3];

                url.pathname = `/core/schedule-management-request/${requestType}/${blendArea}/${blendId}`;
                link.setAttribute('href', `${url.pathname}${url.search}`);
            } catch (error) {
                console.warn('⚠️ Failed to rewrite schedule-management link:', error, href);
            }
        });
    }

    handleScheduleReorder(data) {
        // 🎯 PROTECTION: Skip WebSocket reorder updates during manual sorting
        if (window.isDragging || (window.blendScheduleWS && window.blendScheduleWS.isDragging)) {
            console.log("🎯 Skipping WebSocket schedule reorder - manual sort in progress");
            return;
        }
        
        const blendArea = data.blend_area;
        const reorderedItems = data.reordered_items;
        const totalReordered = data.total_reordered;
        
        const currentPageArea = this.getCurrentPageArea();
        if (this.isLotRecordsPage()) {
            console.debug("Skipping schedule reorder handling on lot numbers page.");
            return;
        }
        if (currentPageArea === blendArea || currentPageArea === 'all') {
            const table = this.getTableForArea(blendArea);
            if (!table) {
                console.warn(`Could not find table for area: ${blendArea}`);
                return;
            }
            
            // Update order numbers in place
            reorderedItems.forEach(item => {
                let row = null;
                
                // Try to find row by blend_id first (for drag-and-drop updates)
                if (item.blend_id) {
                    row = table.querySelector(`tr[data-blend-id="${item.blend_id}"]`);
                }
                
                // If not found by blend_id, try to find by lot_number (for sort updates)
                if (!row && item.lot_number) {
                    // Look for lot number in the lot number cell (usually 5th column)
                    const lotCells = table.querySelectorAll('td.lot-number-cell, td[lot-number]');
                    for (let lotCell of lotCells) {
                        const lotNumber = lotCell.getAttribute('lot-number') || lotCell.textContent.trim();
                        if (lotNumber === item.lot_number) {
                            row = lotCell.closest('tr');
                            break;
                        }
                    }
                }
                
                if (row) {
                    // Update the order cell (usually first column)
                    const orderCell = row.querySelector('td:first-child');
                    if (orderCell) {
                        orderCell.textContent = item.new_order;
                        
                        // Add visual feedback for changed items
                        row.style.backgroundColor = '#fff3cd'; // Light yellow
                        setTimeout(() => {
                            row.style.backgroundColor = '';
                        }, 2000);
                    }
                } else {
                    console.warn(`⚠️ Could not find row for item:`, item);
                }
            });
            
            // Re-sort the table rows based on new order
            this.resortTableByOrder(table);
            
            // Show subtle notification
            this.showOrderUpdateNotification(totalReordered, blendArea, data.update_source);
        }
    }

    getTableForArea(blendArea) {
        const currentPageArea = this.getCurrentPageArea();
        const isLotRecordsPage = this.isLotRecordsPage();

        if (isLotRecordsPage) {
            return (
                document.querySelector('.table-responsive-sm table') ||
                document.querySelector('table.table') ||
                document.querySelector('table')
            );
        }
        
        if (currentPageArea === 'all') {
            // 🎯 ENHANCED: On "all schedules" page, find table within specific tab container
            let containerSelector;
            if (blendArea === 'Desk_1') {
                containerSelector = '#desk1Container #desk1ScheduleTable';
            } else if (blendArea === 'Desk_2') {
                containerSelector = '#desk2Container #desk2ScheduleTable';
            } else if (blendArea === 'LET_Desk') {
                containerSelector = '#LETDeskContainer #letDeskScheduleTable';
            } else if (blendArea === 'Hx') {
                containerSelector = '#horixContainer table';
            } else if (blendArea === 'Dm') {
                containerSelector = '#drumsContainer table';
            } else if (blendArea === 'Totes') {
                containerSelector = '#totesContainer table';
            } else {
                console.warn(`⚠️ Unknown blend area for all schedules page: ${blendArea}`);
                return null;
            }
            
            const table = document.querySelector(containerSelector);
            if (!table) {
                console.warn(`⚠️ Could not find table for ${blendArea} in all schedules page using selector: ${containerSelector}`);
            }
            return table;
        } else {
            // On individual desk pages, use the standard logic
            if (blendArea === 'Desk_1' || blendArea === 'Desk_2' || blendArea === 'LET_Desk') {
                return document.querySelector('#deskScheduleTable');
            }
            // For other areas, find the main table
            return document.querySelector('table');
        }
    }

    resortTableByOrder(table) {
        const tbody = table.querySelector('tbody');
        if (!tbody) return;
        
        // Get all rows except header
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        // Sort rows by order number (first cell)
        rows.sort((a, b) => {
            const orderA = parseInt(a.querySelector('td:first-child')?.textContent || '999', 10);
            const orderB = parseInt(b.querySelector('td:first-child')?.textContent || '999', 10);
            return orderA - orderB;
        });
        
        // Clear tbody and re-append in correct order
        tbody.innerHTML = '';
        rows.forEach(row => tbody.appendChild(row));
    }

    showOrderUpdateNotification(totalReordered, blendArea, updateSource = null) {
        // Create a subtle notification banner
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 4px;
            padding: 10px 15px;
            color: #155724;
            font-weight: 500;
            z-index: 9999;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            transition: opacity 0.3s ease;
        `;
        
        // Customize message based on update source
        let message = `Schedule updated: ${totalReordered} items reordered in ${blendArea}`;
        if (updateSource === 'manual_sort') {
            message = `🎯 Sort applied: ${totalReordered} items reordered in ${blendArea}`;
        }
        
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Fade out and remove after 3 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    initializeTooltipsForRow(row) {
        // Find all blend-sheet-status elements in this specific row
        const statusElements = row.querySelectorAll('.blend-sheet-status');
        
        statusElements.forEach(statusSpan => {
            try {
                // Dispose of any existing tooltip to prevent conflicts
                const existingTooltip = bootstrap.Tooltip.getInstance(statusSpan);
                if (existingTooltip) {
                    existingTooltip.dispose();
                }

                const printHistoryJSON = statusSpan.getAttribute('data-print-history');
                const hasBeenPrinted = statusSpan.getAttribute('data-has-been-printed') === 'true';
                let tooltipTitle;

                // Get current user for tooltip personalization
                const rawCurrentUser = window.currentUserUsername || null;
                const currentUser = rawCurrentUser ? rawCurrentUser.trim() : null;

                if (printHistoryJSON && printHistoryJSON !== 'null' && printHistoryJSON.trim() !== '') {
                    try {
                        const printHistory = JSON.parse(printHistoryJSON);
                        if (Array.isArray(printHistory) && printHistory.length > 0) {
                            let historyHtml = '<table class="tooltip-table"><thead><tr><th>User</th><th>Timestamp</th></tr></thead><tbody>';
                            printHistory.forEach(entry => {
                                const printedAt = entry.printed_at ? new Date(entry.printed_at).toLocaleString() : (entry.timestamp ? new Date(entry.timestamp).toLocaleString() : 'N/A');
                                
                                let printerDisplay = 'Unknown User';
                                const originalPrintedByUsername = entry.printed_by_username;
                                const userFromEntry = entry.user;

                                if (originalPrintedByUsername) { 
                                    const trimmedOriginalUsername = originalPrintedByUsername.trim();
                                    if (currentUser && trimmedOriginalUsername.toLowerCase() === currentUser.toLowerCase()) {
                                        printerDisplay = "(You)"; 
                                    } else {
                                        printerDisplay = trimmedOriginalUsername; 
                                    }
                                } else if (userFromEntry) {
                                    const trimmedUserFromEntry = userFromEntry.trim();
                                    if (currentUser && trimmedUserFromEntry.toLowerCase() === currentUser.toLowerCase()) {
                                        printerDisplay = "(You)";
                                    } else if (trimmedUserFromEntry === "You") {
                                        printerDisplay = "(You)"; 
                                    } else {
                                        printerDisplay = trimmedUserFromEntry;
                                    }
                                } 
                                
                                historyHtml += `<tr><td>${printerDisplay}</td><td>${printedAt}</td></tr>`;
                            });
                            historyHtml += '</tbody></table>';
                            tooltipTitle = historyHtml;

                            // Add visual indicator for multiple prints
                            if (printHistory.length > 1) {
                                statusSpan.classList.add('has-multiple-prints');
                            } else {
                                statusSpan.classList.remove('has-multiple-prints');
                            }
                        } else if (hasBeenPrinted) {
                            tooltipTitle = 'Printed (detailed history unavailable).';
                            statusSpan.classList.remove('has-multiple-prints');
                        } else {
                            tooltipTitle = 'Blend sheet has not been printed.';
                            statusSpan.classList.remove('has-multiple-prints');
                        }
                    } catch (e) {
                        console.error("Error parsing print history JSON:", e, printHistoryJSON);
                        tooltipTitle = "Error loading print history.";
                        statusSpan.classList.remove('has-multiple-prints');
                    }
                } else if (hasBeenPrinted) {
                    tooltipTitle = 'Printed (detailed history unavailable).';
                    statusSpan.classList.remove('has-multiple-prints');
                } else {
                    tooltipTitle = 'Blend sheet has not been printed.';
                    statusSpan.classList.remove('has-multiple-prints');
                }

                if (tooltipTitle) {
                    // Create new Bootstrap tooltip with the same configuration as the main page
                    const newTooltip = new bootstrap.Tooltip(statusSpan, {
                        title: tooltipTitle,
                        html: true,
                        sanitize: false,
                        trigger: 'hover focus',
                        placement: 'top',
                        boundary: 'scrollParent',
                        customClass: 'print-history-tooltip',
                        container: 'body'
                    });
                    
                    // Update the data attribute for Bootstrap's internal tracking
                    statusSpan.setAttribute('data-bs-original-title', tooltipTitle);
                } else {
                    console.warn(`⚠️ No tooltip title generated for status element`);
                }
            } catch (error) {
                console.error(`❌ Error initializing tooltip for status element:`, error);
            }
        });
    }

    initializeTooltipForElement(statusSpan) {
        try {
            // Dispose of any existing tooltip to prevent conflicts
            const existingTooltip = bootstrap.Tooltip.getInstance(statusSpan);
            if (existingTooltip) {
                existingTooltip.dispose();
            }

            const printHistoryJSON = statusSpan.getAttribute('data-print-history');
            const hasBeenPrinted = statusSpan.getAttribute('data-has-been-printed') === 'true';
            let tooltipTitle;

            // Get current user for tooltip personalization
            const rawCurrentUser = window.currentUserUsername || null;
            const currentUser = rawCurrentUser ? rawCurrentUser.trim() : null;

            if (printHistoryJSON && printHistoryJSON !== 'null' && printHistoryJSON.trim() !== '') {
                try {
                    const printHistory = JSON.parse(printHistoryJSON);
                    if (Array.isArray(printHistory) && printHistory.length > 0) {
                        let historyHtml = '<table class="tooltip-table"><thead><tr><th>User</th><th>Timestamp</th></tr></thead><tbody>';
                        printHistory.forEach(entry => {
                            const printedAt = entry.printed_at ? new Date(entry.printed_at).toLocaleString() : (entry.timestamp ? new Date(entry.timestamp).toLocaleString() : 'N/A');
                            
                            let printerDisplay = 'Unknown User';
                            const originalPrintedByUsername = entry.printed_by_username;
                            const userFromEntry = entry.user;

                            if (originalPrintedByUsername) { 
                                const trimmedOriginalUsername = originalPrintedByUsername.trim();
                                if (currentUser && trimmedOriginalUsername.toLowerCase() === currentUser.toLowerCase()) {
                                    printerDisplay = "(You)"; 
                                } else {
                                    printerDisplay = trimmedOriginalUsername; 
                                }
                            } else if (userFromEntry) {
                                const trimmedUserFromEntry = userFromEntry.trim();
                                if (currentUser && trimmedUserFromEntry.toLowerCase() === currentUser.toLowerCase()) {
                                    printerDisplay = "(You)";
                                } else if (trimmedUserFromEntry === "You") {
                                    printerDisplay = "(You)"; 
                                } else {
                                    printerDisplay = trimmedUserFromEntry;
                                }
                            } 
                            
                            historyHtml += `<tr><td>${printerDisplay}</td><td>${printedAt}</td></tr>`;
                        });
                        historyHtml += '</tbody></table>';
                        tooltipTitle = historyHtml;

                        // Add visual indicator for multiple prints
                        if (printHistory.length > 1) {
                            statusSpan.classList.add('has-multiple-prints');
                        } else {
                            statusSpan.classList.remove('has-multiple-prints');
                        }
                    } else if (hasBeenPrinted) {
                        tooltipTitle = 'Printed (detailed history unavailable).';
                        statusSpan.classList.remove('has-multiple-prints');
                    } else {
                        tooltipTitle = 'Blend sheet has not been printed.';
                        statusSpan.classList.remove('has-multiple-prints');
                    }
                } catch (e) {
                    console.error("Error parsing print history JSON:", e, printHistoryJSON);
                    tooltipTitle = "Error loading print history.";
                    statusSpan.classList.remove('has-multiple-prints');
                }
            } else if (hasBeenPrinted) {
                tooltipTitle = 'Printed (detailed history unavailable).';
                statusSpan.classList.remove('has-multiple-prints');
            } else {
                tooltipTitle = 'Blend sheet has not been printed.';
                statusSpan.classList.remove('has-multiple-prints');
            }

            if (tooltipTitle) {
                // Create new Bootstrap tooltip with the same configuration as the main page
                const newTooltip = new bootstrap.Tooltip(statusSpan, {
                    title: tooltipTitle,
                    html: true,
                    sanitize: false,
                    trigger: 'hover focus',
                    placement: 'top',
                    boundary: 'scrollParent',
                    customClass: 'print-history-tooltip',
                    container: 'body'
                });
                
                // Update the data attribute for Bootstrap's internal tracking
                statusSpan.setAttribute('data-bs-original-title', tooltipTitle);
            } else {
                console.warn(`⚠️ No tooltip title generated for single status element`);
            }
        } catch (error) {
            console.error(`❌ Error initializing tooltip for single status element:`, error);
        }
    }

    initializeTankSelectForRow(row) {
        if (this.isLotRecordsPage()) {
            return;
        }
        try {
            const tankSelect = row.querySelector('.tankSelect');
            if (!tankSelect) {
                console.warn(`⚠️ No tank select dropdown found in row`);
                return;
            }
            
            // Remove any existing event handlers to prevent duplicates
            $(tankSelect).off('change.websocket focus.websocket');
            
            // Add change event handler with namespace for easy removal
            $(tankSelect).on('change.websocket', function() {
                const $this = $(this);
                const $row = $this.closest('tr');
                
                // Use data-blend-id for reliable identification
                const blendId = $row.attr('data-blend-id');
                const lotNumber = $row.find('.lot-number-cell').attr('lot-number') || $row.find('td:eq(4)').text().trim();
                const tank = $this.val();
                const blendArea = new URL(window.location.href).searchParams.get("blend-area");
                
                // Encode parameters for backend
                const encodedLotNumber = btoa(lotNumber);
                const encodedTank = btoa(tank);
                
                // Add visual feedback during update
                $this.css({
                    'backgroundColor': '#fff3cd',
                    'transition': 'background-color 0.3s ease'
                });
                
                $.ajax({
                    url: `/core/update-scheduled-blend-tank?encodedLotNumber=${encodedLotNumber}&encodedTank=${encodedTank}&blendArea=${blendArea}`,
                    type: 'GET',
                    dataType: 'json',
                    success: function(data) {
                        // Clear visual feedback on success
                        setTimeout(() => {
                            $this.css('backgroundColor', '');
                        }, 1000);
                    },
                    error: function(xhr, status, error) {
                        console.error(`❌ Tank update failed (WebSocket row):`, error);
                        
                        // Revert selection on error
                        $this.val($this.data('previous-value') || '');
                        
                        // Show error feedback
                        $this.css('backgroundColor', '#ffcccc');
                        setTimeout(() => {
                            $this.css('backgroundColor', '');
                        }, 2000);
                        
                        alert(`Failed to update tank assignment: ${error}`);
                    }
                });
            });
            
            // Add focus event handler to store previous value for error recovery
            $(tankSelect).on('focus.websocket', function() {
                $(this).data('previous-value', $(this).val());
            });
            
        } catch (error) {
            console.error(`❌ Error initializing tank selection for row:`, error);
        }
    }

    getCurrentPageArea() {
        const url = window.location.href;
        
        if (url.includes('blend-area=Desk_1')) {
            return 'Desk_1';
        }
        if (url.includes('blend-area=Desk_2')) {
            return 'Desk_2';
        }
        if (url.includes('blend-area=LET_Desk')) {
            return 'LET_Desk';
        }
        if (url.includes('blend-area=Hx')) {
            return 'Hx';
        }
        if (url.includes('blend-area=Dm')) {
            return 'Dm';
        }
        if (url.includes('blend-area=Totes')) {
            return 'Totes';
        }
        if (url.includes('blend-area=Pails')) {
            return 'Pails';
        }
        if (url.includes('blend-area=all')) {
            return 'all';
        }
        
        // Enhanced fallback detection
        if (url.includes('/drumschedule') || url.includes('drum')) {
            return 'Dm';
        }
        if (url.includes('/horixschedule') || url.includes('horix')) {
            return 'Hx';
        }
        if (url.includes('/deskoneschedule') || url.includes('desk') && url.includes('one')) {
            return 'Desk_1';
        }
        if (url.includes('/desktwoschedule') || url.includes('desk') && url.includes('two')) {
            return 'Desk_2';
        }
        if (url.includes('/toteschedule') || url.includes('tote')) {
            return 'Totes';
        }
        if (url.includes('/allschedules') || url.includes('all')) {
            return 'all';
        }
        
        return 'all';
    }

    isLotRecordsPage() {
        return window.location.pathname.includes('/lot-num-records');
    }

    getTableBodyForArea(blendArea) {
        const currentPageArea = this.getCurrentPageArea();
        const isLotRecordsPage = this.isLotRecordsPage();

        if (isLotRecordsPage) {
            const lotTableBody =
                document.querySelector('.table-responsive-sm table tbody') ||
                document.querySelector('table.table tbody') ||
                document.querySelector('table tbody');

            if (!lotTableBody) {
                console.warn('⚠️ Could not locate lot numbers table body on lot-num-records page');
            }
            return lotTableBody;
        }
        
        if (currentPageArea === 'all') {
            // 🎯 ENHANCED: On "all schedules" page, find table within specific tab container
            let containerSelector;
            if (blendArea === 'Desk_1') {
                containerSelector = '#desk1Container #desk1ScheduleTable tbody';
            } else if (blendArea === 'Desk_2') {
                containerSelector = '#desk2Container #desk2ScheduleTable tbody';
            } else if (blendArea === 'LET_Desk') {
                containerSelector = '#LETDeskContainer #letDeskScheduleTable tbody';
            } else if (blendArea === 'Hx') {
                containerSelector = '#horixContainer table tbody';
            } else if (blendArea === 'Dm') {
                containerSelector = '#drumsContainer table tbody';
            } else if (blendArea === 'Totes') {
                containerSelector = '#totesContainer table tbody';
            } else {
                console.warn(`⚠️ Unknown blend area for all schedules page: ${blendArea}`);
                return null;
            }
            
            const tableBody = document.querySelector(containerSelector);
            if (!tableBody) {
                console.warn(`⚠️ Could not find table body for ${blendArea} in all schedules page using selector: ${containerSelector}`);
            }
            return tableBody;
        } else {
            // On individual pages, prefer schedule tables and ignore modal content
            if (blendArea === 'Desk_1' || blendArea === 'Desk_2' || blendArea === 'LET_Desk') {
                const deskTable = document.querySelector('#deskScheduleTable tbody');
                if (deskTable) {
                    return deskTable;
                }
            }

            const responsiveTables = Array.from(document.querySelectorAll('.table-responsive-sm table tbody')).filter(
                (tbody) => !tbody.closest('.modal')
            );
            if (responsiveTables.length) {
                return responsiveTables[0];
            }

            const nonModalTables = Array.from(document.querySelectorAll('table tbody')).filter(
                (tbody) => !tbody.closest('.modal')
            );
            return nonModalTables[0] || null;
        }
    }

}
