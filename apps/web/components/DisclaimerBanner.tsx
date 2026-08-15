import { AlertTriangle } from "lucide-react";

interface DisclaimerBannerProps {
  disclaimerText?: string | null;
}

export default function DisclaimerBanner({ disclaimerText }: DisclaimerBannerProps) {
  const defaultText =
    "Bu sonuç yalnız ölçülen görsel Style DNA yakınlığını gösterir. Hedef halının kültürünü, dönemini, hanedanını, atölyesini veya özgünlüğünü doğrulamaz.";

  return (
    <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 sm:p-5 flex items-start space-x-3 text-amber-200 text-xs sm:text-sm leading-relaxed my-4">
      <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
      <div className="space-y-1">
        <span className="font-semibold text-amber-300 block">
          Doğrulama ve Özgünlük Sorumluluk Reddi Beyanı:
        </span>
        <p className="text-amber-200/90">{disclaimerText || defaultText}</p>
      </div>
    </div>
  );
}
