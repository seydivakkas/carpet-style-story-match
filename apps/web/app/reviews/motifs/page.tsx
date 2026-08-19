"use client";

import { useState, useEffect, useCallback } from "react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import MotifReviewPanel from "@/components/reviews/MotifReviewPanel";
import {
  fetchMotifReviewQueue,
  fetchMotifReviewDetail,
  fetchMotifReviewHistory,
  MotifReviewQueueItem,
  MotifReviewDetail,
  MotifReviewEvent,
  ReviewApiError
} from "@/lib/api/motif_review";
import {
  ShieldAlert,
  Sparkles,
  CheckCircle2,
  HelpCircle,
  XCircle,
  Layers,
  RefreshCw,
  Info,
  ShieldCheck,
  Search
} from "lucide-react";

export default function CuratorMotifReviewPage() {
  const [activeTab, setActiveTab] = useState<string>("PENDING");
  const [queueItems, setQueueItems] = useState<MotifReviewQueueItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<MotifReviewDetail | null>(null);
  const [selectedHistory, setSelectedHistory] = useState<MotifReviewEvent[]>([]);

  const [loadingQueue, setLoadingQueue] = useState<boolean>(true);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
  const [accessDisabledError, setAccessDisabledError] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);

  const loadQueue = useCallback(async (tab: string) => {
    setLoadingQueue(true);
    setAccessDisabledError(null);
    setGeneralError(null);
    try {
      const res = await fetchMotifReviewQueue(tab);
      setQueueItems(res.items);
      setTotalCount(res.total_count);

      // Auto-select first item if available and none selected or current selected is not in items
      if (res.items.length > 0) {
        if (!selectedSubjectId || !res.items.find((i) => i.review_subject_id === selectedSubjectId)) {
          setSelectedSubjectId(res.items[0].review_subject_id);
        }
      } else {
        setSelectedSubjectId(null);
        setSelectedDetail(null);
        setSelectedHistory([]);
      }
    } catch (err: unknown) {
      if (err instanceof ReviewApiError && err.code === "REVIEW_ACCESS_DISABLED") {
        setAccessDisabledError("İnsan motif inceleme erişimi bu ortamda kapalıdır (MOTIF_REVIEW_ACCESS_MODE=DISABLED). İnceleme yapmak için sunucu yapılandırmasını güncelleyin.");
      } else if (err instanceof Error) {
        setGeneralError(err.message);
      } else {
        setGeneralError("Kuyruk yüklenirken bir hata oluştu.");
      }
    } finally {
      setLoadingQueue(false);
    }
  }, [selectedSubjectId]);

  const loadSubjectDetail = useCallback(async (subjectId: string) => {
    setLoadingDetail(true);
    try {
      const [det, hist] = await Promise.all([
        fetchMotifReviewDetail(subjectId),
        fetchMotifReviewHistory(subjectId)
      ]);
      setSelectedDetail(det);
      setSelectedHistory(hist);
    } catch (err: unknown) {
      console.error("Failed to load subject detail:", err);
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    loadQueue(activeTab);
  }, [activeTab, loadQueue]);

  useEffect(() => {
    if (selectedSubjectId) {
      loadSubjectDetail(selectedSubjectId);
    }
  }, [selectedSubjectId, loadSubjectDetail]);

  const getStatusBadge = (statusStr: string) => {
    switch (statusStr) {
      case "AUTO_CONFIRMED":
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded-md text-[11px] font-medium">
            <CheckCircle2 className="w-3 h-3" />
            <span>Otomatik Doğrulandı</span>
          </span>
        );
      case "CURATOR_CONFIRMED":
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-md text-[11px] font-medium">
            <CheckCircle2 className="w-3 h-3" />
            <span>Küratör Onaylı</span>
          </span>
        );
      case "UNCERTAIN":
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-md text-[11px] font-medium">
            <HelpCircle className="w-3 h-3" />
            <span>Belirsiz</span>
          </span>
        );
      case "REJECTED":
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-red-500/20 text-red-300 border border-red-500/30 rounded-md text-[11px] font-medium">
            <XCircle className="w-3 h-3" />
            <span>Reddedildi</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-md text-[11px] font-medium">
            <Sparkles className="w-3 h-3" />
            <span>İnceleme Bekliyor</span>
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header />

      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-8 flex-1 space-y-6">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center space-x-2 mb-2">
              <div className="inline-flex items-center space-x-2 px-3 py-1 bg-purple-500/10 border border-purple-500/30 rounded-full text-xs font-mono text-purple-300">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>İnsan Motif İnceleme Arayüzü (V2-06B)</span>
              </div>
              <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-amber-500/10 border border-amber-500/30 rounded-full text-[11px] font-mono text-amber-300">
                <span>Geliştirme inceleme modu</span>
              </div>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              Motif Adayları Doğrulama &amp; Kürasyon Kuyruğu
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              VLM tarafından tespit edilen veya haritalanmamış aday motifleri insan gözüyle inceleyin, doğrulayın veya reddedin.
            </p>
          </div>

          <button
            onClick={() => loadQueue(activeTab)}
            className="inline-flex items-center space-x-2 px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 rounded-xl text-xs font-semibold transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loadingQueue ? "animate-spin" : ""}`} />
            <span>Kuyruğu Yenile</span>
          </button>
        </div>

        {/* Disclaimer Banner */}
        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-2xl flex items-start space-x-3 text-amber-200 text-xs leading-relaxed">
          <Info className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold text-amber-300 block mb-0.5">Sorumluluk ve İnceleme Kapsamı Bildirimi:</span>
            <span>
              Bu işlem motifin görsel eşleşmesini doğrular; kültürel anlam, köken, dönem veya özgünlük doğrulaması yapmaz.
            </span>
          </div>
        </div>

        {/* Access Disabled Notice */}
        {accessDisabledError && (
          <div className="p-6 bg-red-500/10 border border-red-500/30 rounded-2xl text-center space-y-3">
            <ShieldAlert className="w-10 h-10 text-red-400 mx-auto" />
            <h3 className="text-lg font-bold text-white">İnceleme Erişimi Devre Dışı</h3>
            <p className="text-xs text-red-300 max-w-xl mx-auto leading-relaxed">
              {accessDisabledError}
            </p>
          </div>
        )}

        {/* General Error Notice */}
        {generalError && !accessDisabledError && (
          <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-300">
            Hata: {generalError}
          </div>
        )}

        {/* Main Interface when Access Available */}
        {!accessDisabledError && (
          <div className="space-y-6">
            {/* Filter Tabs */}
            <div className="flex items-center space-x-2 border-b border-slate-800/80 overflow-x-auto pb-2 text-xs font-medium">
              {[
                { id: "PENDING", label: "Bekleyenler" },
                { id: "CONFIRMED", label: "Doğrulananlar" },
                { id: "UNCERTAIN", label: "Belirsizler" },
                { id: "REJECTED", label: "Reddedilenler" },
                { id: "ALL", label: "Tümü" }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-2 rounded-xl transition-all whitespace-nowrap ${
                    activeTab === tab.id
                      ? "bg-purple-600 text-white font-bold shadow-lg shadow-purple-600/20"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
                  }`}
                >
                  {tab.label}
                </button>
              ))}

              <div className="ml-auto text-xs font-mono text-slate-500 px-3">
                Toplam: {totalCount} aday
              </div>
            </div>

            {/* Split Queue & Inspection Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Candidate List (4 cols) */}
              <div className="lg:col-span-4 space-y-3 max-h-[75vh] overflow-y-auto pr-1">
                {loadingQueue ? (
                  <div className="text-center py-12 text-slate-500 text-xs flex flex-col items-center space-y-2">
                    <RefreshCw className="w-6 h-6 animate-spin text-purple-400" />
                    <span>Kuyruk yükleniyor...</span>
                  </div>
                ) : queueItems.length === 0 ? (
                  <div className="text-center py-12 bg-slate-900/40 border border-slate-800/80 rounded-2xl p-6 text-slate-500 text-xs space-y-2">
                    <Layers className="w-8 h-8 mx-auto text-slate-600" />
                    <p>Bu filtre için aday bulunamadı.</p>
                  </div>
                ) : (
                  queueItems.map((item) => {
                    const isSelected = item.review_subject_id === selectedSubjectId;
                    return (
                      <div
                        key={item.review_subject_id}
                        onClick={() => setSelectedSubjectId(item.review_subject_id)}
                        className={`p-4 rounded-2xl border transition-all cursor-pointer space-y-2 ${
                          isSelected
                            ? "bg-slate-900 border-purple-500/80 shadow-lg shadow-purple-500/10"
                            : "bg-slate-900/50 border-slate-800/80 hover:border-slate-700"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs text-white">
                            {item.visual_candidate_key}
                          </span>
                          {getStatusBadge(item.effective_status)}
                        </div>

                        <div className="text-[11px] text-slate-400 space-y-1 font-mono">
                          <div>
                            Öneri:{" "}
                            <span className="text-amber-400 font-bold">
                              {item.proposed_canonical_motif_key || "Yok"}
                            </span>
                          </div>
                          <div className="flex justify-between items-center text-[10px] text-slate-500 pt-1 border-t border-slate-800/60">
                            <span>Güven: %{(item.candidate_confidence * 100).toFixed(0)}</span>
                            <span>v{item.review_version}</span>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Right Column: Detailed Candidate View (8 cols) */}
              <div className="lg:col-span-8">
                {loadingDetail ? (
                  <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-12 text-center text-slate-500 text-xs flex flex-col items-center space-y-2">
                    <RefreshCw className="w-8 h-8 animate-spin text-purple-400" />
                    <span>Aday detayları yükleniyor...</span>
                  </div>
                ) : selectedDetail ? (
                  <MotifReviewPanel
                    detail={selectedDetail}
                    history={selectedHistory}
                    onRefresh={() => {
                      if (selectedSubjectId) loadSubjectDetail(selectedSubjectId);
                      loadQueue(activeTab);
                    }}
                  />
                ) : (
                  <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-12 text-center text-slate-500 text-xs space-y-2">
                    <Search className="w-10 h-10 mx-auto text-slate-600" />
                    <p>İncelemek için sol listeden bir aday motif seçin.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
