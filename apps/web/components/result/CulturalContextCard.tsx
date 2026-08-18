"use client";

import { useState } from "react";
import { CulturalContextCardData, CulturalClaimItem } from "@/lib/result-experience-api";
import { BookOpen, ShieldCheck, Clock, ExternalLink, ChevronDown, ChevronUp, AlertCircle, FileText } from "lucide-react";

interface Props {
  data: CulturalContextCardData;
}

export default function CulturalContextCard({ data }: Props) {
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});

  const toggleSource = (claimId: string) => {
    setExpandedSources((prev) => ({ ...prev, [claimId]: !prev[claimId] }));
  };

  const getClaimStatusBadge = (status: string) => {
    switch (status) {
      case "DOCUMENTED":
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold rounded-lg">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Belgelenmiş İddia</span>
          </span>
        );
      case "CONTEXTUAL":
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-semibold rounded-lg">
            <BookOpen className="w-3.5 h-3.5" />
            <span>Bağlama Bağlı</span>
          </span>
        );
      case "CONTESTED":
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold rounded-lg">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Tartışmalı İddia</span>
          </span>
        );
      case "UNKNOWN":
      default:
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-slate-800 border border-slate-700 text-slate-400 text-xs font-semibold rounded-lg">
            <span>Bilinmiyor</span>
          </span>
        );
    }
  };

  return (
    <div id="card-3-cultural-context" className="bg-slate-900/70 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-2xl">
            <BookOpen className="w-6 h-6 text-emerald-400" />
          </div>
          <div>
            <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 bg-emerald-500/10 border border-emerald-500/30 rounded-full text-[11px] font-mono text-emerald-300 mb-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Kaynaklandırılmış Doğrulanmış İddialar</span>
            </div>
            <h2 className="text-2xl font-extrabold text-white tracking-tight">3. Kültürel Bağlam</h2>
          </div>
        </div>
      </div>

      {/* Gated States Handling */}
      {data.state === "WAITING_FOR_REVIEW" && (
        <div className="bg-purple-500/10 border border-purple-500/30 rounded-2xl p-5 flex items-start space-x-4 text-xs text-purple-200">
          <Clock className="w-6 h-6 text-purple-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h3 className="font-bold text-sm text-purple-300">İnsan İncelemesi Bekleniyor</h3>
            <p className="leading-relaxed">
              {data.user_message || "Kültürel bağlam sunulmadan önce motif eşleşmesinin insan incelemesinden geçmesi gerekiyor."}
            </p>
          </div>
        </div>
      )}

      {data.state === "WAITING_FOR_RESEARCH" && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-5 flex items-start space-x-4 text-xs text-amber-200">
          <AlertCircle className="w-6 h-6 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h3 className="font-bold text-sm text-amber-300">Kaynak Araştırması Bekleniyor</h3>
            <p className="leading-relaxed">
              {data.user_message || "Motif doğrulandı; kaynaklandırılmış kültürel araştırma henüz mevcut değil."}
            </p>
          </div>
        </div>
      )}

      {/* Ready Claims Display */}
      {data.state === "READY" && data.claims && data.claims.length > 0 && (
        <div className="space-y-4">
          {data.claims.map((claim: CulturalClaimItem) => {
            const isExpanded = expandedSources[claim.claim_id] ?? false;

            return (
              <div
                key={claim.claim_id}
                className="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 space-y-4 hover:border-slate-700 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-900 pb-3">
                  <span className="text-xs font-mono text-slate-400">
                    İddia ID: <span className="text-slate-200">{claim.claim_id}</span>
                  </span>
                  {getClaimStatusBadge(claim.status)}
                </div>

                <p className="text-sm font-semibold text-white leading-relaxed">
                  {claim.statement_tr}
                </p>

                {claim.scope && (
                  <p className="text-xs text-slate-400 font-mono">
                    Kültürel Kapsam: <span className="text-emerald-300">{claim.scope}</span>
                  </p>
                )}

                {/* Institutional Sources Accordion */}
                {claim.sources && claim.sources.length > 0 && (
                  <div className="pt-2">
                    <button
                      onClick={() => toggleSource(claim.claim_id)}
                      className="inline-flex items-center space-x-2 text-xs font-mono text-emerald-400 hover:text-emerald-300 transition-colors"
                    >
                      <FileText className="w-4 h-4" />
                      <span>Akademik / Müze Kaynakları ({claim.sources.length})</span>
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>

                    {isExpanded && (
                      <div className="mt-3 space-y-2 border-t border-slate-900 pt-3">
                        {claim.sources.map((src, idx) => (
                          <div
                            key={idx}
                            className="bg-slate-900/60 border border-slate-800 rounded-xl p-3 text-xs space-y-1.5"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-emerald-300">{src.institution}</span>
                              <span className="font-mono text-slate-400 text-[11px]">{src.locator}</span>
                            </div>
                            <p className="text-slate-200 font-medium">{src.title}</p>
                            {src.excerpt && (
                              <p className="text-slate-400 text-[11px] italic bg-slate-950/80 p-2 rounded border border-slate-800">
                                &quot;{src.excerpt}&quot;
                              </p>
                            )}
                            {src.canonical_url && (
                              <a
                                href={src.canonical_url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center space-x-1 text-[11px] font-mono text-emerald-400 hover:underline pt-1"
                              >
                                <span>Kaynak Kaydına Git</span>
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
