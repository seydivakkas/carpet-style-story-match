import { Inbox } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export default function EmptyState({
  title = "Veri Bulunmuyor",
  description = "Henüz görüntülenecek herhangi bir kayıt bulunamadı.",
  actionLabel,
  onAction
}: EmptyStateProps) {
  return (
    <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-8 sm:p-12 text-center flex flex-col items-center justify-center my-6 space-y-4">
      <div className="p-4 bg-slate-900 border border-slate-800 rounded-full text-slate-500">
        <Inbox className="w-8 h-8" />
      </div>
      <div className="space-y-1 max-w-md">
        <h3 className="text-lg font-semibold text-slate-200">{title}</h3>
        <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">{description}</p>
      </div>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-xs rounded-xl transition-colors shadow-lg shadow-amber-500/10"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
