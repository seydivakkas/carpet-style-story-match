import { Loader2 } from "lucide-react";

interface LoadingStateProps {
  message?: string;
}

export default function LoadingState({ message = "Yükleniyor..." }: LoadingStateProps) {
  return (
    <div className="py-16 flex flex-col items-center justify-center space-y-3 text-slate-400">
      <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
      <span className="text-xs font-mono tracking-wider">{message}</span>
    </div>
  );
}
