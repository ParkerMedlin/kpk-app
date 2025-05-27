/**
 * Tank Selection Modal Handler
 * 
 * Provides elegant tank selection UI when moving blends between desks
 * with incompatible tank assignments.
 */

export class TankSelectionModal {
    constructor() {
        this.modalId = 'tankSelectionModal';
        this.currentMoveData = null;
        this.createModal();
        this.bindEvents();
        console.log("🚰 Tank Selection Modal initialized");
    }

    createModal() {
        // Remove existing modal if present
        const existingModal = document.getElementById(this.modalId);
        if (existingModal) {
            existingModal.remove();
        }

        // Create modal HTML with proper centering and navbar respect
        const modalHTML = `
            <div class="modal fade" id="${this.modalId}" tabindex="-1" aria-labelledby="${this.modalId}Label" aria-hidden="true" style="z-index: 1055;">
                <div class="modal-dialog modal-lg modal-dialog-centered" style="margin-top: 70px; margin-bottom: 70px;">
                    <div class="modal-content border-0 shadow-lg">
                        <div class="modal-header bg-warning text-dark">
                            <h5 class="modal-title" id="${this.modalId}Label">
                                <i class="fas fa-exclamation-triangle me-2"></i>
                                Tank Selection Required
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-info mb-4">
                                <h6 class="alert-heading">
                                    <i class="fas fa-info-circle me-2"></i>
                                    Tank Compatibility Issue
                                </h6>
                                <p class="mb-0">
                                    The current tank assignment is not available in the destination desk. 
                                    Please select a compatible tank from the list below.
                                </p>
                            </div>

                            <div class="row">
                                <div class="col-md-6">
                                    <div class="card border-secondary">
                                        <div class="card-header bg-secondary text-white">
                                            <h6 class="mb-0">
                                                <i class="fas fa-info-circle me-2"></i>
                                                Move Details
                                            </h6>
                                        </div>
                                        <div class="card-body">
                                            <table class="table table-sm table-borderless mb-0">
                                                <tr>
                                                    <td class="fw-bold">Item Code:</td>
                                                    <td id="tankModal-itemCode">-</td>
                                                </tr>
                                                <tr>
                                                    <td class="fw-bold">Description:</td>
                                                    <td id="tankModal-itemDescription">-</td>
                                                </tr>
                                                <tr>
                                                    <td class="fw-bold">Lot Number:</td>
                                                    <td id="tankModal-lotNumber">-</td>
                                                </tr>
                                                <tr>
                                                    <td class="fw-bold">Current Tank:</td>
                                                    <td>
                                                        <span id="tankModal-currentTank" class="badge bg-danger">-</span>
                                                    </td>
                                                </tr>
                                                <tr>
                                                    <td class="fw-bold">Destination:</td>
                                                    <td>
                                                        <span id="tankModal-destination" class="badge bg-primary">-</span>
                                                    </td>
                                                </tr>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card border-success">
                                        <div class="card-header bg-success text-white">
                                            <h6 class="mb-0">
                                                <i class="fas fa-list me-2"></i>
                                                Available Tanks
                                            </h6>
                                        </div>
                                        <div class="card-body">
                                            <div class="form-group">
                                                <label for="tankModal-tankSelect" class="form-label fw-bold">
                                                    Select Tank:
                                                </label>
                                                <select id="tankModal-tankSelect" class="form-select form-select-lg">
                                                    <option value="">-- Select a tank --</option>
                                                </select>
                                                <div class="form-text">
                                                    Choose a tank that is available in the destination desk.
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-danger" data-bs-dismiss="modal">
                                <i class="fas fa-times me-2"></i>
                                Cancel Move
                            </button>
                            <button type="button" id="tankModal-confirmMove" class="btn btn-success" disabled>
                                <i class="fas fa-check me-2"></i>
                                Confirm Move
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add modal to document
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Initialize Bootstrap modal
        this.modal = new bootstrap.Modal(document.getElementById(this.modalId), {
            backdrop: 'static',
            keyboard: false
        });
    }

    bindEvents() {
        // Tank selection change handler
        document.getElementById('tankModal-tankSelect').addEventListener('change', (e) => {
            const confirmButton = document.getElementById('tankModal-confirmMove');
            if (e.target.value) {
                confirmButton.disabled = false;
                confirmButton.classList.remove('btn-secondary');
                confirmButton.classList.add('btn-success');
            } else {
                confirmButton.disabled = true;
                confirmButton.classList.remove('btn-success');
                confirmButton.classList.add('btn-secondary');
            }
        });

        // Confirm move button handler
        document.getElementById('tankModal-confirmMove').addEventListener('click', () => {
            this.confirmMove();
        });

        // Modal hidden event - cleanup
        document.getElementById(this.modalId).addEventListener('hidden.bs.modal', () => {
            this.currentMoveData = null;
        });
    }

    show(moveData) {
        console.log("🚰 Showing tank selection modal with data:", moveData);
        
        this.currentMoveData = moveData;
        
        // Populate modal with move data
        document.getElementById('tankModal-itemCode').textContent = moveData.blend_info.item_code;
        document.getElementById('tankModal-itemDescription').textContent = moveData.blend_info.item_description;
        document.getElementById('tankModal-lotNumber').textContent = moveData.blend_info.lot_number;
        document.getElementById('tankModal-currentTank').textContent = moveData.original_tank;
        document.getElementById('tankModal-destination').textContent = moveData.destination_desk;

        // Populate tank options
        const tankSelect = document.getElementById('tankModal-tankSelect');
        tankSelect.innerHTML = '<option value="">-- Select a tank --</option>';
        
        // Add "None" option first
        const noneOption = document.createElement('option');
        noneOption.value = 'None';
        noneOption.textContent = 'None (No Tank Assignment)';
        noneOption.style.fontStyle = 'italic';
        //noneOption.style.color = '#6c757d';
        tankSelect.appendChild(noneOption);
        
        // Add separator option (disabled)
        const separatorOption = document.createElement('option');
        separatorOption.disabled = true;
        separatorOption.textContent = '──────────────────';
        tankSelect.appendChild(separatorOption);
        
        // Add available tanks
        moveData.available_tanks.forEach(tank => {
            const option = document.createElement('option');
            option.value = tank;
            option.textContent = tank;
            tankSelect.appendChild(option);
        });

        // Reset confirm button state
        const confirmButton = document.getElementById('tankModal-confirmMove');
        confirmButton.disabled = true;
        confirmButton.classList.remove('btn-success');
        confirmButton.classList.add('btn-secondary');

        // Show modal
        this.modal.show();
    }

    confirmMove() {
        const selectedTank = document.getElementById('tankModal-tankSelect').value;
        
        if (!selectedTank || !this.currentMoveData) {
            console.error("❌ No tank selected or no move data available");
            return;
        }

        console.log(`🚰 Confirming move with selected tank: ${selectedTank}`);

        // Disable confirm button and show loading state
        const confirmButton = document.getElementById('tankModal-confirmMove');
        const originalText = confirmButton.innerHTML;
        confirmButton.disabled = true;
        confirmButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';

        // Prepare move parameters
        const moveParams = new URLSearchParams({
            blend_area: this.currentMoveData.blend_info.blend_area,
            blend_id: this.currentMoveData.blend_info.blend_id,
            destination_desk: this.currentMoveData.destination_desk,
            selected_tank: selectedTank,
            hourshort: this.getHourshortValue()
        });

        // Execute the move
        fetch(`/core/move-blend-with-tank-selection/?${moveParams}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest' // Identify as AJAX request
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log("✅ Tank-aware blend move successful:", data);
                    
                    // Show success notification
                    const displayTank = selectedTank === 'None' ? 'No Tank Assignment' : selectedTank;
                    this.showNotification(
                        'success',
                        'Move Successful',
                        `Blend moved to ${this.currentMoveData.destination_desk} with tank: ${displayTank}`
                    );
                    
                    // Hide modal
                    this.modal.hide();
                    
                    // No page reload needed - WebSocket handles the updates!
                    // The blend_moved WebSocket message will automatically update the UI
                } else {
                    console.error("❌ Tank-aware blend move failed:", data);
                    this.showNotification('error', 'Move Failed', data.error || 'Unknown error occurred');
                    
                    // Restore button state
                    confirmButton.disabled = false;
                    confirmButton.innerHTML = originalText;
                }
            })
            .catch(error => {
                console.error("❌ Error during tank-aware blend move:", error);
                this.showNotification('error', 'Move Failed', 'Network error occurred');
                
                // Restore button state
                confirmButton.disabled = false;
                confirmButton.innerHTML = originalText;
            });
    }

    getHourshortValue() {
        // Try to extract hourshort value from the current row
        if (this.currentMoveData && this.currentMoveData.blend_info) {
            const blendId = this.currentMoveData.blend_info.blend_id;
            const row = document.querySelector(`tr[data-blend-id="${blendId}"]`);
            if (row) {
                const shortCell = row.querySelector('td[data-hour-short]');
                if (shortCell) {
                    return shortCell.getAttribute('data-hour-short');
                }
            }
        }
        return '999.0'; // Default fallback
    }

    showNotification(type, title, message) {
        // Create notification element
        const notificationId = `notification-${Date.now()}`;
        const bgClass = type === 'success' ? 'bg-success' : 'bg-danger';
        const iconClass = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
        
        const notificationHTML = `
            <div id="${notificationId}" class="position-fixed top-0 end-0 p-3" style="z-index: 9999;">
                <div class="toast show ${bgClass} text-white" role="alert">
                    <div class="toast-header ${bgClass} text-white border-0">
                        <i class="fas ${iconClass} me-2"></i>
                        <strong class="me-auto">${title}</strong>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                    </div>
                    <div class="toast-body">
                        ${message}
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', notificationHTML);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            const notification = document.getElementById(notificationId);
            if (notification) {
                notification.remove();
            }
        }, 5000);
    }

    hide() {
        if (this.modal) {
            this.modal.hide();
        }
    }

    destroy() {
        if (this.modal) {
            this.modal.dispose();
        }
        const modalElement = document.getElementById(this.modalId);
        if (modalElement) {
            modalElement.remove();
        }
    }
}

export default TankSelectionModal; 