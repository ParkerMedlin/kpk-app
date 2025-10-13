import { getItemCodesForCheckedBoxes } from '../uiFunctions/uiFunctions.js'

export class ShiftSelectCheckBoxes {
    constructor() {
        try {
            this.setUpCheckBoxes();
        } catch(err) {
            console.error(err.message);
        }
    };

    setUpCheckBoxes() {
        let lastCheckedCheckbox = null;
        const getVisibleCheckboxes = () => {
            return Array.from(document.querySelectorAll('.checkbox')).filter((checkbox) => {
                // `offsetParent` is null when an element or its ancestors are display:none.
                return checkbox.offsetParent !== null;
            });
        };

        function handleShiftClick(event) {
            const visibleCheckboxes = getVisibleCheckboxes();
            const targetIndex = visibleCheckboxes.indexOf(event.target);

            if (targetIndex === -1) {
                lastCheckedCheckbox = null;
                return;
            }

            if (event.shiftKey && lastCheckedCheckbox) {
                const lastIndex = visibleCheckboxes.indexOf(lastCheckedCheckbox);

                if (lastIndex !== -1) {
                    const start = Math.min(lastIndex, targetIndex);
                    const end = Math.max(lastIndex, targetIndex);
                    const shouldCheck = event.target.checked;

                    for (let i = start; i <= end; i++) {
                        visibleCheckboxes[i].checked = shouldCheck;
                    }
                }
            }

            // Update the last checked index only if the checkbox remains visible
            lastCheckedCheckbox = event.target;
        }

        // Add event listeners to each checkbox
        document.querySelectorAll('.checkbox').forEach((checkbox) => {
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

export class LabelPrintSender {
    constructor() {
        try {
            this.setupEventListener();
        } catch(err) {
            console.error(err.message);
        }
    };

    setupEventListener() {
        // Select all checkboxes when the "Select All" checkbox is checked
        $("#blendLabelPrintButton").on("click", function() {
            html2canvas(document.querySelector("#labelContainer")).then(canvas => {
                let img;
                img = canvas.toDataURL("image/jpeg");
            }); 
        });

    }
}
