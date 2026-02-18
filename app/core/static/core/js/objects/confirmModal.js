export function confirmAction(message) {
    return new Promise((resolve) => {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.setAttribute('tabindex', '-1');
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-body fs-5">${message}</div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">No</button>
                        <button type="button" class="btn btn-danger confirm-yes-btn">Yes</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        const bsModal = new bootstrap.Modal(modal);

        modal.querySelector('.confirm-yes-btn').addEventListener('click', () => {
            resolve(true);
            bsModal.hide();
        });

        modal.addEventListener('hidden.bs.modal', () => {
            resolve(false);
            modal.remove();
        }, { once: true });

        bsModal.show();
    });
}
