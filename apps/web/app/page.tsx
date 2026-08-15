"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchHealth, fetchStyleDNAMeta, fetchNarrativeThemesMeta } from "@/lib/api";
import { Activity, ShieldCheck, Layers, BookOpen, AlertCircle } from "lucide-react";

export default function Home() {
  const { data: healthData, isLoading: healthLoading, isError: healthError } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 10000,
  });

  const { data: styleDnaMeta } = useQuery({
    queryKey: ["styleDnaMeta"],
    queryFn: fetchStyleDNAMeta,
  });

  const { data: narrativeMeta } = useQuery({
    queryKey: ["narrativeMeta"],
    queryFn: fetchNarrativeThemesMeta,
  });

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between p-6 sm:p-12 font-sans">
      {/* Header section */}
      <header className="max-w-4xl mx-auto w-full flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-slate-800/80 pb-6 gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-amber-500 animate-pulse" />
            <span className="text-xs font-mono tracking-widest text-amber-500 uppercase">System Active</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white mt-1">
            Carpet Style & Story Match
          </h1>
        </div>

        {/* Backend health pill */}
        <div className="flex items-center space-x-3 bg-slate-900/90 border border-slate-800 px-4 py-2 rounded-full shadow-inner">
          <Activity className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-medium text-slate-300">API Status:</span>
          {healthLoading ? (
            <span className="text-xs font-mono text-amber-400 animate-pulse">Connecting...</span>
          ) : healthError ? (
            <span className="inline-flex items-center text-xs font-mono text-rose-400">
              <AlertCircle className="w-3 h-3 mr-1" /> Offline
            </span>
          ) : (
            <span className="inline-flex items-center text-xs font-mono text-emerald-400">
              <ShieldCheck className="w-3.5 h-3.5 mr-1" /> {healthData?.status.toUpperCase()}
            </span>
          )}
        </div>
      </header>

      {/* Hero section */}
      <section className="max-w-4xl mx-auto w-full my-12 space-y-6">
        <div className="bg-gradient-to-r from-slate-900 via-slate-900/80 to-slate-950 border border-slate-800 rounded-2xl p-8 sm:p-12 shadow-2xl relative overflow-hidden">
          <div className="absolute -right-16 -top-16 w-64 h-64 bg-amber-500/5 rounded-full blur-3xl pointer-events-none" />
          <h2 className="text-2xl sm:text-3xl font-light text-slate-200 leading-snug">
            Halıların görsel karakterini, estetik tercihlerini ve belgelenmiş hikâyelerini bir araya getir.
          </h2>
          <p className="text-slate-400 text-sm sm:text-base max-w-2xl mt-4 leading-relaxed">
            Bu platform, halıların görsel form dilini (9D Style DNA), tematik kültürel anlatılarını (8 Narrative Themes) ve doğrulanmış müze/arşiv referanslarını birbirine karıştırmadan, ayrı ve ölçülebilir boyutlarda değerlendirir.
          </p>
        </div>

        {/* Canonical Contracts Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
          {/* Style DNA Card */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 hover:border-slate-700/80 transition-colors">
            <div className="flex items-center space-x-3 mb-4">
              <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Frozen 9D Style DNA</h3>
                <p className="text-xs text-slate-400">Ölçülebilir Görsel Karakter Boyutları</p>
              </div>
            </div>
            <div className="space-y-2 mt-4">
              {styleDnaMeta?.dimensions.map((dim) => (
                <div key={dim.code} className="flex items-center justify-between text-xs bg-slate-950/60 px-3 py-2 rounded border border-slate-800/40">
                  <span className="font-mono text-amber-400 font-bold">{dim.code}</span>
                  <span className="font-medium text-slate-200">{dim.label_tr}</span>
                  <span className="text-slate-500 text-[10px]">{dim.min_label} ↔ {dim.max_label}</span>
                </div>
              )) || (
                <div className="text-xs text-slate-500 italic py-2">Canonical contract loaded via API...</div>
              )}
            </div>
          </div>

          {/* Narrative Themes Card */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 hover:border-slate-700/80 transition-colors">
            <div className="flex items-center space-x-3 mb-4">
              <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg">
                <BookOpen className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Frozen 8 Narrative Themes</h3>
                <p className="text-xs text-slate-400">Belgelenmiş Kültürel Temalar</p>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-2 mt-4">
              {narrativeMeta?.themes.map((theme) => (
                <div key={theme.code} className="flex items-center space-x-2 text-xs bg-slate-950/60 px-3 py-2 rounded border border-slate-800/40">
                  <span className="font-mono text-emerald-400 font-bold">{theme.code}</span>
                  <span className="text-base">{theme.icon}</span>
                  <span className="font-medium text-slate-200">{theme.label_tr}</span>
                </div>
              )) || (
                <div className="text-xs text-slate-500 italic py-2">Canonical contract loaded via API...</div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="max-w-4xl mx-auto w-full border-t border-slate-800/80 pt-6 text-center sm:text-left flex flex-col sm:flex-row justify-between items-center text-xs text-slate-500 gap-4">
        <div>
          © 2026 Seydi Eryılmaz (@seydivakkas). Tüm Hakları Saklıdır.
        </div>
        <div className="font-mono text-[11px] text-slate-600">
          Clean Monorepo Architecture • No Fake Production Data
        </div>
      </footer>
    </main>
  );
}
