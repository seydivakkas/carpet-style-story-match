"use client";

import { use, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ProgressSteps from "@/components/ProgressSteps";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import {
  useAssessment,
  useStartVisualPhase,
  useVisualPresentations,
  useVisualResponses,
  useSaveVisualResponse,
  useCompleteVisualAssessment,
  useBuildMultimodalProfile
} from "@/lib/api/preferences";
import { API_BASE_URL, VISUAL_CHOICE_LABELS } from "@/lib/constants";
import { VisualChoiceEnum } from "@/lib/types/api";
import { ArrowRight, CheckCircle2 } from "lucide-react";

const CHOICES: VisualChoiceEnum[] = [
  "STRONGLY_LEFT",
  "SLIGHTLY_LEFT",
  "NEUTRAL",
  "SLIGHTLY_RIGHT",
  "STRONGLY_RIGHT"
];

export default function VisualPreferencesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: assessmentId } = use(params);
  const router = useRouter();

  const { data: assessment, isLoading: assessmentLoading } = useAssessment(assessmentId);
  const { data: presentations, isLoading: presentationsLoading, error: presentationsError } = useVisualPresentations(assessmentId);
  const { data: existingResponses } = useVisualResponses(assessmentId);

  const startVisual = useStartVisualPhase(assessmentId);
  const saveResponse = useSaveVisualResponse(assessmentId);
  const completeVisual = useCompleteVisualAssessment(assessmentId);
  const buildProfile = useBuildMultimodalProfile(assessmentId);

  const [selectedChoices, setSelectedChoices] = useState<Record<string, VisualChoiceEnum>>({});

  // Auto start visual phase if not already started
  useEffect(() => {
    if (assessment && assessment.status === "TEXT_COMPLETE" && (!presentations || presentations.length === 0)) {
      startVisual.mutate();
    }
  }, [assessment, presentations, startVisual]);

  // Hydrate existing choices
  useEffect(() => {
    if (existingResponses && existingResponses.length > 0) {
      const map: Record<string, VisualChoiceEnum> = {};
      existingResponses.forEach((r) => {
        map[r.stimulus_key] = r.display_choice;
      });
      setSelectedChoices(map);
    }
  }, [existingResponses]);

  if (assessmentLoading || presentationsLoading || startVisual.isPending) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header assessmentId={assessmentId} />
        <LoadingState message="Görsel A/B kartları hazırlanıyor..." />
        <Footer />
      </div>
    );
  }

  if (presentationsError || startVisual.isError) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header assessmentId={assessmentId} />
        <main className="max-w-4xl mx-auto w-full p-6">
          <ErrorState
            error={presentationsError || startVisual.error}
            title="Görsel Aşama Başlatılamadı"
            onRetry={() => startVisual.mutate()}
          />
        </main>
        <Footer />
      </div>
    );
  }

  const list = presentations || [];
  const totalPresentations = list.length;
  const answeredCount = Object.keys(selectedChoices).length;
  const isAllAnswered = totalPresentations > 0 && answeredCount >= totalPresentations;

  const handleSelectChoice = (stimulusKey: string, choice: VisualChoiceEnum) => {
    setSelectedChoices((prev) => ({ ...prev, [stimulusKey]: choice }));
    saveResponse.mutate({ stimulusKey, choice });
  };

  const handleComplete = async () => {
    try {
      await completeVisual.mutateAsync();
      await buildProfile.mutateAsync();
      router.push(`/assessment/${assessmentId}/profile`);
    } catch {
      // Error handled by mutation state
    }
  };

  const resolveAssetUrl = (pathUrl: string) => {
    if (pathUrl.startsWith("http")) return pathUrl;
    return `${API_BASE_URL}${pathUrl.startsWith("/") ? "" : "/"}${pathUrl}`;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header assessmentId={assessmentId} />

      <main className="max-w-5xl mx-auto w-full px-6 py-8 flex-1 space-y-6">
        <ProgressSteps assessmentId={assessmentId} currentStep="visual" />

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Aşama 2: Görsel A/B Karşılaştırma
            </h1>
            <p className="text-slate-400 text-xs sm:text-sm mt-1">
              Yan yana sunulan 6 görsel çiftinde gözünüze en uyumlu ve hoş gelen tarafı seçin.
            </p>
          </div>

          <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 px-4 py-2 rounded-xl text-xs font-mono">
            <span className="text-slate-400">İlerleme:</span>
            <span className="text-amber-400 font-bold">{answeredCount} / {totalPresentations}</span>
            {isAllAnswered && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
          </div>
        </div>

        {/* Visual Cards */}
        <div className="space-y-8">
          {list.map((p, idx) => {
            const currentChoice = selectedChoices[p.stimulus_key];

            return (
              <div
                key={p.id}
                className={`bg-slate-900/60 border rounded-2xl p-6 transition-all space-y-6 ${
                  currentChoice ? "border-slate-700/80 shadow-md" : "border-slate-800/60"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-amber-400 font-bold uppercase tracking-wider">
                    Görsel Çift {idx + 1}
                  </span>
                  {currentChoice && (
                    <span className="text-[10px] font-mono font-medium px-2 py-0.5 bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 rounded-lg">
                      Tercih Yapıldı
                    </span>
                  )}
                </div>

                {/* Side-by-side Asset Comparison */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
                  {/* Left Side */}
                  <div className="space-y-2 text-center">
                    <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 flex items-center justify-center min-h-[220px] max-h-[300px] overflow-hidden">
                      <img
                        src={resolveAssetUrl(p.left_asset_url)}
                        alt={`Görsel Çift ${idx + 1} Sol Seçenek`}
                        className="max-h-[260px] w-auto object-contain rounded"
                      />
                    </div>
                    <span className="text-xs font-mono text-slate-400">Sol Görsel</span>
                  </div>

                  {/* Right Side */}
                  <div className="space-y-2 text-center">
                    <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 flex items-center justify-center min-h-[220px] max-h-[300px] overflow-hidden">
                      <img
                        src={resolveAssetUrl(p.right_asset_url)}
                        alt={`Görsel Çift ${idx + 1} Sağ Seçenek`}
                        className="max-h-[260px] w-auto object-contain rounded"
                      />
                    </div>
                    <span className="text-xs font-mono text-slate-400">Sağ Görsel</span>
                  </div>
                </div>

                {/* Response Scale Buttons */}
                <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 pt-2 border-t border-slate-800/40">
                  {CHOICES.map((choice) => {
                    const isSelected = currentChoice === choice;

                    return (
                      <button
                        key={choice}
                        onClick={() => handleSelectChoice(p.stimulus_key, choice)}
                        className={`px-3 py-3 rounded-xl text-xs font-medium border transition-all text-center flex items-center justify-center ${
                          isSelected
                            ? "bg-amber-500 text-slate-950 border-amber-400 font-bold shadow-lg shadow-amber-500/20 scale-[1.02]"
                            : "bg-slate-950/80 text-slate-300 border-slate-800/80 hover:border-slate-700 hover:bg-slate-900"
                        }`}
                      >
                        <span>{VISUAL_CHOICE_LABELS[choice]}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {(completeVisual.isError || buildProfile.isError) && (
          <ErrorState
            error={completeVisual.error || buildProfile.error}
            title="Görsel Profil Oluşturulamadı"
          />
        )}

        <div className="pt-6 flex justify-end">
          <button
            onClick={handleComplete}
            disabled={!isAllAnswered || completeVisual.isPending || buildProfile.isPending}
            className="inline-flex items-center space-x-3 px-8 py-3.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-sm rounded-xl transition-all shadow-xl shadow-amber-500/20 disabled:opacity-40 disabled:pointer-events-none"
          >
            <span>Profilimi Oluştur ve İncele</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </main>

      <Footer />
    </div>
  );
}
