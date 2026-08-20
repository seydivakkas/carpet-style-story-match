"use client";

import Link from "next/link";
import { MotifStoryCardData } from "@/lib/result-experience-api";
import { Sparkles, ShieldCheck, Clock, BookOpen, AlertTriangle, Compass, ArrowUpRight } from "lucide-react";

interface Props {
  data: MotifStoryCardData;
}

export default function MotifStoryCard({ data }: Props) {
  return (
    <div id="card-4-motif-story" className="bg-slate-900/70 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-2xl">
            <Sparkles className="w-6 h-6 text-amber-400" />
          </div>
          <div>
            <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 bg-amber-500/10 border border-amber-500/30 rounded-full text-[11px] font-mono text-amber-300 mb-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Kaynaklandırılmış Doğrulanmış Anlatı</span>
            </div>
            <h2 className="text-2xl font-extrabold text-white tracking-tight">4. Motif Hikâyeleri</h2>
          </div>
        </div>
      </div>

      {/* Gated States Handling */}
      {data.state === "WAITING_FOR_REVIEW" && (
        <div className="bg-purple-500/10 border border-purple-500/30 rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs text-purple-200">
          <div className="flex items-start space-x-4">
            <Clock className="w-6 h-6 text-purple-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h3 className="font-bold text-sm text-purple-300">İnsan İncelemesi Bekleniyor</h3>
              <p className="leading-relaxed text-slate-300">
                {data.user_message || "Kültürel anlatı sunulmadan önce motif eşleşmesinin insan incelemesinden geçmesi gerekiyor."}
              </p>
            </div>
          </div>
          <Link
            href="/reviews/motifs"
            className="inline-flex items-center space-x-1.5 px-4 py-2 bg-purple-500 hover:bg-purple-400 text-slate-950 font-bold rounded-xl text-xs transition-colors shrink-0 shadow-md"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Motif İnceleme Paneline Git</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {data.state === "WAITING_FOR_RESEARCH" && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-5 flex items-start space-x-4 text-xs text-amber-200">
          <AlertTriangle className="w-6 h-6 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h3 className="font-bold text-sm text-amber-300">Kaynak Araştırması Bekleniyor</h3>
            <p className="leading-relaxed">
              {data.user_message || "Motif doğrulandı; kaynaklandırılmış anlatı henüz mevcut değil."}
            </p>
          </div>
        </div>
      )}

      {/* Ready Story Display */}
      {data.state === "READY" && data.story && (
        <div className="space-y-6">
          <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-6 space-y-4">
            <h3 className="text-xl font-bold text-white tracking-tight">{data.story.title}</h3>
            <p className="text-sm text-slate-300 leading-relaxed font-serif italic border-l-2 border-amber-500 pl-4 py-1">
              {data.story.summary}
            </p>

            <div className="space-y-6 pt-4 border-t border-slate-900">
              {data.story.sections.map((sec, idx) => (
                <div key={idx} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-base font-bold text-amber-300">{sec.heading}</h4>
                    {sec.is_contested && (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-amber-500/10 border border-amber-500/30 text-amber-400 text-[10px] font-mono rounded">
                        <AlertTriangle className="w-3 h-3" />
                        <span>Tartışmalı Anlatı</span>
                      </span>
                    )}
                  </div>

                  <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-sans">
                    {sec.content}
                  </p>

                  {sec.citations && sec.citations.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 pt-1 font-mono text-[11px] text-slate-400">
                      <BookOpen className="w-3 h-3 text-amber-400" />
                      <span>Atıflar:</span>
                      {sec.citations.map((cite, cidx) => (
                        <span key={cidx} className="bg-slate-900 border border-slate-800 text-amber-300/90 px-2 py-0.5 rounded">
                          [{cite}]
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Optional Thematic Affinity Subsection */}
          {data.thematic_affinity && (
            <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-5 space-y-3">
              <div className="flex items-center space-x-2 text-xs font-mono text-emerald-400 font-bold uppercase tracking-wider">
                <Compass className="w-4 h-4 text-emerald-400" />
                <span>Tematik Yakınlık</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {data.thematic_affinity.affinity_description}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {data.thematic_affinity.matched_themes.map((theme) => (
                  <span key={theme} className="text-xs bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 px-2.5 py-1 rounded-lg font-mono">
                    {theme}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
