"use client";

import { use, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ProgressSteps from "@/components/ProgressSteps";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import DimensionBar from "@/components/DimensionBar";
import {
  useAssessment,
  useUserPreferenceProfile,
  useConfidenceProfile,
  useOverrideDimension,
  useConfirmProfile
} from "@/lib/api/preferences";
import { CANONICAL_DIMENSIONS_ORDER } from "@/lib/constants";
import { ArrowRight, CheckCircle, Info, Lock } from "lucide-react";

export default function ProfileReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: assessmentId } = use(params);
  const router = useRouter();

  const { data: assessment, isLoading: assessmentLoading } = useAssessment(assessmentId);
  const { data: profile, isLoading: profileLoading, error: profileError } = useUserPreferenceProfile(assessmentId);
  const { data: confidenceProfile } = useConfidenceProfile(assessmentId);

  const overrideDim = useOverrideDimension(assessmentId);
  const confirmProfile = useConfirmProfile(assessmentId);

  const [dimensionValues, setDimensionValues] = useState<Record<string, number>>({});

  useEffect(() => {
    if (profile && profile.dimensions) {
      const map: Record<string, number> = {};
      profile.dimensions.forEach((d) => {
        map[d.dimension_key] = d.final_value;
      });
      setDimensionValues(map);
    }
  }, [profile]);

  if (assessmentLoading || profileLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header assessmentId={assessmentId} />
        <LoadingState message="Multimodal 9D estetik tercih profiliniz hesaplanıyor..." />
        <Footer />
      </div>
    );
  }

  if (profileError) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header assessmentId={assessmentId} />
        <main className="max-w-4xl mx-auto w-full p-6">
          <ErrorState error={profileError} title="Profil Yüklenemedi" />
        </main>
        <Footer />
      </div>
    );
  }

  const isConfirmed = profile?.is_confirmed || profile?.is_reviewed || false;

  const handleSliderChange = (dimKey: string, val: number) => {
    if (isConfirmed) return;
    setDimensionValues((prev) => ({ ...prev, [dimKey]: val }));
    overrideDim.mutate({ dimensionKey: dimKey, value: val });
  };

  const handleConfirm = async () => {
    try {
      if (!isConfirmed) {
        await confirmProfile.mutateAsync();
      }
      router.push(`/assessment/${assessmentId}/importance`);
    } catch {
      // Error handled by mutation
    }
  };

  // Build confidence lookup
  const confidenceMap: Record<string, "HIGH" | "MODERATE" | "LOW"> = {};
  if (confidenceProfile && confidenceProfile.dimensions) {
    confidenceProfile.dimensions.forEach((cd) => {
      confidenceMap[cd.dimension_key] = cd.confidence_level;
    });
  }

  // Build dimension map for order rendering
  const dimsMap = new Map(profile?.dimensions.map((d) => [d.dimension_key, d]));

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header assessmentId={assessmentId} />

      <main className="max-w-4xl mx-auto w-full px-6 py-8 flex-1 space-y-6">
        <ProgressSteps assessmentId={assessmentId} currentStep="profile" />

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                Aşama 3: 9D Görsel Estetik Tercih Profiliniz
              </h1>
              {isConfirmed && (
                <span className="inline-flex items-center space-x-1 text-xs font-medium px-2.5 py-1 bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 rounded-full">
                  <Lock className="w-3 h-3" />
                  <span>Kilitli</span>
                </span>
              )}
            </div>
            <p className="text-slate-400 text-xs sm:text-sm mt-1">
              Metin ve görsel tercihlerinizden elde edilen multimodal 9 boyutlu estetik karakteriniz.
            </p>
          </div>
        </div>

        {/* Confidence Help Banner */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 flex items-start space-x-3 text-xs text-slate-300 leading-relaxed">
          <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-slate-200 block">
              Kanıt Gücü &amp; Tercih Değeri Ayrımı:
            </span>
            <p className="text-slate-400">
              Bu sayfadaki <b>Kanıt Seviyesi</b> (Kanıt: Yüksek / Orta / Düşük), sistemin mevcut cevaplarınızdan bu tercihi ne kadar tutarlı çıkardığını gösterir. Tercihinizin büyüklüğünü veya önemini temsil etmez. İsterseniz slider ile değerlerinizi güncelleyebilirsiniz.
            </p>
          </div>
        </div>

        {/* 9D Dimension Bars */}
        <div className="space-y-4">
          {CANONICAL_DIMENSIONS_ORDER.map((key) => {
            const dimObj = dimsMap.get(key);
            if (!dimObj) return null;

            const currentValue = dimensionValues[key] ?? dimObj.final_value;

            return (
              <DimensionBar
                key={key}
                dimensionKey={key}
                inferredValue={dimObj.inferred_value}
                userOverrideValue={dimObj.user_override_value}
                finalValue={currentValue}
                provenance={dimObj.provenance}
                confidenceLevel={confidenceMap[key]}
                isInteractive={!isConfirmed}
                onOverrideChange={(val) => handleSliderChange(key, val)}
              />
            );
          })}
        </div>

        {confirmProfile.isError && (
          <ErrorState error={confirmProfile.error} title="Profil Onaylanamadı" />
        )}

        <div className="pt-6 flex justify-end">
          <button
            onClick={handleConfirm}
            disabled={confirmProfile.isPending}
            className="inline-flex items-center space-x-3 px-8 py-3.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-sm rounded-xl transition-all shadow-xl shadow-amber-500/20 disabled:opacity-40 disabled:pointer-events-none"
          >
            {isConfirmed ? (
              <>
                <span>Öncelik Seçimine Devam Et</span>
                <ArrowRight className="w-4 h-4" />
              </>
            ) : (
              <>
                <CheckCircle className="w-4 h-4" />
                <span>Profilimi Onayla ve Devam Et</span>
              </>
            )}
          </button>
        </div>
      </main>

      <Footer />
    </div>
  );
}
