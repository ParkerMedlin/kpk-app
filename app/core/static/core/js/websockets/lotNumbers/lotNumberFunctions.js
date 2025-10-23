export async function fetchLotRecordRow(lotId) {
    try {
        const response = await fetch(`/core/get-lot-num-record-row/${lotId}/`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `HTTP ${response.status}: Failed to fetch lot record row`);
        }

        const data = await response.json();
        
        if (data.status !== 'success') {
            throw new Error(data.message || 'Unknown error fetching lot record row');
        }

        return {
            html: data.html,
            lotNumber: data.lot_number,
            lotId: data.lot_id
        };

    } catch (error) {
        console.error(`Error fetching lot record row for lot ID ${lotId}:`, error);
        throw error;
    }
}

