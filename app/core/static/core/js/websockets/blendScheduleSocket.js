import { BaseSocket } from '../../../shared/js/websockets/BaseSocket.js';
import { StateCache } from '../../../shared/js/websockets/StateCache.js';
import {
    buildWebSocketUrl,
    sanitizeForJson,
    updateConnectionIndicator,
} from '../../../shared/js/websockets/helpers.js';

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
        let shouldProcess = false;

        if (currentPageArea === 'all') {
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
        const blendId = data.blend_id;
        const row = document.querySelector(`tr[data-blend-id="${blendId}"]`);

        if (!row) {
            console.warn(`No row found for blend_id: ${blendId}`);
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

    removeBlend(data) {
        const blendId = data.blend_id;
        const row = document.querySelector(`tr[data-blend-id="${blendId}"]`);
        if (row) {
            row.style.backgroundColor = '#ffcccc';
            setTimeout(() => {
                row.remove();
            }, 1000);
        }
    }

    addBlend(data) {
        const htmlRow = data.html_row;
        const blendArea = data.blend_area || data.new_blend_area;
        
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

        let row = document.querySelector(`tr[data-blend-id="${oldBlendId}"]`);
        if (!row && newBlendId !== oldBlendId) {
            row = document.querySelector(`tr[data-blend-id="${newBlendId}"]`);
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
        this._positionLotRecordsRow(row);
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
        this._positionLotRecordsRow(row);
        this._removeDuplicateLotRows(row, normalizedBlendId, resolvedLotRecordId);

        row.style.backgroundColor = '#cce5ff';
        row.style.transition = 'background-color 2s ease';
        setTimeout(() => {
            row.style.backgroundColor = '';
        }, 2000);
    }

    _positionLotRecordsRow(row) {
        if (!row) {
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
                    console.warn(`⚠️ Could not find tank select dropdown in existing row`);
                }
            }
            
            return; // Exit after updating existing row
        }
        
        // Find an existing row to clone as a template
        const existingRow = this._findTemplateRow(tableBody, targetBlendId);
        
        if (!existingRow) {
            console.error(`❌ Could not find existing row to clone for table structure`);
            return;
        }
        
        // Clone the existing row for perfect structure preservation
        const newRow = existingRow.cloneNode(true);
        newRow.setAttribute('data-blend-id', targetBlendId);
        
        // Update the data-blend-id attributes in all child elements
        const elementsWithDataAttr = newRow.querySelectorAll('[data-blend-id]');
        elementsWithDataAttr.forEach(el => {
            el.setAttribute('data-blend-id', targetBlendId);
        });

        const deskLines = ['Desk_1', 'Desk_2', 'LET_Desk'];
        const lineContext = data.line || targetArea || '';
        const isDeskContext =
            deskLines.includes(lineContext) ||
            deskLines.includes(targetArea) ||
            (!data.line && !targetArea);
        const rawQuantity = data.quantity;
        let numericQuantity = NaN;
        
        // Apply row styling classes from WebSocket data
        if (data.row_classes) {
            // Clear existing classes that might conflict
            newRow.className = '';
            // Apply the classes from the server
            newRow.className = data.row_classes;
        } else {
            // Fallback: Apply essential classes based on template pattern
            const essentialClasses = ['tableBodyRow'];
            
            // Add blend area class (Desk_1, Desk_2, LET_Desk)
            if (targetArea) {
                essentialClasses.push(targetArea);
            }
            
            // Try to preserve line-specific styling from original row if available
            if (existingRow && existingRow.className) {
                const lineRowMatch = existingRow.className.match(/(\w+)Row/);
                if (lineRowMatch && lineRowMatch[1] !== 'tableBody') {
                    essentialClasses.push(lineRowMatch[0]); // Add the full match (e.g., 'ProdRow')
                }
            }
            
            // Apply urgent styling if indicated
            if (data.is_urgent) {
                essentialClasses.push('priorityMessage');
            }
            
            // Apply special item styling
            if (data.item_code === "******") {
                essentialClasses.push('NOTE');
            } else if (data.item_code === "!!!!!") {
                essentialClasses.push('priorityMessage');
            }
            
            newRow.className = essentialClasses.join(' ');
        }
        
        // Update order number (first cell)
        const orderCell = newRow.querySelector('td:first-child, .orderCell');
        if (orderCell) {
            orderCell.textContent = data.order;
        }
        
        // Update item code (second cell typically)
        const itemCodeCell = newRow.querySelector('td:nth-child(2)');
        if (itemCodeCell) {
            itemCodeCell.textContent = data.item_code;
        }
        
        // Update item description 
        const descriptionCell = newRow.querySelector('td:nth-child(3)');
        if (descriptionCell) {
            descriptionCell.textContent = data.item_description;
        }
        
        // Update lot number cell
        const lotCell = newRow.querySelector('.lot-number-cell, td[lot-number]');
        if (lotCell) {
            lotCell.setAttribute('lot-number', data.lot_number);
            // Update the text content, preserving any inner structure
            const lotTextNodes = Array.from(lotCell.childNodes).filter(node => node.nodeType === Node.TEXT_NODE);
            if (lotTextNodes.length > 0) {
                lotTextNodes[0].textContent = data.lot_number;
            } else {
                // Fallback: find the text content area
                const lotTextElement = lotCell.querySelector('span, div') || lotCell;
                if (lotTextElement !== lotCell) {
                    lotTextElement.textContent = data.lot_number;
                } else {
                    lotCell.textContent = data.lot_number;
                }
            }
        }
        
        // Update quantity - ensure proper formatting and handling
        const quantityCell = newRow.querySelector('.quantity-cell, td.quantity-cell');
        if (quantityCell) {
            if (rawQuantity !== undefined && rawQuantity !== null && rawQuantity !== '') {
                numericQuantity = parseFloat(rawQuantity);
                if (!Number.isNaN(numericQuantity)) {
                    const formattedQuantity = numericQuantity.toFixed(isDeskContext ? 1 : 0);
                    quantityCell.textContent = isDeskContext ? `${formattedQuantity} gal` : formattedQuantity;
                } else {
                    quantityCell.textContent = '0.0 gal';
                    console.warn(`⚠️ Invalid quantity value: ${rawQuantity}, defaulting to 0.0 gal`);
                }
            } else {
                quantityCell.textContent = '0.0 gal';
                console.warn(`⚠️ No quantity data provided, defaulting to 0.0 gal`);
            }
        } else {
            console.warn(`⚠️ Could not find quantity cell in new row`);
        }
        
        // Update blend status with proper data attributes for tooltips
        const statusSpan = newRow.querySelector('.blend-sheet-status');
        if (statusSpan) {
            statusSpan.setAttribute('data-has-been-printed', data.has_been_printed);
            statusSpan.setAttribute('data-print-history', data.print_history_json || '[]');
            statusSpan.setAttribute('data-record-id', resolvedLotRecordId);
            statusSpan.innerHTML = data.last_print_event_str;
            
            // Add the edited indicator if needed
            if (data.was_edited_after_last_print) {
                statusSpan.innerHTML += '<sup class="edited-after-print-indicator">!</sup>';
            }
        }
        
        // Update Short column (8th column) with hourshort value from frontend
        const shortCell = newRow.querySelector('td:nth-child(8)');
        if (shortCell) {
            // Clear existing content to prevent contamination from cloned row
            shortCell.textContent = '';
            shortCell.removeAttribute('data-hour-short');
            
            if (data.hourshort !== undefined && data.hourshort !== null) {
                // Set the data-hour-short attribute with the value from frontend
                shortCell.setAttribute('data-hour-short', parseFloat(data.hourshort).toFixed(1));
                
                // Determine what to display based on line type and item description
                let shortDisplayValue;
                
                if (data.line && data.line !== 'Prod') {
                    // For non-Prod lines, show run date
                    if (data.run_date) {
                        const runDate = new Date(data.run_date);
                        shortDisplayValue = `${(runDate.getMonth() + 1).toString().padStart(2, '0')}/${runDate.getDate().toString().padStart(2, '0')}/${runDate.getFullYear().toString().slice(-2)}`;
                    } else {
                        shortDisplayValue = 'N/A';
                    }
                } else if (data.item_description && data.item_description.includes('LET') && data.item_description.includes('(kinpak)')) {
                    // For LET kinpak items, show run date
                    if (data.run_date) {
                        const runDate = new Date(data.run_date);
                        shortDisplayValue = `${(runDate.getMonth() + 1).toString().padStart(2, '0')}/${runDate.getDate().toString().padStart(2, '0')}/${runDate.getFullYear().toString().slice(-2)}`;
                    } else {
                        shortDisplayValue = 'N/A';
                    }
                } else {
                    // For regular Prod line items, show hourshort value (from frontend)
                    shortDisplayValue = parseFloat(data.hourshort).toFixed(1);
                }
                
                shortCell.textContent = shortDisplayValue;
            } else {
                // No hourshort data provided - set a placeholder
                shortCell.textContent = 'N/A';
                console.warn(`⚠️ No hourshort data provided from frontend, set to N/A`);
            }
        } else {
            console.error(`❌ Could not find Short column (8th column) in new row`);
            // Debug: Show all cells in the row
            const allCells = newRow.querySelectorAll('td');
            console.log(`🔍 Row has ${allCells.length} cells:`, Array.from(allCells).map((cell, index) => `${index + 1}: "${cell.textContent.trim()}"`));
        }
        
        // Update any dropdown IDs to be unique
        const dropdownButtons = newRow.querySelectorAll('[id*="dropdown"], [id*="Dropdown"]');
        dropdownButtons.forEach(button => {
            const oldId = button.id;
            const newId = oldId.replace(/\d+$/, data.new_blend_id);
            button.id = newId;
            
            // Update any aria-labelledby references
            const relatedElements = newRow.querySelectorAll(`[aria-labelledby="${oldId}"]`);
            relatedElements.forEach(el => {
                el.setAttribute('aria-labelledby', newId);
            });
        });
        
                // Update tank selection dropdown
        const tankSelect = newRow.querySelector('.tankSelect');
        if (tankSelect) {
            // Clear existing selection to prevent contamination from cloned row
            tankSelect.value = '';
            
            // Handle tank assignment - null/empty means no tank selected (empty dropdown)
            if (data.tank !== undefined && data.tank !== null && data.tank !== '' && data.tank !== 'null' && data.tank !== 'None') {
                // Set the tank value from WebSocket data
                tankSelect.value = data.tank;
                
                // Add visual confirmation that tank was preserved
                tankSelect.style.backgroundColor = '#d4edda'; // Light green
                tankSelect.style.transition = 'background-color 2s ease';
                setTimeout(() => {
                    tankSelect.style.backgroundColor = '';
                }, 2000);
            } else {
                // No tank assigned - set to empty which should select the default "no selection" option
                tankSelect.value = '';
                
                // If that doesn't work, try to find and select the first option (usually the default)
                if (tankSelect.selectedIndex === -1 && tankSelect.options.length > 0) {
                    tankSelect.selectedIndex = 0;
                }
                
                // Add visual confirmation that "None" was selected
                tankSelect.style.backgroundColor = '#f8f9fa'; // Light gray
                tankSelect.style.transition = 'background-color 2s ease';
                setTimeout(() => {
                    tankSelect.style.backgroundColor = '';
                }, 2000);
            }
        } else {
            console.warn(`⚠️ Could not find tank select dropdown (.tankSelect) in new row`);
        }

        // Update management dropdown links
        const managementLinks = newRow.querySelectorAll('a[href*="schedule-management-request"]');
        managementLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href) {
                // Replace the old blend ID with the new one
                const newHref = href.replace(/\/\d+\?/, `/${data.new_blend_id}?`);
                link.setAttribute('href', newHref);
            }
        });
        
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
        
        // Add visual feedback - blue highlight that fades to normal
        newRow.style.backgroundColor = '#cce5ff';
        newRow.style.transition = 'background-color 2s ease';
        
        setTimeout(() => {
            newRow.style.backgroundColor = '';
        }, 2000);
        
        // Ensure inline datasets reflect the new payload
        this.updateLotInfo({
            blend_id: data.new_blend_id,
            lot_number: data.lot_number,
            item_code: data.item_code,
            item_description: data.item_description,
            quantity: data.quantity,
            line: data.line,
            blend_area: data.new_blend_area,
            run_date: data.run_date,
            lot_num_record_id: data.lot_num_record_id || data.lot_id,
            lot_id: data.lot_num_record_id || data.lot_id,
            has_been_printed: data.has_been_printed,
            last_print_event_str: data.last_print_event_str,
            print_history_json: data.print_history_json,
            was_edited_after_last_print: data.was_edited_after_last_print
        });

        // Initialize tooltips for the new row's status elements
        this.initializeTooltipsForRow(newRow);
        
        // 🚰 Initialize tank selection event handlers for the new row
        this.initializeTankSelectForRow(newRow);
        
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
            // On individual desk pages, use the standard logic
            if (blendArea === 'Desk_1' || blendArea === 'Desk_2' || blendArea === 'LET_Desk') {
                return document.querySelector('#deskScheduleTable tbody');
            }
            return document.querySelector('table tbody');
        }
    }

}
