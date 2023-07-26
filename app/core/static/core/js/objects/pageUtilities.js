import { getItemCodesForCheckedBoxes } from '../uiFunctions/uiFunctions.js'

export class ShiftSelectCheckBoxes {
    constructor() {
        try {
            this.setUpCheckBoxes();
            console.log("Instance of class ShiftSelectCheckBoxes created.");
        } catch(err) {
            console.error(err.message);
        }
    };

    setUpCheckBoxes() {
        // Get all the checkboxes in the table
        const checkboxes = document.querySelectorAll('.checkbox');

        // Set the data-index attribute for each checkbox
        checkboxes.forEach((checkbox, index) => {
            checkbox.setAttribute('data-index', index);
        });

        let lastCheckedIndex = null;

        function handleShiftClick(event) {
            if (event.shiftKey && lastCheckedIndex !== null) {
            // Find the index of the clicked checkbox
            const currentCheckedIndex = parseInt(event.target.getAttribute('data-index'), 10);

            // Determine the range of checkboxes to check
            const start = Math.min(lastCheckedIndex, currentCheckedIndex);
            const end = Math.max(lastCheckedIndex, currentCheckedIndex);

            // Check or uncheck the checkboxes in the range
            for (let i = start; i <= end; i++) {
                checkboxes[i].checked = true;
            }
            }

            // Update the last checked index
            lastCheckedIndex = parseInt(event.target.getAttribute('data-index'), 10);
        }

        // Add event listeners to each checkbox
        checkboxes.forEach((checkbox) => {
            checkbox.addEventListener('click', handleShiftClick);
            checkbox.addEventListener('click', function() {
                let itemCodes = getItemCodesForCheckedBoxes();
                console.log(itemCodes);
            });
        });



    };
};

export class SelectAllCheckBox {
    constructor() {
        try {
            this.setUpSelectAllCheckBox();
            console.log("Instance of class ShiftSelectCheckBoxes created.");
        } catch(err) {
            console.error(err.message);
        }
    };

    setUpSelectAllCheckBox() {
        // Select all checkboxes when the "Select All" checkbox is checked
        $("#selectAllCheckbox").on("change", function() {
            const isChecked = $(this).prop("checked");
            $(".checkbox").prop("checked", isChecked);
        });

        // Update the "Select All" checkbox state based on the checkboxes in the table rows
        $(".checkbox").on("change", function() {
            const allChecked = $(".checkbox:checked").length === $(".checkbox").length;
            $("#selectAllCheckbox").prop("checked", allChecked);
        });
    };

};