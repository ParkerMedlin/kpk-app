$(document).ready(function() {
    const monthNames = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
    ];


    const $emailLink = $("#emailLink");
    const countsTable = document.getElementById("countsTable");
    const todayDate = new Date();
    const monthNumber = todayDate.getMonth();
    const todayString = monthNames[monthNumber] + "%20" + String(todayDate.getDate()).padStart(2, '0') + "%20" + String(todayDate.getFullYear());
    let subjectString = `Counts%20for%20${todayString}`;
    
    $emailLink.attr('href', `mailto:jdavis@kinpakinc.com?cc=kkeyes@kinpakinc.com&subject=${subjectString}`);

    // Helper function to convert RGB or RGBA color string to HEX
    function colorToHex(color) {
        if (!color) return color; // Return null/undefined as is
        const lowerColor = color.toLowerCase();
        if (lowerColor === 'transparent') {
            return 'transparent';
        }
        // Check if it's already a hex color
        if (lowerColor.startsWith('#')) {
            if (lowerColor.length === 4) { // #RGB to #RRGGBB
                return `#${lowerColor[1]}${lowerColor[1]}${lowerColor[2]}${lowerColor[2]}${lowerColor[3]}${lowerColor[3]}`;
            }
            return lowerColor;
        }

        const rgbaMatch = lowerColor.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)$/);
        if (rgbaMatch) {
            const r = parseInt(rgbaMatch[1], 10);
            const g = parseInt(rgbaMatch[2], 10);
            const b = parseInt(rgbaMatch[3], 10);
            const a = parseFloat(rgbaMatch[4]);

            if (rgbaMatch[4] !== undefined && a === 0) { // Explicitly alpha = 0
                return 'transparent';
            }
            const toHexComponent = (c) => {
                const hex = c.toString(16);
                return hex.length === 1 ? '0' + hex : hex;
            };
            return `#${toHexComponent(r)}${toHexComponent(g)}${toHexComponent(b)}`;
        }
        return color; // Return original if not parsable/handled
    }

    // Helper function to identify column indices
    function getColumnIndices(headerCells) {
        let varianceColumnIndex = -1;
        let varianceCostColumnIndex = -1;
        headerCells.forEach((th, index) => {
            const headerText = th.textContent.trim();
            if (headerText === 'Variance') {
                varianceColumnIndex = index;
            } else if (headerText === 'Variance Cost') {
                varianceCostColumnIndex = index;
            }
        });
        return { varianceColumnIndex, varianceCostColumnIndex };
    }

    // Helper function to apply computed styles to a cloned element
    function applyStylesToElement(originalEl, clonedEl, varianceColumnIndex, varianceCostColumnIndex) {
        const computedStyle = window.getComputedStyle(originalEl);
        const styleMap = {};

        const cssPropertiesToInline = [
            'background-color', 'color',
            'font-family', 'font-size', 'font-weight', 'font-style', 'text-decoration',
            'text-align', 'vertical-align',
            'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
            'border-top-color', 'border-top-style', 'border-top-width',
            'border-right-color', 'border-right-style', 'border-right-width',
            'border-bottom-color', 'border-bottom-style', 'border-bottom-width',
            'border-left-color', 'border-left-style', 'border-left-width',
            'border-collapse', 'border-spacing'
        ];

        for (const propName of cssPropertiesToInline) {
            let originalPropValue = computedStyle.getPropertyValue(propName);
            let processedPropValue = originalPropValue;

            if (originalPropValue) {
                const trimmedPropName = propName.trim();
                if (trimmedPropName.includes('color')) {
                    processedPropValue = colorToHex(originalPropValue);
                }
                if (processedPropValue) {
                    styleMap[trimmedPropName] = String(processedPropValue).trim();
                }
            }
        }

        // Specific override for Variance and Variance Cost column data cells (TD)
        if (originalEl.tagName === 'TD' &&
            ((varianceColumnIndex !== -1 && originalEl.cellIndex === varianceColumnIndex) ||
             (varianceCostColumnIndex !== -1 && originalEl.cellIndex === varianceCostColumnIndex))) {
            styleMap['text-align'] = 'right';
        }

        let styleString = Object.entries(styleMap)
                              .map(([key, value]) => `${key}:${value};`)
                              .join('');

        if (styleString) {
            clonedEl.setAttribute('style', styleString);
        }
    }

    // Recursive helper to apply styles to an element and its children
    function styleTreeRecursive(originalEl, clonedEl, varianceColumnIndex, varianceCostColumnIndex) {
        applyStylesToElement(originalEl, clonedEl, varianceColumnIndex, varianceCostColumnIndex);

        const originalChildren = Array.from(originalEl.children);
        const clonedChildren = Array.from(clonedEl.children);

        for (let i = 0; i < originalChildren.length; i++) {
            if (originalChildren[i].nodeType === Node.ELEMENT_NODE && clonedChildren[i] && clonedChildren[i].nodeType === Node.ELEMENT_NODE) {
                styleTreeRecursive(originalChildren[i], clonedChildren[i], varianceColumnIndex, varianceCostColumnIndex);
            }
        }
    }

    // Helper function to specifically style table headers
    function styleTableHeaders(clonedTable) {
        const clonedHeaderCells = clonedTable.querySelectorAll('thead th');
        clonedHeaderCells.forEach(thCell => {
            thCell.style.backgroundColor = '#87b0cd';
        });
    }

    // Main function to get HTML with inlined styles (Refactored)
    function getStyledHtml(element) {
        if (!element || element.nodeType !== Node.ELEMENT_NODE) {
            console.error("getStyledHtml: Invalid element provided.");
            return "";
        }

        const headerCells = element.querySelectorAll('thead th');
        const { varianceColumnIndex, varianceCostColumnIndex } = getColumnIndices(headerCells);

        const clone = element.cloneNode(true); // Deep clone

        styleTreeRecursive(element, clone, varianceColumnIndex, varianceCostColumnIndex);
        styleTableHeaders(clone);

        return clone.outerHTML;
    }

    $emailLink.click(function(event){
        event.preventDefault(); // Prevent the default mailto action initially to handle copy first
        const htmlContent = getStyledHtml(countsTable); 

        if (!htmlContent) {
            console.error("Failed to generate styled HTML content. Aborting copy.");
            // Optionally, still proceed with mailto link or alert user
            // window.location.href = $emailLink.attr('href');
            return;
        }

        if (navigator.clipboard && navigator.clipboard.write) {
            const blob = new Blob([htmlContent], { type: 'text/html' });
            const item = new ClipboardItem({ 'text/html': blob });
            navigator.clipboard.write([item])
                .then(() => {
                    console.log("Table HTML content with inlined styles copied via navigator.clipboard.write.");
                    window.location.href = $emailLink.attr('href'); 
                })
                .catch(err => {
                    console.error("Failed to copy HTML table content using navigator.clipboard.write: ", err);
                    executeFallbackCopy(htmlContent); 
                });
        } else {
            console.log("navigator.clipboard.write API not available, attempting fallback.");
            executeFallbackCopy(htmlContent);
        }
    });

    // Fallback function to use document.execCommand('copy') with a contentEditable div
    function executeFallbackCopy(styledHtml) {
        const tempDiv = document.createElement('div');
        tempDiv.contentEditable = 'true';
        tempDiv.innerHTML = styledHtml;
        tempDiv.style.position = 'absolute';
        tempDiv.style.left = '-9999px'; // Move off-screen
        document.body.appendChild(tempDiv);

        const range = document.createRange();
        range.selectNodeContents(tempDiv);
        
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);

        try {
            document.execCommand('copy');
            console.log("Table content with inlined styles copied to clipboard using fallback (document.execCommand on contentEditable div).");
        } catch (e) {
            console.error("Fallback copy method (document.execCommand on contentEditable div) failed:", e);
        } finally {
            document.body.removeChild(tempDiv); // Clean up the temporary element
            selection.removeAllRanges(); // Clear selection after attempting copy
            // Proceed with the mailto link after fallback copy attempt
            window.location.href = $emailLink.attr('href');
        }
    }

    var totalVarianceCell = $("#totalVarianceCell");
    var totalVarianceValue = Math.abs(parseFloat(totalVarianceCell.text().replace(/[^0-9.-]+/g,"")));
    if (totalVarianceValue > 1000) {
        totalVarianceCell.addClass('bigMoney');
    }
    
});