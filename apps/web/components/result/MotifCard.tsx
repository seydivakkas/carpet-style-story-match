"use client";

import { MotifCardData } from "@/lib/result-experience-api";
import { Shapes, ShieldCheck, Clock, CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";

interface Props {
  data: MotifCardData;
}

export default function MotifCard({ data }: Props) {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "CURATOR_CONFIRMED":
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold rounded-lg">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Küratöryel Doğrulama</span>
          </span>
        );
      case "UNCERTAIN":
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold rounded-lg">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Belirsiz</span>
          </span>
        );
      case "REJECTED":
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-semibold rounded-lg">
            <XCircle className="w-3.5 h-3.5" />
            <span>Reddedildi</span>
          </span>
        );
      case "WAITING_FOR_REVIEW":
      case "AI_CANDIDATE":
      default:
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs font-semibold rounded-lg">
            <Clock className="w-3.5 h-3.5" />
            <span>İnsan İncelemesi Bekleniyor</span>
          </span>
        );
    }
  };

  return (
    <div id="card-2-motifs" className="bg-slate-900/70 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-purple-500/10 border border-purple-500/30 rounded-2xl">
            <Shapes className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 bg-purple-500/10 border border-purple-500/30 rounded-full text-[11px] font-mono text-purple-300 mb-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Görsel İnceleme &amp; İnsan İnceleme Kapısı</span>
            </div>
            <h2 className="text-2xl font-extrabold text-white tracking-tight">2. Motifler</h2>
          </div>
        </div>

        {/* Review Summary Counters */}
        {data.review_summary && (
          <div className="flex items-center space-x-2 text-xs font-mono bg-slate-950 px-3 py-2 rounded-xl border border-slate-800">
            <span className="text-slate-400">Toplam: {data.review_summary.total_candidates}</span>
            <span className="text-slate-600">•</span>
            <span className="text-emerald-400">Doğrulanan: {data.review_summary.confirmed_count}</span>
            <span className="text-slate-600">•</span>
            <span className="text-purple-300">Bekleyen: {data.review_summary.pending_count}</span>
          </div>
        )}
      </div>

      {/* State Notification if Waiting for Review */}
      {data.state === "WAITING_FOR_REVIEW" && (
        <div className="bg-purple-500/10 border border-purple-500/30 rounded-2xl p-4 flex items-start space-x-3 text-xs text-purple-200">
          <Clock className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold block text-sm text-purple-300 mb-1">İnsan İncelemesi Bekleniyor</span>
            <span>
              Yapay zeka görsel motif adaylarını tespit etti. Kültürel bağlam ve hikâye kilitlerinin açılması için uzman küratör incelemesi beklenmektedir.
            </span>
          </div>
        </div>
      )}

      {/* Candidates List */}
      {data.candidates && data.candidates.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.candidates.map((cand) => (
            <div
              key={cand.candidate_id}
              className="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 space-y-3 flex flex-col justify-between hover:border-slate-700 transition-colors"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white tracking-wide">
                    {cand.turkish_label}
                  </span>
                  {getStatusBadge(cand.status)}
                </div>

                <p className="text-xs font-mono text-slate-400">
                  Görsel Kod: <span className="text-slate-200">{cand.visual_descriptor}</span>
                </p>
              </div>

              <div className="space-y-2 pt-3 border-t border-slate-900">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 font-mono">AI Güveni:</span>
                  <span className="font-mono font-bold text-purple-300">
                    %{(cand.ai_confidence * 100).toFixed(1)}
                  </span>
                </div>

                {cand.bounding_box && (
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <span>Görsel Bölge (BBox):</span>
                    <span className="text-slate-300">
                      [{cand.bounding_box.map((b) => b.toFixed(2)).join(", ")}]
                    </span>
                  </div>
                )}

                {cand.confirmed_canonical_motif_key && (
                  <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-2 text-xs font-mono text-emerald-300">
                    Doğrulanan Kanonik Anahtar: {cand.confirmed_canonical_motif_key}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-slate-950/60 border border-slate-800 rounded-2xl p-6 text-center text-xs text-slate-400 flex flex-col items-center space-y-2">
          <Info className="w-6 h-6 text-slate-400" />
          <span>Görsel motif adayı tespit edilmedi veya motif aşaması çalıştırılmadı.</span>
        </div>
      )}
    </div>
  );
}
