"use client";
import { useState } from "react";
import { parseExcel, normalizeKeys, exportData } from "@/utils/excel";
import {
  UploadCloud, Play, FileSpreadsheet, FileText,
  Loader2, CheckCircle, AlertCircle, Info, Trash2
} from "lucide-react";

interface Shipment {
  id: number;
  trackingNumber: string;
  carrier: string;
  systemEta: string;
  liveEta?: string;
  status?: string;
  summary?: string;
  co2?: string;
  etaChanged?: boolean;
  loading?: boolean;
  selected?: boolean;
  type?: string;
  raw?: any;
}

export default function Dashboard() {
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);

  // --- 1. UPLOAD & PARSE ---
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    const data = await parseExcel(e.target.files[0]);

    // Map Excel rows to our App Structure
    const mapped = data.map((row: any, index: number) => {
      const norm = normalizeKeys(row);

      // --- CLEAN CARRIER NAMES ---
      let carrier = String(norm.carrier || "Unknown").toUpperCase();

      if (carrier.includes('HAPAG')) carrier = 'HAPAG-LLOYD';
      else if (carrier.includes('CMA')) carrier = 'CMA CGM';
      else if (carrier.includes('ONE')) carrier = 'ONE';
      else if (carrier.includes('MSC')) carrier = 'MSC';
      else if (carrier.includes('HYUNDAI') || carrier.includes('HMM')) carrier = 'HMM';
      else if (carrier.includes('MAERSK')) carrier = 'MAERSK';
      else if (carrier.includes('COSCO')) carrier = 'COSCO';
      else if (carrier.includes('EVERGREEN')) carrier = 'EVERGREEN';

      // --- CLEAN CONTAINER NUMBER ---
      // Remove spaces or invisible characters
      const rawTracking = String(norm.trackingNumber || "").trim();

      // Guess type based on number format
      // Air = 3 digits - 8 digits (e.g., 098-12345678)
      // Sea = 4 letters + 7 numbers (e.g., MSCU1234567)
      const isAir = rawTracking.includes("-") || (rawTracking.length === 11 && !isNaN(Number(rawTracking)));

      return {
        id: index,
        trackingNumber: rawTracking,
        carrier: carrier,
        systemEta: norm.systemEta || "N/A",
        type: isAir ? "air" : "sea",
        loading: false,
        selected: true,
        raw: row
      } as Shipment;
    })
    // FILTER: Only keep rows that actually have a Container/AWB Number
    .filter(s => s.trackingNumber && s.trackingNumber.length > 5 && s.trackingNumber !== "UNKNOWN");

    setShipments(mapped);
  };

  // --- 2. EDITING LOGIC ---
  const updateShipment = (id: number, field: keyof Shipment, value: string) => {
    setShipments(prev => prev.map(s => s.id === id ? { ...s, [field]: value } : s));
  };

  const toggleSelect = (id: number) => {
    setShipments(prev => prev.map(s => s.id === id ? { ...s, selected: !s.selected } : s));
  };

  const toggleSelectAll = (checked: boolean) => {
    setShipments(prev => prev.map(s => ({ ...s, selected: checked })));
  };

  const deleteRow = (id: number) => {
    setShipments(prev => prev.filter(s => s.id !== id));
  };

  // --- 3. TRACKING LOGIC ---
  const startTracking = async () => {
    setIsProcessing(true);
    setProgress(0);

    let completed = 0;
    const total = shipments.filter(s => s.selected).length;

    // We use a functional update pattern to ensure we always have latest state
    for (let i = 0; i < shipments.length; i++) {
      if (!shipments[i].selected) continue; // Skip unselected

      // Mark current row as loading
      setShipments(prev => {
        const newArr = [...prev];
        newArr[i] = { ...newArr[i], loading: true, status: "Processing..." };
        return newArr;
      });

      try {
        const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${API_BASE}/api/track/sea`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            number: shipments[i].trackingNumber,
            carrier: shipments[i].carrier,
            system_eta: shipments[i].systemEta
          })
        });

        const data = await res.json();

        // Update row with results
        setShipments(prev => {
          const newArr = [...prev];
          newArr[i] = {
            ...newArr[i],
            loading: false,
            liveEta: data.live_eta || "N/A",
            status: data.status || "Error",
            summary: data.smart_summary || data.message || "No data",
            co2: data.co2 || "N/A",
            etaChanged: data.eta_changed || false
          };
          return newArr;
        });

      } catch (error) {
        setShipments(prev => {
          const newArr = [...prev];
          newArr[i] = { ...newArr[i], loading: false, status: "Network Error" };
          return newArr;
        });
      }

      completed++;
      setProgress(Math.round((completed / total) * 100));
    }

    setIsProcessing(false);
  };

  // --- 4. EXPORT LOGIC ---
  const handleExport = (format: 'xlsx' | 'csv') => {
    const selectedRows = shipments.filter(s => s.selected);
    const exportDataList = selectedRows.map(s => ({
      "Container No": s.trackingNumber,
      "Carrier": s.carrier,
      "System ETA": s.systemEta,
      "Live ETA": s.liveEta,
      "CO2 Emissions": s.co2,
      "Status": s.status,
      "Summary": s.summary,
      "ETA Changed": s.etaChanged ? "YES" : "NO"
    }));
    exportData(exportDataList, format);
  };

  // --- 5. HELPERS ---
  const getStatusColor = (status?: string) => {
    if (!status) return "bg-gray-100 text-gray-600";
    const s = status.toLowerCase();
    if (s.includes("arrived") || s.includes("delivered")) return "bg-green-100 text-green-800 border-green-200";
    if (s.includes("transit") || s.includes("departed")) return "bg-blue-100 text-blue-800 border-blue-200";
    if (s.includes("error") || s.includes("found")) return "bg-red-100 text-red-800 border-red-200";
    return "bg-yellow-100 text-yellow-800 border-yellow-200";
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8 font-sans text-slate-800">
      <div className="max-w-7xl mx-auto">

        {/* --- HEADER --- */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold text-slate-900">Sea Freight Tracker <span className="text-blue-600">v2.0</span></h1>
            <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded border border-blue-200">BETA</span>
          </div>
          <p className="text-slate-500">Upload your sea shipment manifest to sync live ETAs and CO2 data.</p>
        </div>

        {/* --- INFO CARD --- */}
        {shipments.length === 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-8 flex gap-4 items-start">
            <Info className="text-blue-600 shrink-0 mt-1" />
            <div>
              <h3 className="font-semibold text-blue-900">Required Excel Format</h3>
              <p className="text-blue-700 text-sm mt-1">Your file must contain at least these columns (headers are flexible):</p>
              <div className="flex gap-4 mt-3">
                <span className="px-3 py-1 bg-white border border-blue-200 rounded text-sm text-blue-800 font-mono">Container No</span>
                <span className="px-3 py-1 bg-white border border-blue-200 rounded text-sm text-blue-800 font-mono">Carrier (e.g. Hapag)</span>
                <span className="px-3 py-1 bg-white border border-blue-200 rounded text-sm text-blue-800 font-mono">ETA (Optional)</span>
              </div>
            </div>
          </div>
        )}

        {/* --- UPLOAD ZONE --- */}
        {shipments.length === 0 && (
          <div className="border-2 border-dashed border-slate-300 rounded-2xl p-16 text-center bg-white hover:bg-slate-50 transition cursor-pointer relative group">
            <input type="file" accept=".xlsx,.csv" onChange={handleFileUpload} className="absolute inset-0 opacity-0 cursor-pointer z-10" />
            <div className="flex flex-col items-center group-hover:scale-105 transition-transform duration-200">
              <div className="bg-slate-100 p-4 rounded-full mb-4 group-hover:bg-blue-100">
                <UploadCloud className="text-slate-400 group-hover:text-blue-600" size={40} />
              </div>
              <h3 className="text-xl font-semibold text-slate-900">Drag & Drop your Excel file here</h3>
              <p className="text-slate-500 mt-2">Supports .xlsx and .csv files</p>
            </div>
          </div>
        )}

        {/* --- MAIN INTERFACE --- */}
        {shipments.length > 0 && (
          <div className="space-y-4">

            {/* Toolbar */}
            <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-slate-200">
              <div className="flex items-center gap-4">
                <div className="text-sm font-medium text-slate-600">
                  {shipments.filter(s => s.selected).length} Selected
                </div>
                {isProcessing && (
                  <div className="flex items-center gap-2 text-sm text-blue-600 font-medium bg-blue-50 px-3 py-1 rounded-full">
                    <Loader2 className="animate-spin" size={14} />
                    Processing {progress}%
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => setShipments([])}
                  className="px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition"
                  disabled={isProcessing}
                >
                  Reset
                </button>

                <div className="h-8 w-px bg-slate-200 mx-2"></div>

                <button
                  onClick={() => handleExport('csv')}
                  disabled={isProcessing}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg transition"
                >
                  <FileText size={16} /> CSV
                </button>
                <button
                  onClick={() => handleExport('xlsx')}
                  disabled={isProcessing}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg transition"
                >
                  <FileSpreadsheet size={16} /> Excel
                </button>

                <button
                  onClick={startTracking}
                  disabled={isProcessing}
                  className="flex items-center gap-2 px-6 py-2 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition disabled:opacity-50 disabled:cursor-not-allowed ml-2"
                >
                  {isProcessing ? "Analyzing..." : "Start Analysis"} <Play size={16} />
                </button>
              </div>
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-4 w-10">
                        <input
                          type="checkbox"
                          onChange={(e) => toggleSelectAll(e.target.checked)}
                          checked={shipments.every(s => s.selected)}
                          className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                        />
                      </th>
                      <th className="px-4 py-4 w-40">Container No.</th>
                      <th className="px-4 py-4 w-32">Carrier</th>
                      <th className="px-4 py-4 w-32">System ETA</th>
                      <th className="px-4 py-4 w-40">Live Status</th>
                      <th className="px-4 py-4 w-32">Live ETA</th>
                      <th className="px-4 py-4 w-28">CO2</th>
                      <th className="px-4 py-4">Smart Summary</th>
                      <th className="px-4 py-4 w-10"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {shipments.map((item) => (
                      <tr key={item.id} className={`hover:bg-slate-50 transition ${!item.selected ? 'opacity-50 grayscale' : ''}`}>
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={item.selected}
                            onChange={() => toggleSelect(item.id)}
                            className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                          />
                        </td>

                        {/* Editable Inputs */}
                        <td className="px-4 py-3">
                          <input
                            value={item.trackingNumber}
                            onChange={(e) => updateShipment(item.id, 'trackingNumber', e.target.value)}
                            className="w-full bg-transparent border-none focus:ring-0 p-0 font-medium text-slate-900 uppercase"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <input
                            value={item.carrier}
                            onChange={(e) => updateShipment(item.id, 'carrier', e.target.value)}
                            className="w-full bg-transparent border-none focus:ring-0 p-0 text-slate-500"
                          />
                        </td>
                        <td className="px-4 py-3 text-slate-500">{item.systemEta}</td>

                        {/* Status Badge */}
                        <td className="px-4 py-3">
                          {item.loading ? (
                            <div className="flex items-center gap-2 text-blue-600">
                              <Loader2 className="animate-spin" size={16} /> Checking...
                            </div>
                          ) : (
                            <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(item.status)}`}>
                              {item.status || "Pending"}
                            </span>
                          )}
                        </td>

                        {/* Live ETA */}
                        <td className={`px-4 py-3 font-medium ${item.etaChanged ? "text-red-600" : "text-slate-700"}`}>
                          {item.liveEta || "-"}
                        </td>

                        {/* CO2 Emissions */}
                        <td className="px-4 py-3 text-slate-600 text-sm">
                          {item.co2 || "-"}
                        </td>

                        {/* Summary */}
                        <td className="px-4 py-3 text-slate-600 max-w-lg truncate" title={item.summary}>
                          {item.summary || "-"}
                        </td>

                        {/* Actions */}
                        <td className="px-4 py-3 text-right">
                          <button onClick={() => deleteRow(item.id)} className="text-slate-400 hover:text-red-600 transition">
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
