"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { startAnalysis, deleteAnalysisRecord, fetchModelAcceptance, ModelAcceptance } from "@/lib/result-experience-api";
import { Upload, Sparkles, AlertCircle, Loader2, ArrowLeft, History, ArrowUpRight, ShieldCheck, Trash2, CheckCircle2 } from "lucide-react";

interface RecentAnalysisEntry {
  id: string;
  fileName: string;
  timestamp: string;
}

export default function NewUploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [recentAnalyses, setRecentAnalyses] = useState<RecentAnalysisEntry[]>([]);
  const [modelAcceptance, setModelAcceptance] = useState<ModelAcceptance | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("carpet_recent_analyses");
      if (stored) {
        setRecentAnalyses(JSON.parse(stored));
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchModelAcceptance().then((result) => {
      if (!cancelled) setModelAcceptance(result);
    }).catch(() => {
      // Servis erişimi yoksa bilimsel bir başarı iddiasında bulunulmaz.
    });
    return () => { cancelled = true; };
  }, []);

  const handleDeleteRecent = async (id: string) => {
    try {
      setDeletingId(id);
      setError(null);
      await deleteAnalysisRecord(id);
      
      const updated = recentAnalyses.filter((x) => x.id !== id);
      setRecentAnalyses(updated);
      localStorage.setItem("carpet_recent_analyses", JSON.stringify(updated));
      setSuccessMsg("Analiz kaydı ve veritabanı verileri başarıyla silindi.");
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(`Silme hatası: ${err.message}`);
      } else {
        setError("Kayıt silinirken bir hata oluştu.");
      }
    } finally {
      setDeletingId(null);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm("Tüm geçmiş analiz kayıtları veritabanından ve listeden silinecek. Emin misiniz?")) {
      return;
    }
    setError(null);
    setSuccessMsg(null);
    const failed: RecentAnalysisEntry[] = [];
    let deleted = 0;
    for (const item of recentAnalyses) {
      try {
        await deleteAnalysisRecord(item.id);
        deleted += 1;
      } catch {
        // Başarısız silmeleri listeden çıkarmayarak tekrar denemeyi mümkün kıl.
        failed.push(item);
      }
    }
    setRecentAnalyses(failed);
    if (failed.length) {
      localStorage.setItem("carpet_recent_analyses", JSON.stringify(failed));
      setError(`${deleted} analiz silindi, ${failed.length} analiz silinemedi. Kalanları tekrar deneyebilirsiniz.`);
    } else {
      localStorage.removeItem("carpet_recent_analyses");
      setSuccessMsg("Tüm geçmiş analiz kayıtları başarıyla silindi.");
      setTimeout(() => setSuccessMsg(null), 4000);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setPreviewUrl(URL.createObjectURL(selected));
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Lütfen analiz etmek için bir halı görseli seçin.");
      return;
    }

    try {
      setUploading(true);
      setError(null);
      const res = await startAnalysis(file);

      try {
        const newEntry: RecentAnalysisEntry = {
          id: res.analysis_id,
          fileName: file.name,
          timestamp: new Date().toISOString()
        };
        const existing: RecentAnalysisEntry[] = JSON.parse(
          localStorage.getItem("carpet_recent_analyses") || "[]"
        );
        const updated = [newEntry, ...existing.filter((x) => x.id !== res.analysis_id)].slice(0, 10);
        localStorage.setItem("carpet_recent_analyses", JSON.stringify(updated));
        setRecentAnalyses(updated);
      } catch {
        // ignore storage errors
      }

      router.push(`/analysis/${res.analysis_id}`);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Yükleme sırasında beklenmeyen bir hata oluştu.");
      }
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header />

      <main className="max-w-4xl mx-auto w-full px-6 py-12 flex-1 space-y-10">
        <div className="flex items-center space-x-3">
          <Link
            href="/"
            className="p-2 bg-slate-900 hover:bg-slate-800 rounded-xl border border-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">
              Yüklenen Halı Görsel Analizi
            </h1>
            <p className="text-slate-400 text-sm">
              Halı fotoğrafınızı yükleyin; görsel karakter analizini inceleyin. Motif çıkarımı ve tarihsel bağlantılar için doğrulanmamış çıktılar kesin bilgi olarak sunulmaz.
            </p>
          </div>
        </div>

        <div role="status" className="rounded-2xl border border-amber-600/40 bg-amber-950/30 p-4 text-amber-100 text-sm space-y-2">
          <p className="font-semibold">Motif modeli — bilimsel kabul bekliyor</p>
          <p>
            {modelAcceptance?.caution_tr ??
             "Gerçek motif dedektörünün bağımsız doğrulama kabulü henüz tamamlanmadı; kesin motif tanıma garantisi verilmez."}
          </p>
          {modelAcceptance && (
            <p className="text-xs text-amber-200/80">
              Kanıt envanteri: {modelAcceptance.available_artifacts}/{modelAcceptance.checked_artifacts} kaynak mevcut.
              Model doğruluk kabulü: {modelAcceptance.model_quality}.
            </p>
          )}
        </div>

        {successMsg && (
          <div className="flex items-center space-x-3 p-4 bg-emerald-950/80 border border-emerald-500/40 rounded-2xl text-emerald-300 text-sm shadow-lg animate-in fade-in">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
            <p className="font-medium">{successMsg}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-slate-900/80 border border-slate-800 rounded-3xl p-8 space-y-6 shadow-2xl">
          {/* File Upload Dropzone */}
          <div className="border-2 border-dashed border-slate-700 hover:border-amber-500/60 rounded-2xl p-8 text-center space-y-4 transition-colors cursor-pointer relative bg-slate-950/60">
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleFileChange}
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
            />

            {previewUrl ? (
              <div className="space-y-4 flex flex-col items-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={previewUrl}
                  alt="Yüklenen Halı Önizleme"
                  className="max-h-64 rounded-xl border border-slate-700 object-contain shadow-lg"
                />
                <span className="text-xs font-mono text-amber-300 font-bold">
                  {file?.name} ({file ? (file.size / (1024 * 1024)).toFixed(2) : 0} MB)
                </span>
              </div>
            ) : (
              <div className="space-y-3 flex flex-col items-center">
                <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-2xl text-amber-400">
                  <Upload className="w-8 h-8" />
                </div>
                <div className="space-y-1">
                  <p className="font-bold text-white text-base">
                    Halı fotoğrafı seçin veya buraya sürükleyin
                  </p>
                  <p className="text-xs text-slate-400 font-mono">
                    Desteklenen formatlar: JPEG, PNG, WebP (Maks. 25 MB)
                  </p>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="flex items-center space-x-3 p-4 bg-rose-950/60 border border-rose-800 rounded-xl text-rose-300 text-sm">
              <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
              <p>{error}</p>
            </div>
          )}

          {/* Submit Action */}
          <button
            type="submit"
            disabled={!file || uploading}
            className={`w-full py-4 rounded-2xl font-bold flex items-center justify-center space-x-2 transition-all shadow-xl ${
              !file || uploading
                ? "bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700"
                : "bg-amber-500 hover:bg-amber-400 text-slate-950 hover:shadow-amber-500/20 active:scale-[0.99]"
            }`}
          >
            {uploading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>YOLO & Style DNA Analizi Yapılıyor...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                <span>Halıyı Analiz Et & 5 Kartlı Raporu Oluştur</span>
              </>
            )}
          </button>
        </form>

        {/* Recent Analyses Persistence Section */}
        {recentAnalyses.length > 0 && (
          <section className="bg-slate-900/60 border border-slate-800/80 rounded-3xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 bg-amber-500/10 rounded-xl text-amber-400">
                  <History className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white tracking-tight">
                    Son Analiz Edilen Halılar
                  </h2>
                  <p className="text-xs text-slate-400 font-mono">
                    Daha önce yükleyip incelediğiniz halıların 5 kartlı raporlarına doğrudan erişin veya veritabanından silin.
                  </p>
                </div>
              </div>

              <button
                onClick={handleClearAll}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-900 hover:bg-rose-950/70 border border-slate-800 hover:border-rose-800/60 rounded-xl text-[11px] font-mono text-slate-400 hover:text-rose-300 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                <span>Tümünü Temizle</span>
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              {recentAnalyses.map((item) => (
                <div
                  key={item.id}
                  className="bg-slate-950/80 border border-slate-800 hover:border-amber-500/40 rounded-2xl p-4 flex items-center justify-between gap-4 transition-all group shadow-md"
                >
                  <div className="flex items-center space-x-3 min-w-0">
                    <div className="w-14 h-14 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex-shrink-0 flex items-center justify-center">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={`/api/v1/upload-analysis/${item.id}/image`}
                        alt={item.fileName}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                    </div>
                    <div className="min-w-0">
                      <span className="text-xs font-bold text-white truncate block group-hover:text-amber-300 transition-colors">
                        {item.fileName || "Halı Görseli"}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500 block truncate">
                        ID: {item.id.slice(0, 8)}...
                      </span>
                      <span className="text-[10px] font-mono text-slate-400 block mt-0.5">
                        {new Date(item.timestamp).toLocaleString("tr-TR")}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col space-y-1.5 flex-shrink-0">
                    <Link
                      href={`/analysis/${item.id}`}
                      className="inline-flex items-center space-x-1 px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-xl font-bold text-xs transition-colors shadow-sm"
                    >
                      <span>Raporu Aç</span>
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </Link>
                    <div className="flex items-center space-x-1.5">
                      <Link
                        href="/reviews/motifs"
                        className="inline-flex items-center space-x-1 px-2.5 py-1 bg-slate-800 hover:bg-purple-950 hover:text-purple-300 text-slate-400 rounded-xl font-medium text-[11px] transition-colors"
                      >
                        <ShieldCheck className="w-3 h-3 text-purple-400" />
                        <span>Motif</span>
                      </Link>
                      <button
                        onClick={() => handleDeleteRecent(item.id)}
                        disabled={deletingId === item.id}
                        title="Analiz kaydını ve veritabanı verilerini sil"
                        className="inline-flex items-center space-x-1 px-2.5 py-1 bg-slate-900 hover:bg-rose-950/80 hover:text-rose-300 text-slate-400 rounded-xl font-medium text-[11px] transition-colors border border-slate-800 hover:border-rose-800/60"
                      >
                        <Trash2 className="w-3 h-3 text-rose-400" />
                        <span>{deletingId === item.id ? "..." : "Kaldır"}</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>

      <Footer />
    </div>
  );
}
