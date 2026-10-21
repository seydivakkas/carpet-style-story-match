"use client";

import { useEffect, useState, use } from "react";
import { fetchAnalysisStatus, fetchUnifiedResultById, fetchAnalysisImageObjectUrl, UnifiedUploadResult } from "@/lib/result-experience-api";
import UnifiedUploadResultPage from "@/components/result/UnifiedUploadResultPage";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import Link from "next/link";
import { Loader2, AlertCircle } from "lucide-react";
import { ApiClientError } from "@/lib/api/client";

interface PageProps {
  params: Promise<{ analysisId: string }>;
}

export default function AnalysisResultPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const analysisId = resolvedParams.analysisId;

  const [result, setResult] = useState<UnifiedUploadResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const url = result?.image_meta.primary_image_url;
    return () => {
      if (url?.startsWith("blob:")) URL.revokeObjectURL(url);
    };
  }, [result?.image_meta.primary_image_url]);

  useEffect(() => {
    let isCancelled = false;
    let timerId: NodeJS.Timeout | null = null;

    const startTime = Date.now();
    let transientErrors = 0;
    timerId = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    async function poll() {
      try {
        setLoading(true);
        setError(null);

        while (!isCancelled) {
          try {
            const statusRes = await fetchAnalysisStatus(analysisId);
            transientErrors = 0;
            if (isCancelled) break;

            if (statusRes.status === "COMPLETED" || statusRes.status === "BLOCKED_BY_QUALITY") {
              const resData = await fetchUnifiedResultById(analysisId);
              let privateImageUrl = "";
              try {
                privateImageUrl = await fetchAnalysisImageObjectUrl(analysisId);
              } catch {
                // Görsel izni olmayan ya da dosyası silinmiş kayıt sonuçsuz kalmaz.
              }
              if (!isCancelled) {
                setResult({...resData, image_meta:{...resData.image_meta,primary_image_url:privateImageUrl}});
              } else if (privateImageUrl) {
                URL.revokeObjectURL(privateImageUrl);
              }
              if (!isCancelled) {
                setLoading(false);

                // Ensure stored in recent analyses
                try {
                  const newEntry = {
                    id: analysisId,
                    fileName: "Halı Analiz Raporu",
                    timestamp: new Date().toISOString()
                  };
                  const existing = JSON.parse(localStorage.getItem("carpet_recent_analyses") || "[]");
                  const updated = [newEntry, ...existing.filter((x: any) => x.id !== analysisId)].slice(0, 10);
                  localStorage.setItem("carpet_recent_analyses", JSON.stringify(updated));
                } catch {
                  // ignore storage error
                }
              }
              return;
            }

            if (statusRes.status === "FAILED") {
              if (!isCancelled) {
                setError(statusRes.error || "Analiz işlemi sırasında sunucu hatası oluştu.");
                setLoading(false);
              }
              return;
            }
          } catch (fetchErr: unknown) {
            if (fetchErr instanceof ApiClientError && fetchErr.status === 403) {
              if (!isCancelled) {
                setError("Bu analize erişim anahtarı bulunamadı veya geçersiz. Yalnızca analiz sahibinin oturumu erişebilir.");
                setLoading(false);
              }
              return;
            }
            if (fetchErr instanceof ApiClientError && fetchErr.status === 404) {
              if (!isCancelled) {
                setError("Analiz kaydı bulunamadı.");
                setLoading(false);
              }
              return;
            }
            transientErrors += 1;
            if (transientErrors >= 5) {
              if (!isCancelled) {
                setError("Sunucuya erişilemiyor. Bağlantıyı kontrol edip yeniden deneyin.");
                setLoading(false);
              }
              return;
            }
          }

          if (Date.now() - startTime >= 90000) {
            if (!isCancelled) {
              setError("Analiz süresi zaman aşımına uğradı (90 saniye).");
              setLoading(false);
            }
            return;
          }

          await new Promise((resolve) => setTimeout(resolve, transientErrors ? Math.min(12000, 1500 * 2 ** transientErrors) : 1500));
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          if (err instanceof Error) {
            setError(err.message);
          } else {
            setError("Analiz süreci takip edilirken beklenmeyen bir hata oluştu.");
          }
          setLoading(false);
        }
      }
    }

    if (analysisId) {
      poll();
    }

    return () => {
      isCancelled = true;
      if (timerId) clearInterval(timerId);
    };
  }, [analysisId, retry]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header />
        <main className="flex-1 flex flex-col items-center justify-center p-8 space-y-6">
          <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-2xl text-amber-400">
            <Loader2 className="w-10 h-10 animate-spin mx-auto" />
          </div>
          <div className="text-center space-y-2">
            <h2 className="text-xl font-extrabold text-white">Analiz Sürüyor…</h2>
            <p className="text-xs font-mono text-slate-400">
              9D Style DNA, Renk Analizi ve Motif Tespiti çalıştırılıyor ({elapsedSeconds} saniye)
            </p>
          </div>
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
          <button
            type="button"
            onClick={() => { setLoading(true); setError(null); setElapsedSeconds(0); setRetry((n) => n + 1); }}
            className="px-6 py-2.5 bg-slate-700 hover:bg-slate-600 text-white font-bold text-xs rounded-xl"
          >Yeniden Dene</button>
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
