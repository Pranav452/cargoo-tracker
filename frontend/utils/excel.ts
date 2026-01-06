import * as XLSX from 'xlsx';
import { saveAs } from 'file-saver';

// NEW: Helper to convert Excel Serial Date to String
const excelDateToJSDate = (serial: any) => {
   if (!serial || isNaN(serial)) return serial; // Return original if not a number
   // Excel base date logic
   const utc_days  = Math.floor(serial - 25569);
   const utc_value = utc_days * 86400;
   const date_info = new Date(utc_value * 1000);

   // Format as DD/MM/YYYY
   return date_info.toLocaleDateString('en-GB');
}

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
    else if (lower === 'eta') {
        // APPLY DATE FIX HERE
        newRow.systemEta = excelDateToJSDate(row[key]);
    }
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

// --- PASTED TABLE PARSER ---
// Accepts text copied from Excel/Sheets (tab- or comma-separated)
// Returns an array of row objects keyed by header names
export const parsePastedTable = (text: string): any[] => {
  if (!text.trim()) return [];

  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  if (lines.length === 0) return [];

  // Detect separator: prefer tab, fallback to comma
  const detectSeparator = (sample: string) => {
    if (sample.includes('\t')) return '\t';
    if (sample.includes(',')) return ',';
    return '\t';
  };

  const separator = detectSeparator(lines[0]);

  const headers = lines[0].split(separator).map((h) => h.trim());

  const rows: any[] = [];

  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(separator);
    if (parts.every((p) => !p.trim())) continue;

    const row: any = {};
    headers.forEach((header, idx) => {
      row[header] = (parts[idx] ?? '').trim();
    });
    rows.push(row);
  }

  return rows;
};
