"use client";

import { useEffect, useState, use } from "react";
import { fetchUnifiedResultById, UnifiedUploadResult } from "@/lib/result-experience-api";
import UnifiedUploadResultPage from "@/components/result/UnifiedUploadResultPage";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import Link from "next/link";
import { Loader2, AlertCircle } from "lucide-react";

interface PageProps {
  params: Promise<{ analysisId: string }>;
}

export default function AnalysisResultPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const analysisId = resolvedParams.analysisId;

  const [result, setResult] = useState<UnifiedUploadResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadResult() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchUnifiedResultById(analysisId);
        setResult(data);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Analiz sonucu yüklenirken beklenmeyen bir hata oluştu.");
        }
      } finally {
        setLoading(false);
      }
    }

    if (analysisId) {
      loadResult();
    }
  }, [analysisId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header />
        <main className="flex-1 flex flex-col items-center justify-center p-8 space-y-4">
          <Loader2 className="w-10 h-10 text-amber-400 animate-spin" />
          <p className="text-sm font-mono text-slate-400">Analiz sonucu yükleniyor ({analysisId.slice(0, 8)}...)</p>
        </main>
        <Footer />
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header />
        <main className="flex-1 flex flex-col items-center justify-center p-8 max-w-lg mx-auto text-center space-y-4">
          <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-2xl text-rose-400">
            <AlertCircle className="w-8 h-8 mx-auto mb-2" />
            <h2 className="text-lg font-bold text-white mb-1">Analiz Sonucu Alınamadı</h2>
            <p className="text-xs text-rose-200">{error || "Sonuç bulunamadı."}</p>
          </div>
          <Link
            href="/analysis/new"
            className="px-6 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-xl transition-all"
          >
            Yeni Halı Yükleyin
          </Link>
        </main>
        <Footer />
      </div>
    );
  }

  return <UnifiedUploadResultPage result={result} />;
}
