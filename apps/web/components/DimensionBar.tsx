"use client";

import { DIMENSION_DETAILS, PROVENANCE_LABELS } from "../lib/constants";
import { ProvenanceEnum } from "../lib/types/api";

interface DimensionBarProps {
  dimensionKey: string;
  inferredValue?: number;
  userOverrideValue?: number | null;
  finalValue: number;
  provenance?: ProvenanceEnum;
  confidenceLevel?: "HIGH" | "MODERATE" | "LOW";
  isInteractive?: boolean;
  onOverrideChange?: (value: number) => void;
}

export default function DimensionBar({
  dimensionKey,
  inferredValue,
  finalValue,
  provenance,
  confidenceLevel,
  isInteractive = false,
  onOverrideChange
}: DimensionBarProps) {
  const meta = DIMENSION_DETAILS[dimensionKey] || {
    code: dimensionKey,
    label_tr: dimensionKey,
    min_label: "Düşük",
    max_label: "Yüksek"
  };

  const prov = provenance ? PROVENANCE_LABELS[provenance] : null;

  return (
    <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 space-y-3 hover:border-slate-700/80 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="font-mono text-xs font-bold text-amber-400 px-2 py-0.5 bg-amber-500/10 border border-amber-500/20 rounded">
            {meta.code}
          </span>
          <span className="font-semibold text-sm text-slate-100">{meta.label_tr}</span>
        </div>

        <div className="flex items-center space-x-2">
          {confidenceLevel && (
            <span
              className={`text-[10px] font-medium px-2 py-0.5 rounded border ${
                confidenceLevel === "HIGH"
                  ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                  : confidenceLevel === "MODERATE"
                  ? "bg-amber-500/10 text-amber-300 border-amber-500/20"
                  : "bg-rose-500/10 text-rose-300 border-rose-500/20"
              }`}
            >
              Kanıt: {confidenceLevel === "HIGH" ? "Yüksek" : confidenceLevel === "MODERATE" ? "Orta" : "Düşük"}
            </span>
          )}

          {prov && (
            <span className={`text-[10px] font-medium px-2 py-0.5 rounded border ${prov.color}`}>
              {prov.label_tr}
            </span>
          )}

          <span className="font-mono text-sm font-bold text-amber-300">
            {finalValue.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Bar container */}
      <div className="space-y-1">
        <div className="relative w-full h-3 bg-slate-950 rounded-full border border-slate-800/60 overflow-hidden">
          {/* Final Value Fill */}
          <div
            className="absolute top-0 bottom-0 left-0 bg-gradient-to-r from-amber-600 to-amber-400 rounded-full transition-all duration-300"
            style={{ width: `${Math.max(0, Math.min(100, finalValue * 100))}%` }}
          />

          {/* Inferred Value Marker if different */}
          {inferredValue !== undefined && Math.abs(inferredValue - finalValue) > 0.01 && (
            <div
              className="absolute top-0 bottom-0 w-1 bg-slate-400/80 shadow-md"
              style={{ left: `${Math.max(0, Math.min(100, inferredValue * 100))}%` }}
              title={`Sistem çıkarımı: ${inferredValue.toFixed(2)}`}
            />
          )}
        </div>

        {/* Pole labels */}
        <div className="flex items-center justify-between text-[11px] text-slate-500 font-medium">
          <span>{meta.min_label} (0.0)</span>
          {inferredValue !== undefined && Math.abs(inferredValue - finalValue) > 0.01 && (
            <span className="text-[10px] text-slate-400 italic">
              Çıkarılan: {inferredValue.toFixed(2)}
            </span>
          )}
          <span>{meta.max_label} (1.0)</span>
        </div>
      </div>

      {/* Interactive slider if review is open */}
      {isInteractive && onOverrideChange && (
        <div className="pt-2 border-t border-slate-800/40 flex items-center space-x-3">
          <label className="text-xs text-slate-400 font-medium min-w-max">
            Düzenle:
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={finalValue}
            onChange={(e) => onOverrideChange(parseFloat(e.target.value))}
            className="w-full accent-amber-500 bg-slate-950 cursor-pointer h-2 rounded-lg"
          />
        </div>
      )}
    </div>
  );
}
