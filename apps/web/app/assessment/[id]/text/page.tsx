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
  useTextQuestionsMeta,
  useTextResponses,
  useSaveTextResponse,
  useCompleteTextAssessment
} from "@/lib/api/preferences";
import { TEXT_CHOICE_LABELS } from "@/lib/constants";
import { TextChoiceEnum } from "@/lib/types/api";
import { ArrowRight, CheckCircle2, HelpCircle } from "lucide-react";

const CHOICES: TextChoiceEnum[] = [
  "STRONGLY_A",
  "SLIGHTLY_A",
  "NEUTRAL",
  "SLIGHTLY_B",
  "STRONGLY_B"
];

export default function TextPreferencesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: assessmentId } = use(params);
  const router = useRouter();

  const { data: assessment, isLoading: assessmentLoading, error: assessmentError } = useAssessment(assessmentId);
  const { data: questions, isLoading: questionsLoading, error: questionsError } = useTextQuestionsMeta();
  const { data: existingResponses } = useTextResponses(assessmentId);

  const saveResponse = useSaveTextResponse(assessmentId);
  const completeText = useCompleteTextAssessment(assessmentId);

  const [selectedChoices, setSelectedChoices] = useState<Record<string, TextChoiceEnum>>({});

  useEffect(() => {
    if (existingResponses && existingResponses.length > 0) {
      const map: Record<string, TextChoiceEnum> = {};
      existingResponses.forEach((r) => {
        map[r.question_key] = r.choice;
      });
      setSelectedChoices(map);
    }
  }, [existingResponses]);

  if (assessmentLoading || questionsLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header assessmentId={assessmentId} />
        <LoadingState message="Metin tercihi soruları yükleniyor..." />
        <Footer />
      </div>
    );
  }

  if (assessmentError || questionsError) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header assessmentId={assessmentId} />
        <main className="max-w-4xl mx-auto w-full p-6">
          <ErrorState error={assessmentError || questionsError} title="Sorular Yüklenemedi" />
        </main>
        <Footer />
      </div>
    );
  }

  const rawQuestions = Array.isArray(questions)
    ? questions
    : (questions as unknown as { questions?: typeof questions })?.questions || [];
  const sortedQuestions = [...rawQuestions].sort((a, b) => a.order - b.order);
  const totalQuestions = sortedQuestions.length;
  const answeredCount = Object.keys(selectedChoices).length;
  const isAllAnswered = totalQuestions > 0 && answeredCount >= totalQuestions;

  const handleSelectChoice = (questionKey: string, choice: TextChoiceEnum) => {
    setSelectedChoices((prev) => ({ ...prev, [questionKey]: choice }));
    saveResponse.mutate({ questionKey, choice });
  };

  const handleComplete = async () => {
    try {
      await completeText.mutateAsync();
      router.push(`/assessment/${assessmentId}/visual`);
    } catch {
      // Error handled by mutation state
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header assessmentId={assessmentId} />

      <main className="max-w-4xl mx-auto w-full px-6 py-8 flex-1 space-y-6">
        <ProgressSteps assessmentId={assessmentId} currentStep="text" />

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Aşama 1: Metin Bazlı Estetik Tercihler
            </h1>
            <p className="text-slate-400 text-xs sm:text-sm mt-1">
              Aşağıdaki 6 soru için tasarım anlayışınızı en iyi yansıtan seçeneği işaretleyin.
            </p>
          </div>

          <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 px-4 py-2 rounded-xl text-xs font-mono">
            <span className="text-slate-400">İlerleme:</span>
            <span className="text-amber-400 font-bold">{answeredCount} / {totalQuestions}</span>
            {isAllAnswered && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
          </div>
        </div>

        {/* Question Cards */}
        <div className="space-y-6">
          {sortedQuestions.map((q, idx) => {
            const qKey = q.question_key || (q as unknown as { key: string }).key;
            const currentChoice = selectedChoices[qKey];

            return (
              <div
                key={qKey}
                className={`bg-slate-900/60 border rounded-2xl p-6 transition-all space-y-4 ${
                  currentChoice
                    ? "border-slate-700/80 shadow-md"
                    : "border-slate-800/60 opacity-90"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono text-amber-400 font-bold uppercase tracking-wider">
                      Soru {idx + 1}
                    </span>
                    <h3 className="font-semibold text-base text-slate-100 flex items-center space-x-2">
                      <span>{q.option_a_tr}</span>
                      <span className="text-slate-500 font-normal">veya</span>
                      <span>{q.option_b_tr}</span>
                    </h3>
                  </div>

                  {currentChoice && (
                    <span className="text-[10px] font-mono font-medium px-2 py-1 bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 rounded-lg">
                      Yanıtlandı
                    </span>
                  )}
                </div>

                {/* Options scale */}
                <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 pt-2">
                  {CHOICES.map((choice) => {
                    const isSelected = currentChoice === choice;
                    return (
                      <button
                        key={choice}
                        onClick={() => handleSelectChoice(qKey, choice)}
                        className={`px-3 py-2.5 rounded-xl text-xs font-medium border transition-all text-center flex flex-col items-center justify-center space-y-1 ${
                          isSelected
                            ? "bg-amber-500 text-slate-950 border-amber-400 font-bold shadow-lg shadow-amber-500/20 scale-[1.02]"
                            : "bg-slate-950/80 text-slate-300 border-slate-800/80 hover:border-slate-700 hover:bg-slate-900"
                        }`}
                      >
                        <span>{TEXT_CHOICE_LABELS[choice]}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {completeText.isError && (
          <ErrorState error={completeText.error} title="Metin Aşaması Tamamlanamadı" />
        )}

        <div className="pt-6 flex justify-end">
          <button
            onClick={handleComplete}
            disabled={!isAllAnswered || completeText.isPending}
            className="inline-flex items-center space-x-3 px-8 py-3.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-sm rounded-xl transition-all shadow-xl shadow-amber-500/20 disabled:opacity-40 disabled:pointer-events-none"
          >
            <span>Görsel Karşılaştırmaya Geç</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </main>

      <Footer />
    </div>
  );
}
