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
  useUserPreferenceProfile,
  useImportanceProfile,
  useCreateImportanceProfile
} from "@/lib/api/preferences";
import { CANONICAL_DIMENSIONS_ORDER, DIMENSION_DETAILS } from "@/lib/constants";
import { ArrowRight, Star, SlidersHorizontal, Check, AlertCircle } from "lucide-react";

export default function ImportanceSelectionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: assessmentId } = use(params);
  const router = useRouter();

  const { data: assessment, isLoading: assessmentLoading } = useAssessment(assessmentId);
  const { data: userProfile } = useUserPreferenceProfile(assessmentId);
  const { data: existingImportance } = useImportanceProfile(assessmentId);

  const createImportance = useCreateImportanceProfile(assessmentId);

  const [priorityDims, setPriorityDims] = useState<string[]>([]);
  const [flexibleDims, setFlexibleDims] = useState<string[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const togglePriority = (key: string) => {
    setErrorMsg(null);
    if (priorityDims.includes(key)) {
      setPriorityDims(priorityDims.filter((k) => k !== key));
    } else {
      if (priorityDims.length >= 3) {
        setErrorMsg("En fazla 3 adet öncelikli boyut seçebilirsiniz.");
        return;
      }
      if (flexibleDims.includes(key)) {
        setFlexibleDims(flexibleDims.filter((k) => k !== key));
      }
      setPriorityDims([...priorityDims, key]);
    }
  };

  const toggleFlexible = (key: string) => {
    setErrorMsg(null);
    if (flexibleDims.includes(key)) {
      setFlexibleDims(flexibleDims.filter((k) => k !== key));
    } else {
      if (flexibleDims.length >= 3) {
        setErrorMsg("En fazla 3 adet esnek boyut seçebilirsiniz.");
        return;
      }
      if (priorityDims.includes(key)) {
        setPriorityDims(priorityDims.filter((k) => k !== key));
      }
      setFlexibleDims([...flexibleDims, key]);
    }
  };

  const handleSubmit = async (skip: boolean = false) => {
    setErrorMsg(null);
    try {
      await createImportance.mutateAsync({
        skip,
        priority_dimensions: skip ? [] : priorityDims,
        flexible_dimensions: skip ? [] : flexibleDims
      });
      router.push(`/assessment/${assessmentId}/narrative`);
    } catch {
      // Error handled by mutation
    }
  };

  if (assessmentLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header assessmentId={assessmentId} />
        <LoadingState message="Öncelik seçimi yükleniyor..." />
        <Footer />
      </div>
    );
  }

  const isExisting = Boolean(existingImportance);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header assessmentId={assessmentId} />

      <main className="max-w-4xl mx-auto w-full px-6 py-8 flex-1 space-y-6">
        <ProgressSteps assessmentId={assessmentId} currentStep="importance" />

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Aşama 4: Öncelik ve Esneklik Tercihleri
            </h1>
            <p className="text-slate-400 text-xs sm:text-sm mt-1">
              Halı eşleşmesinde sizin için olmazsa olmaz boyutları ve esnek kalabileceğiniz boyutları belirleyin.
            </p>
          </div>

          <div className="flex items-center space-x-3 text-xs font-mono">
            <span className="px-3 py-1 bg-amber-500/10 text-amber-300 border border-amber-500/30 rounded-xl">
              Öncelikli: {priorityDims.length} / 3
            </span>
            <span className="px-3 py-1 bg-blue-500/10 text-blue-300 border border-blue-500/30 rounded-xl">
              Esnek: {flexibleDims.length} / 3
            </span>
          </div>
        </div>

        {errorMsg && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-3 text-xs text-rose-300 flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* 9D Dimension Selection Grid */}
        <div className="space-y-3">
          {CANONICAL_DIMENSIONS_ORDER.map((key) => {
            const meta = DIMENSION_DETAILS[key];
            const isPriority = priorityDims.includes(key);
            const isFlexible = flexibleDims.includes(key);

            return (
              <div
                key={key}
                className={`bg-slate-900/60 border rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 transition-all ${
                  isPriority
                    ? "border-amber-500/50 bg-amber-500/5 shadow-md"
                    : isFlexible
                    ? "border-blue-500/50 bg-blue-500/5 shadow-md"
                    : "border-slate-800/80"
                }`}
              >
                <div className="flex items-center space-x-3">
                  <span className="font-mono text-xs font-bold text-amber-400 px-2.5 py-1 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                    {meta.code}
                  </span>
                  <div>
                    <h3 className="font-semibold text-sm text-slate-100">{meta.label_tr}</h3>
                    <p className="text-[11px] text-slate-400">
                      {meta.min_label} ↔ {meta.max_label}
                    </p>
                  </div>
                </div>

                {/* Selection Buttons */}
                <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
                  <button
                    onClick={() => togglePriority(key)}
                    disabled={isExisting}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all flex items-center space-x-1.5 ${
                      isPriority
                        ? "bg-amber-500 text-slate-950 border-amber-400 shadow"
                        : "bg-slate-950/60 text-slate-400 border-slate-800 hover:border-slate-700 hover:text-slate-200"
                    }`}
                  >
                    <Star className="w-3.5 h-3.5" />
                    <span>Öncelikli</span>
                  </button>

                  <button
                    onClick={() => toggleFlexible(key)}
                    disabled={isExisting}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all flex items-center space-x-1.5 ${
                      isFlexible
                        ? "bg-blue-500 text-slate-950 border-blue-400 shadow"
                        : "bg-slate-950/60 text-slate-400 border-slate-800 hover:border-slate-700 hover:text-slate-200"
                    }`}
                  >
                    <SlidersHorizontal className="w-3.5 h-3.5" />
                    <span>Esnek</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {createImportance.isError && (
          <ErrorState error={createImportance.error} title="Öncelikler Kaydedilemedi" />
        )}

        <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <button
            onClick={() => handleSubmit(true)}
            disabled={createImportance.isPending}
            className="text-xs text-slate-400 hover:text-slate-200 underline underline-offset-4 font-medium transition-colors"
          >
            Özel bir önceliğim yok (Tümünü standart 0.6 ağırlıkla kullan)
          </button>

          <button
            onClick={() => handleSubmit(false)}
            disabled={createImportance.isPending}
            className="inline-flex items-center space-x-3 px-8 py-3.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-sm rounded-xl transition-all shadow-xl shadow-amber-500/20 disabled:opacity-40 disabled:pointer-events-none w-full sm:w-auto justify-center"
          >
            <span>Öncelikleri Kaydet ve Devam Et</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </main>

      <Footer />
    </div>
  );
}
