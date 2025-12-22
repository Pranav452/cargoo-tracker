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
        const jsonData = XLSX.utils.sheet_to_json(sheet);
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
    if (lower.includes('container') || lower.includes('tracking')) newRow.trackingNumber = row[key];
    else if (lower.includes('carrier') || lower.includes('shipping line')) newRow.carrier = row[key];
    else if (lower.includes('eta') || lower.includes('arrival')) newRow.systemEta = row[key];
    else newRow[key] = row[key]; // Keep extra columns
  });
  return newRow;
};

// --- EXPORTING ---
export const exportData = (data: any[], format: 'xlsx' | 'csv') => {
  const ws = XLSX.utils.json_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Tracking Results");

  if (format === 'xlsx') {
    const excelBuffer = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const blob = new Blob([excelBuffer], { type: 'application/octet-stream' });
    saveAs(blob, `Sea_Tracking_Report_${new Date().toISOString().split('T')[0]}.xlsx`);
  } else {
    const csvOutput = XLSX.utils.sheet_to_csv(ws);
    const blob = new Blob([csvOutput], { type: 'text/csv;charset=utf-8' });
    saveAs(blob, `Sea_Tracking_Report_${new Date().toISOString().split('T')[0]}.csv`);
  }
};
