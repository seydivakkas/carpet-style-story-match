"use client";

import { useRouter } from "next/navigation";
import { useCreateAssessment } from "@/lib/api/preferences";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ErrorState from "@/components/ErrorState";
import { Sparkles, FileText, Image as ImageIcon, Sliders, Star, BookOpen, ArrowRight, Loader2 } from "lucide-react";

export default function NewAssessmentPage() {
  const router = useRouter();
  const createAssessment = useCreateAssessment();

  const handleStart = async () => {
    try {
      const newAssessment = await createAssessment.mutateAsync();
      if (typeof window !== "undefined") {
        localStorage.setItem("last_assessment_id", newAssessment.id);
      }
      router.push(`/assessment/${newAssessment.id}/text`);
    } catch {
      // Error handled by mutation error state
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header />

      <main className="max-w-4xl mx-auto w-full px-6 py-12 flex-1 space-y-8">
        <div className="text-center space-y-4 max-w-2xl mx-auto">
          <div className="inline-flex items-center space-x-2 px-3 py-1 bg-amber-500/10 border border-amber-500/30 rounded-full text-xs font-mono text-amber-400">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Estetik Tercih & Anlatı İlgisi Analizi</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
            Kişisel Estetik Profilinizi Oluşturun
          </h1>

          <p className="text-slate-400 text-sm sm:text-base leading-relaxed">
            Bu değerlendirme; açık ifadeler, kontrollü görsel A/B seçimleri ve öncelik belirleme adımlarıyla 9 boyutlu Görsel Tercih Profilinizi ve tematik ilgi haritanızı çıkarır.
          </p>
        </div>

        {/* Steps Card Overview */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 pt-4">
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 space-y-2">
            <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl w-max">
              <FileText className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-sm text-slate-200">1. Metin Soruları</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              6 açık estetik eğilim sorusu ile genel tasarım anlayışınızı belirleyin.
            </p>
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 space-y-2">
            <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl w-max">
              <ImageIcon className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-sm text-slate-200">2. Görsel Karşılaştırma</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              6 kontrollü görsel A/B kartında doğrudan gözünüze hitap eden tarafı seçin.
            </p>
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 space-y-2">
            <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl w-max">
              <Sliders className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-sm text-slate-200">3. Profil İnceleme</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Hesaplanan 9 boyutlu profilinizi görün, isterseniz değerleri manuel düzenleyin.
            </p>
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 space-y-2">
            <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl w-max">
              <Star className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-sm text-slate-200">4. Öncelik & Esneklik</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              En çok önem verdiğiniz ve esnek olduğunuz boyutları seçin.
            </p>
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 space-y-2">
            <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl w-max">
              <BookOpen className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-sm text-slate-200">5. Hikâye Temaları</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Kültürel motif hikâyelerine ilgi seviyenizi belirleyin (Doğa, Yuva, Zanaat vb.).
            </p>
          </div>

          <div className="bg-gradient-to-br from-amber-500/20 to-amber-600/10 border border-amber-500/40 rounded-2xl p-5 flex flex-col justify-between">
            <div className="space-y-1">
              <span className="text-[10px] font-mono text-amber-400 uppercase tracking-widest font-bold">Hazır mısınız?</span>
              <h3 className="font-bold text-sm text-white">Profilinizi Çıkarın</h3>
            </div>
            <p className="text-xs text-amber-200/80 mt-2">
              Yaklaşık 3-4 dakika sürer. Hesapsız, anonim başlatabilirsiniz.
            </p>
          </div>
        </div>

        {createAssessment.isError && (
          <ErrorState
            error={createAssessment.error}
            title="Değerlendirme Başlatılamadı"
            onRetry={handleStart}
          />
        )}

        <div className="pt-6 flex justify-center">
          <button
            onClick={handleStart}
            disabled={createAssessment.isPending}
            className="inline-flex items-center space-x-3 px-8 py-4 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-base rounded-2xl transition-all shadow-xl shadow-amber-500/20 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none"
          >
            {createAssessment.isPending ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Oluşturuluyor...</span>
              </>
            ) : (
              <>
                <span>Değerlendirmeyi Başlat</span>
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </div>
      </main>

      <Footer />
    </div>
  );
}
