import { StyleDnaReadinessEnum } from "../lib/types/api";

interface StatusBadgeProps {
  status?: string | null;
  readiness?: StyleDnaReadinessEnum | null;
  type?: "readiness" | "level" | "status";
}

export default function StatusBadge({ status, readiness, type = "status" }: StatusBadgeProps) {
  if (readiness) {
    const config: Record<StyleDnaReadinessEnum, { label: string; color: string }> = {
      STYLE_DNA_COMPLETE: { label: "Style DNA Tamam", color: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30" },
      STYLE_DNA_PARTIAL: { label: "Style DNA Kısmi", color: "bg-amber-500/10 text-amber-300 border-amber-500/30" },
      STYLE_DNA_MISSING: { label: "Style DNA Eksik", color: "bg-slate-800 text-slate-400 border-slate-700" },
      STYLE_DNA_FAILED: { label: "Style DNA Başarısız", color: "bg-rose-500/10 text-rose-300 border-rose-500/30" },
      NO_PRIMARY_IMAGE: { label: "Görsel Yok", color: "bg-slate-800 text-slate-500 border-slate-700" }
    };
    const c = config[readiness] || { label: readiness, color: "bg-slate-800 text-slate-400" };
    return (
      <span className={`inline-flex items-center text-[11px] font-mono font-medium px-2.5 py-0.5 rounded-full border ${c.color}`}>
        {c.label}
      </span>
    );
  }

  if (!status) return null;

  const colorMap: Record<string, string> = {
    COMPLETE: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
    PARTIAL: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    NOT_AVAILABLE: "bg-slate-800 text-slate-400 border-slate-700",
    VERY_CLOSE: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
    CLOSE: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
    MODERATE: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    LIMITED: "bg-slate-800 text-slate-400 border-slate-700",
    VERY_STRONG: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
    STRONG: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
  };

  const styleClass = colorMap[status] || "bg-slate-800 text-slate-300 border-slate-700";

  return (
    <span className={`inline-flex items-center text-[11px] font-medium px-2.5 py-0.5 rounded-full border ${styleClass}`}>
      {status}
    </span>
  );
}
