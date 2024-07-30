import { AddLotNumModal } from '../objects/modalObjects.js';
import { ShiftSelectCheckBoxes } from '../objects/pageUtilities.js'
import { getMatchingLotNumbers } from '../requestFunctions/requestFunctions.js'

$(document).ready(function(){
    const thisAddLotNumModal = new AddLotNumModal();
    $('.lotNumButton').each(function(){
        $(this).click(thisAddLotNumModal.setAddLotModalInputs);
    });
    const thisShiftSelectCheckBoxes = new ShiftSelectCheckBoxes();
    const urlParameters = new URLSearchParams(window.location.search);
    let blendArea = urlParameters.get('blend-area');
    console.log(blendArea);
    if (blendArea == 'Hx') {
        thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-hx`);
    } else if (blendArea == 'Dm') {
        thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-dm`);
    } else if (blendArea == 'Totes') {
        thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-totes`);
    } else if (blendArea == 'Desk_1') {
        thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-desk-1`);
        new TableSorter('deskScheduleTable', 'Short');
    } else if (blendArea == 'Desk_2') {
        thisAddLotNumModal.formElement.prop("action", `/core/add-lot-num-record/?redirect-page=blend-schedule-desk-2`);
        new TableSorter('deskScheduleTable', 'Short');
    }

    class TableSorter {
        constructor(tableId, columnName) {
          this.table = document.getElementById(tableId);
          this.columnIndex = this.getColumnIndex(columnName);
          this.sortState = { asc: true };
          this.button = this.createSortButton();
        }
      
        getColumnIndex(name) {
          const headers = this.table.querySelectorAll('th');
          return Array.from(headers).findIndex(th => th.textContent.trim() === name)+1;
        }
      
        createSortButton() {
          const button = document.createElement('button');
          button.textContent = 'Sort by Short';
          button.setAttribute('aria-label', 'Sort table by Short column');
          button.addEventListener('click', () => this.sort());
          button.addEventListener('keydown', e => e.key === 'Enter' && this.sort());
          this.table.parentNode.insertBefore(button, this.table);
          return button;
        }
      
        async sort() {
          this.button.setAttribute('aria-busy', 'true');
          this.button.disabled = true;
      
          const rows = Array.from(this.table.querySelectorAll('tbody tr'));
          const sortedRows = await this.sortRows(rows);
      
          const fragment = document.createDocumentFragment();
          sortedRows.forEach(row => fragment.appendChild(row));
      
          this.table.tBodies[0].appendChild(fragment);
          this.updateSortState();
      
          this.button.removeAttribute('aria-busy');
          this.button.disabled = false;
        }
      
        sortRows(rows) {
            const cachedValues = rows.map(row => {
              const val = this.getCellValue(row);
              const isNumber = /^\d+(\.\d+)?$/.test(val);
              const isDate = /^\d{1,2}\/\d{1,2}\/\d{4}$/.test(val);
              const type = isNumber ? 'number' : (isDate ? 'date' : 'string');
              const sortValue = isNumber ? parseFloat(val) :
                                (isDate ? new Date(val.split('/').reverse().join('-')) : val);          
              return { row, original: val, type, sortValue };
            });
          
            cachedValues.sort((a, b) => {
              if (a.type !== b.type) {
                const typePriority = { number: 0, date: 1, string: 2 };
                return typePriority[a.type] - typePriority[b.type];
              }
          
              if (a.type === 'number' || a.type === 'date') {
                const result = a.sortValue - b.sortValue;
                console.log(`Comparing ${a.original} to ${b.original}: ${result}`);
                return this.sortState.asc ? result : -result;
              }
              return this.sortState.asc ? a.original.localeCompare(b.original) : b.original.localeCompare(a.original);
            });
          
            return cachedValues.map(item => item.row);
          }
      
        getCellValue(row) {
          return row.cells[this.columnIndex]?.textContent.trim() ?? '';
        }
      
        updateSortState() {
          this.sortState.asc = !this.sortState.asc;
          this.button.textContent = `Sort by Short (${this.sortState.asc ? 'Asc' : 'Desc'})`;
        }
      }

});