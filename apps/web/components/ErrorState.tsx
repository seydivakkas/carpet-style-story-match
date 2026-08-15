import { AlertCircle, RefreshCw } from "lucide-react";
import { ApiClientError } from "../lib/api/client";

interface ErrorStateProps {
  error?: unknown;
  title?: string;
  onRetry?: () => void;
}

export default function ErrorState({ error, title = "Bir Hata Oluştu", onRetry }: ErrorStateProps) {
  let code = "UNKNOWN_ERROR";
  let message = "İşlem sırasında beklenmeyen bir hata meydana geldi.";

  if (error instanceof ApiClientError) {
    code = error.code;
    message = error.message;
  } else if (error instanceof Error) {
    message = error.message;
  }

  return (
    <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-6 sm:p-8 text-center flex flex-col items-center justify-center my-6 space-y-4">
      <div className="p-3 bg-rose-500/20 text-rose-400 rounded-full">
        <AlertCircle className="w-6 h-6" />
      </div>
      <div className="space-y-1 max-w-md">
        <span className="font-mono text-[10px] text-rose-400 font-bold uppercase tracking-wider block">
          Hata Kodu: {code}
        </span>
        <h3 className="text-base font-semibold text-rose-200">{title}</h3>
        <p className="text-xs sm:text-sm text-rose-300/80 leading-relaxed">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center space-x-2 px-4 py-2 bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 border border-rose-500/40 rounded-xl text-xs font-semibold transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Tekrar Dene</span>
        </button>
      )}
    </div>
  );
}
