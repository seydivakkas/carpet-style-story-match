import Link from "next/link";
import { Check, FileText, Image as ImageIcon, Sliders, Star, BookOpen, CheckCircle } from "lucide-react";

export type StepKey = "text" | "visual" | "profile" | "importance" | "narrative" | "complete";

interface ProgressStepsProps {
  assessmentId: string;
  currentStep: StepKey;
}

const STEPS: Array<{ key: StepKey; label: string; icon: React.ComponentType<{ className?: string }> }> = [
  { key: "text", label: "Metin Tercihleri", icon: FileText },
  { key: "visual", label: "Görsel Karşılaştırma", icon: ImageIcon },
  { key: "profile", label: "Profil İnceleme", icon: Sliders },
  { key: "importance", label: "Öncelikler", icon: Star },
  { key: "narrative", label: "Hikâye Temaları", icon: BookOpen },
  { key: "complete", label: "Tamamlandı", icon: CheckCircle }
];

export default function ProgressSteps({ assessmentId, currentStep }: ProgressStepsProps) {
  const currentIndex = STEPS.findIndex((s) => s.key === currentStep);

  return (
    <nav aria-label="Değerlendirme İlerlemesi" className="w-full my-6">
      <ol className="flex items-center justify-between w-full bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 overflow-x-auto gap-2">
        {STEPS.map((step, idx) => {
          const isDone = idx < currentIndex;
          const isCurrent = idx === currentIndex;
          const StepIcon = step.icon;

          return (
            <li key={step.key} className="flex items-center min-w-max">
              <Link
                href={`/assessment/${assessmentId}/${step.key}`}
                className={`flex items-center space-x-2 text-xs font-medium px-3 py-2 rounded-xl transition-all ${
                  isCurrent
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm"
                    : isDone
                    ? "text-emerald-400 hover:bg-slate-800/60"
                    : "text-slate-500 hover:text-slate-400"
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs font-mono font-bold ${
                    isCurrent
                      ? "bg-amber-500 text-slate-950"
                      : isDone
                      ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                      : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {isDone ? <Check className="w-3.5 h-3.5" /> : idx + 1}
                </div>
                <span className="hidden sm:inline">{step.label}</span>
              </Link>
              {idx < STEPS.length - 1 && (
                <div className="w-4 sm:w-8 h-px bg-slate-800 mx-1 sm:mx-2" />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
