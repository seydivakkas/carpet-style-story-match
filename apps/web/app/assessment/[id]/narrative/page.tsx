"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ProgressSteps from "@/components/ProgressSteps";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import {
  useAssessment,
  useUserNarrativeProfile,
  useCreateNarrativeProfile
} from "@/lib/api/preferences";
import { CANONICAL_NARRATIVE_THEMES_ORDER, NARRATIVE_THEME_DETAILS } from "@/lib/constants";
import { ArrowRight, BookOpen, Heart, Sparkles, AlertCircle } from "lucide-react";

export default function NarrativeSelectionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: assessmentId } = use(params);
  const router = useRouter();

  const { data: assessment, isLoading: assessmentLoading } = useAssessment(assessmentId);
  const { data: existingNarrative } = useUserNarrativeProfile(assessmentId);

  const createNarrative = useCreateNarrativeProfile(assessmentId);

  const [primaryThemes, setPrimaryThemes] = useState<string[]>([]);
  const [secondaryThemes, setSecondaryThemes] = useState<string[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const togglePrimary = (key: string) => {
    setErrorMsg(null);
    if (primaryThemes.includes(key)) {
      setPrimaryThemes(primaryThemes.filter((k) => k !== key));
    } else {
      if (primaryThemes.length >= 3) {
        setErrorMsg("En fazla 3 adet ana ilgi teması seçebilirsiniz.");
        return;
      }
      if (secondaryThemes.includes(key)) {
        setSecondaryThemes(secondaryThemes.filter((k) => k !== key));
      }
      setPrimaryThemes([...primaryThemes, key]);
    }
  };

  const toggleSecondary = (key: string) => {
    setErrorMsg(null);
    if (secondaryThemes.includes(key)) {
      setSecondaryThemes(secondaryThemes.filter((k) => k !== key));
    } else {
      if (secondaryThemes.length >= 3) {
        setErrorMsg("En fazla 3 adet ikincil ilgi teması seçebilirsiniz.");
        return;
      }
      if (primaryThemes.includes(key)) {
        setPrimaryThemes(primaryThemes.filter((k) => k !== key));
      }
      setSecondaryThemes([...secondaryThemes, key]);
    }
  };

  const handleSubmit = async (skip: boolean = false) => {
    setErrorMsg(null);
    try {
      await createNarrative.mutateAsync({
        skip,
        primary_themes: skip ? [] : primaryThemes,
        secondary_themes: skip ? [] : secondaryThemes
      });
      router.push(`/assessment/${assessmentId}/complete`);
    } catch {
      // Error handled by mutation
    }
  };

  if (assessmentLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header assessmentId={assessmentId} />
        <LoadingState message="Hikâye temaları yükleniyor..." />
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header assessmentId={assessmentId} />

      <main className="max-w-4xl mx-auto w-full px-6 py-8 flex-1 space-y-6">
        <ProgressSteps assessmentId={assessmentId} currentStep="narrative" />

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Aşama 5: Kültürel Motif Hikâye Temaları
            </h1>
            <p className="text-slate-400 text-xs sm:text-sm mt-1">
              Halı motiflerinin belgelenmiş anlatılarından sizi en çok çeken temaları işaretleyin.
            </p>
          </div>

          <div className="flex items-center space-x-3 text-xs font-mono">
            <span className="px-3 py-1 bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 rounded-xl">
              Ana İlgi: {primaryThemes.length} / 3
            </span>
            <span className="px-3 py-1 bg-amber-500/10 text-amber-300 border border-amber-500/30 rounded-xl">
              İkincil İlgi: {secondaryThemes.length} / 3
            </span>
          </div>
        </div>

        {errorMsg && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-3 text-xs text-rose-300 flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* 8 Themes Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {CANONICAL_NARRATIVE_THEMES_ORDER.map((key) => {
            const theme = NARRATIVE_THEME_DETAILS[key];
            const isPrimary = primaryThemes.includes(key);
            const isSecondary = secondaryThemes.includes(key);

            return (
              <div
                key={key}
                className={`bg-slate-900/60 border rounded-2xl p-5 flex flex-col justify-between space-y-4 transition-all ${
                  isPrimary
                    ? "border-emerald-500/50 bg-emerald-500/5 shadow-md"
                    : isSecondary
                    ? "border-amber-500/50 bg-amber-500/5 shadow-md"
                    : "border-slate-800/80"
                }`}
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="text-xl">{theme.icon}</span>
                      <span className="font-mono text-xs font-bold text-emerald-400">
                        {theme.code}
                      </span>
                      <h3 className="font-semibold text-base text-slate-100">
                        {theme.label_tr}
                      </h3>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {theme.description}
                  </p>
                </div>

                {/* Choices buttons */}
                <div className="flex items-center space-x-2 pt-2 border-t border-slate-800/40">
                  <button
                    onClick={() => togglePrimary(key)}
                    className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold border transition-all flex items-center justify-center space-x-1.5 ${
                      isPrimary
                        ? "bg-emerald-500 text-slate-950 border-emerald-400 shadow"
                        : "bg-slate-950/60 text-slate-400 border-slate-800 hover:border-slate-700 hover:text-slate-200"
                    }`}
                  >
                    <Heart className="w-3.5 h-3.5" />
                    <span>Ana İlgi</span>
                  </button>

                  <button
                    onClick={() => toggleSecondary(key)}
                    className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold border transition-all flex items-center justify-center space-x-1.5 ${
                      isSecondary
                        ? "bg-amber-500 text-slate-950 border-amber-400 shadow"
                        : "bg-slate-950/60 text-slate-400 border-slate-800 hover:border-slate-700 hover:text-slate-200"
                    }`}
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>İkincil İlgi</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {createNarrative.isError && (
          <ErrorState error={createNarrative.error} title="Hikâye Temaları Kaydedilemedi" />
        )}

        <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <button
            onClick={() => handleSubmit(true)}
            disabled={createNarrative.isPending}
            className="text-xs text-slate-400 hover:text-slate-200 underline underline-offset-4 font-medium transition-colors"
          >
            Hikâye temalarını şimdilik atla
          </button>

          <button
            onClick={() => handleSubmit(false)}
            disabled={createNarrative.isPending}
            className="inline-flex items-center space-x-3 px-8 py-3.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-sm rounded-xl transition-all shadow-xl shadow-amber-500/20 disabled:opacity-40 disabled:pointer-events-none w-full sm:w-auto justify-center"
          >
            <span>Değerlendirmeyi Tamamla</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </main>

      <Footer />
    </div>
  );
}
