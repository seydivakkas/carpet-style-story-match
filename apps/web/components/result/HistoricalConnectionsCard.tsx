"use client";

import { HistoricalConnectionsCardData } from "@/lib/result-experience-api";
import { Compass, AlertTriangle, ExternalLink, ShieldCheck, HelpCircle } from "lucide-react";

interface Props {
  data: HistoricalConnectionsCardData;
}

export default function HistoricalConnectionsCard({ data }: Props) {
  return (
    <div id="card-5-historical-connections" className="bg-slate-900/70 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-2xl">
            <Compass className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 bg-blue-500/10 border border-blue-500/30 rounded-full text-[11px] font-mono text-blue-300 mb-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Görsel Yakınlık + Müze Kaynak Metadata&apos;sı</span>
            </div>
            <h2 className="text-2xl font-extrabold text-white tracking-tight">5. Tarihsel Bağlantılar</h2>
          </div>
        </div>
      </div>

      {/* Mandatory Visible Disclaimer Box */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 flex items-start space-x-3 text-xs text-amber-200">
        <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-bold text-amber-300 uppercase tracking-wider font-mono text-[11px] block">
            Zorunlu Yasal &amp; Bilimsel Bildirim
          </span>
          <p className="font-semibold text-white">
            {data.disclaimer || "Görsel yakınlık tarihsel köken, dönem veya özgünlük doğrulaması değildir."}
          </p>
        </div>
      </div>

      {/* Historical Matches Grid */}
      {data.matches && data.matches.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.matches.map((item) => (
            <div
              key={item.historical_reference_id}
              className="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 space-y-4 flex flex-col justify-between hover:border-slate-700 transition-colors"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-blue-300 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/30 font-bold">
                    MÜZE KAYDI: #{item.rank}
                  </span>
                  <span className="text-xs font-mono font-bold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/30">
                    GÖRSEL YAKINLIK: %{item.visual_proximity_score.toFixed(1)}
                  </span>
                </div>

                <h3 className="text-base font-bold text-white line-clamp-2">{item.object_title}</h3>
                <p className="text-xs font-mono text-blue-300 font-semibold">{item.institution}</p>
              </div>

              {/* Museum Metadata Grid */}
              <div className="grid grid-cols-2 gap-2 text-xs font-mono bg-slate-900/60 p-3 rounded-xl border border-slate-800/80">
                <div>
                  <span className="text-slate-400 text-[10px] block">Dönem / Tarih</span>
                  <span className="text-slate-200 font-semibold">{item.date_or_period || "Bilinmiyor"}</span>
                </div>
                <div>
                  <span className="text-slate-400 text-[10px] block">Kültür</span>
                  <span className="text-slate-200 font-semibold">{item.origin_culture || "Anadolu / Türk"}</span>
                </div>
                {item.origin_geography && (
                  <div className="col-span-2">
                    <span className="text-slate-400 text-[10px] block">Coğrafya</span>
                    <span className="text-slate-200 font-semibold">{item.origin_geography}</span>
                  </div>
                )}
              </div>

              {/* Canonical Link */}
              {item.canonical_source_url && (
                <a
                  href={item.canonical_source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center justify-center space-x-2 w-full py-2 bg-slate-900 hover:bg-slate-800 text-slate-200 font-semibold text-xs rounded-xl border border-slate-800 transition-colors"
                >
                  <span>Müze Resmi Kaydını İncele</span>
                  <ExternalLink className="w-3.5 h-3.5 text-blue-400" />
                </a>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-slate-950/60 border border-slate-800 rounded-2xl p-6 text-center text-xs text-slate-400 flex flex-col items-center space-y-2">
          <HelpCircle className="w-6 h-6 text-slate-400" />
          <span>Tarihsel görsel referans eşleşmesi bulunamadı.</span>
        </div>
      )}
    </div>
  );
}
