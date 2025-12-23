import * as XLSX from 'xlsx';
import { saveAs } from 'file-saver';

// --- PARSING ---
export const parseExcel = (file: File): Promise<any[]> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = e.target?.result;
        const workbook = XLSX.read(data, { type: 'binary' });
        const sheetName = workbook.SheetNames[0];
        const sheet = workbook.Sheets[sheetName];

        // Convert sheet to array of arrays first to find the header row
        const rawData = XLSX.utils.sheet_to_json(sheet, { header: 1 }) as any[][];

        let headerRowIndex = 0;
        let foundHeaders = false;

        // Hunt for the real header row (Look for "Container" or "Shipping Line")
        for (let i = 0; i < Math.min(rawData.length, 20); i++) {
          const rowStr = JSON.stringify(rawData[i]).toLowerCase();
          if (rowStr.includes("container") && rowStr.includes("shipping")) {
            headerRowIndex = i;
            foundHeaders = true;
            break;
          }
        }

        // If we found headers, re-parse starting from that row
        let jsonData;
        if (foundHeaders) {
          const range = XLSX.utils.decode_range(sheet['!ref'] || 'A1');
          range.s.r = headerRowIndex; // Start reading from the header row
          const newRef = XLSX.utils.encode_range(range);
          jsonData = XLSX.utils.sheet_to_json(sheet, { range: newRef });
        } else {
          // Fallback to default
          jsonData = XLSX.utils.sheet_to_json(sheet);
        }

        resolve(jsonData);
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = reject;
    reader.readAsBinaryString(file);
  });
};

// --- NORMALIZATION ---
export const normalizeKeys = (row: any) => {
  const newRow: any = {};

  Object.keys(row).forEach((key) => {
    const lower = key.toLowerCase().trim();

    // Smart Column Mapping based on your team's file
    if (lower.includes('container no') || lower === 'container') newRow.trackingNumber = row[key];
    else if (lower.includes('shipping line') || lower === 'carrier') newRow.carrier = row[key];
    else if (lower === 'eta') newRow.systemEta = row[key]; // Strict 'eta' to avoid 'actual eta' confusion
    else newRow[key] = row[key]; // Keep extra columns
  });

  return newRow;
};

// --- EXPORTING ---
export const exportData = (data: any[], format: 'xlsx' | 'csv') => {
  const ws = XLSX.utils.json_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Updated Tracking");

  const fileName = `Tracking_Update_${new Date().toISOString().split('T')[0]}`;

  if (format === 'xlsx') {
    const excelBuffer = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const blob = new Blob([excelBuffer], { type: 'application/octet-stream' });
    saveAs(blob, `${fileName}.xlsx`);
  } else {
    const csvOutput = XLSX.utils.sheet_to_csv(ws);
    const blob = new Blob([csvOutput], { type: 'text/csv;charset=utf-8' });
    saveAs(blob, `${fileName}.csv`);
  }
};
