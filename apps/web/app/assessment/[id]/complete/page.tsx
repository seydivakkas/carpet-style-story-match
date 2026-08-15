"use client";

import { use } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ProgressSteps from "@/components/ProgressSteps";
import LoadingState from "@/components/LoadingState";
import {
  useAssessment,
  useUserPreferenceProfile,
  useImportanceProfile,
  useUserNarrativeProfile
} from "@/lib/api/preferences";
import { CheckCircle2, Layers, Star, BookOpen, ArrowRight, Compass } from "lucide-react";

export default function AssessmentCompletePage({ params }: { params: Promise<{ id: string }> }) {
  const { id: assessmentId } = use(params);

  const { data: assessment, isLoading: assessmentLoading } = useAssessment(assessmentId);
  const { data: userProfile } = useUserPreferenceProfile(assessmentId);
  const { data: importanceProfile } = useImportanceProfile(assessmentId);
  const { data: narrativeProfile } = useUserNarrativeProfile(assessmentId);

  if (assessmentLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header assessmentId={assessmentId} />
        <LoadingState message="Değerlendirme özetiniz yükleniyor..." />
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header assessmentId={assessmentId} />

      <main className="max-w-4xl mx-auto w-full px-6 py-8 flex-1 space-y-8">
        <ProgressSteps assessmentId={assessmentId} currentStep="complete" />

        <div className="text-center space-y-3 max-w-xl mx-auto">
          <div className="w-16 h-16 bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 rounded-full flex items-center justify-center mx-auto shadow-lg shadow-emerald-500/10">
            <CheckCircle2 className="w-8 h-8" />
          </div>

          <h1 className="text-3xl font-bold tracking-tight text-white">
            Tebrikler! Estetik Profiliniz Hazır
          </h1>

          <p className="text-slate-400 text-sm leading-relaxed">
            Metin soruları, görsel karşılaştırmalar, boyut öncelikleri ve hikâye temaları başarıyla kaydedildi. Artık kataloğu ve müze referanslarını kendi profilinizle karşılaştırabilirsiniz.
          </p>
        </div>

        {/* Readiness Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
          {/* Aesthetic Profile Card */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-3">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-100 text-sm">9D Görsel Profil</h3>
                <span className="text-[11px] font-mono text-emerald-400">HAZIR</span>
              </div>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              9 boyutlu estetik tercihleriniz tamamlandı ve onaylandı.
            </p>
          </div>

          {/* Importance Profile Card */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-3">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 bg-blue-500/10 text-blue-400 rounded-xl">
                <Star className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-100 text-sm">Öncelikler</h3>
                <span className="text-[11px] font-mono text-emerald-400">
                  {importanceProfile?.is_skipped ? "STANDART (ATLADI)" : "ÖZEL AYARLANDI"}
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Eşleşme ağırlıkları ve esneklik alanlarınız kaydedildi.
            </p>
          </div>

          {/* Narrative Profile Card */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-3">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 bg-emerald-500/10 text-emerald-400 rounded-xl">
                <BookOpen className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-100 text-sm">Hikâye Temaları</h3>
                <span className="text-[11px] font-mono text-emerald-400">
                  {narrativeProfile?.is_skipped ? "ATLADI" : "SEÇİLDİ"}
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              {narrativeProfile?.is_skipped
                ? "Hikâye temaları seçilmedi (varsayılan nötr)."
                : `${narrativeProfile?.selections.filter(s => s.interest_level === "PRIMARY").length || 0} ana ilgi teması seçildi.`}
            </p>
          </div>
        </div>

        {/* Action CTAs */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href={`/catalog?assessment=${assessmentId}`}
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-3 px-8 py-4 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-sm rounded-2xl transition-all shadow-xl shadow-amber-500/20"
          >
            <span>Katalog Halılarına Göz At</span>
            <ArrowRight className="w-4 h-4" />
          </Link>

          <Link
            href={`/historical-references?assessment=${assessmentId}`}
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-3 px-8 py-4 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 font-semibold text-sm rounded-2xl transition-all"
          >
            <Compass className="w-4 h-4 text-amber-400" />
            <span>Tarihsel Müze Referanslarını İncele</span>
          </Link>
        </div>
      </main>

      <Footer />
    </div>
  );
}
