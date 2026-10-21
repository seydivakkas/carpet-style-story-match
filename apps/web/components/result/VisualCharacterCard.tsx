"use client";

import { VisualCharacterCardData } from "@/lib/result-experience-api";
import { Palette, Sparkles, Layers, ArrowUpRight, HelpCircle } from "lucide-react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";

interface Props {
  data: VisualCharacterCardData;
  primaryImageUrl?: string;
}

const DIMENSION_CONFIG: Record<
  string,
  { label: string; minEndpoint: string; maxEndpoint: string }
> = {
  color_energy: {
    label: "Renk Enerjisi",
    minEndpoint: "Sakin",
    maxEndpoint: "Canlı",
  },
  color_diversity: {
    label: "Renk Çeşitliliği",
    minEndpoint: "Sınırlı Palet",
    maxEndpoint: "Zengin Palet",
  },
  contrast: {
    label: "Kontrast",
    minEndpoint: "Yumuşak",
    maxEndpoint: "Güçlü",
  },
  warmth: {
    label: "Sıcaklık",
    minEndpoint: "Soğuk",
    maxEndpoint: "Sıcak",
  },
  visual_complexity: {
    label: "Görsel Karmaşıklık",
    minEndpoint: "Sade",
    maxEndpoint: "Detaylı",
  },
  structural_order: {
    label: "Yapısal Düzen",
    minEndpoint: "Serbest",
    maxEndpoint: "Düzenli",
  },
  rhythm_repetition: {
    label: "Ritim / Tekrar",
    minEndpoint: "Tekil",
    maxEndpoint: "Ritmik/Tekrarlı",
  },
  focal_strength: {
    label: "Odak Gücü",
    minEndpoint: "Dağıtılmış",
    maxEndpoint: "Güçlü Odak",
  },
  form_language: {
    label: "Form Dili",
    minEndpoint: "Geometrik",
    maxEndpoint: "Organik",
  },
};

export default function VisualCharacterCard({ data, primaryImageUrl }: Props) {
  if (data.state === "BLOCKED_BY_QUALITY") {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6 space-y-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-amber-500/10 border border-amber-500/30 rounded-2xl">
            <Palette className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">1. Görsel Karakter</h2>
            <span className="text-xs text-amber-400 font-mono">Görüntü Kalitesi Yetersiz</span>
          </div>
        </div>
        <p className="text-sm text-slate-400">
          Görüntü kalitesi düşük olduğu için Style DNA 9D görsel analiz engellendi.
        </p>
      </div>
    );
  }

  // Radar chart data preparation
  const radarData = Object.entries(DIMENSION_CONFIG).map(([key, cfg]) => {
    const rawVal = data.dimensions[key] ?? 0.5;
    return {
      dimension: cfg.label,
      value: Math.round(rawVal * 100),
      fullMark: 100,
    };
  });

  const fullImageUrl = primaryImageUrl
    ? (primaryImageUrl.startsWith("http") || primaryImageUrl.startsWith("blob:") ? primaryImageUrl : `http://localhost:8000${primaryImageUrl}`)
    : null;

  return (
    <div id="card-1-visual-character" className="bg-slate-900/70 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-8 shadow-xl">
      {/* Header Badge & Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div className="flex items-center space-x-4">
          {fullImageUrl && (
            <div className="relative w-20 h-28 rounded-2xl overflow-hidden border-2 border-amber-500/40 shadow-lg flex-shrink-0 bg-slate-950">
              <img
                src={fullImageUrl}
                alt="Yüklenen Halı Görseli"
                className="w-full h-full object-cover"
              />
            </div>
          )}
          <div className="space-y-1">
            <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 bg-amber-500/10 border border-amber-500/30 rounded-full text-[11px] font-mono text-amber-300">
              <Sparkles className="w-3 h-3" />
              <span>Görsel İnceleme Sonucu</span>
            </div>
            <h2 className="text-2xl font-extrabold text-white tracking-tight">1. Görsel Karakter</h2>
          </div>
        </div>

        <div className="text-xs font-mono text-slate-400 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800 self-start sm:self-auto">
          Stil Sürümü: <span className="text-amber-300 font-semibold">{data.style_dna_version}</span>
        </div>
      </div>

      {/* Style DNA 9D Radar Chart & Accessible Table Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
        {/* Radar Chart */}
        <div className="bg-slate-950/80 border border-slate-800/80 rounded-2xl p-4 sm:p-6 h-[340px] flex flex-col justify-between">
          <div className="text-xs font-mono text-slate-400 flex items-center justify-between">
            <span className="text-amber-400 font-bold">9 Boyutlu Style DNA Radarı</span>
            <span>0 – 100 Ölçeği</span>
          </div>

          <div className="w-full h-[270px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="dimension" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="#475569" />
                <Radar name="Style DNA" dataKey="value" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.35} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Accessible Style DNA Table */}
        <div className="space-y-3">
          <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider font-mono">
            Style DNA Ölçüm Tablosu
          </h3>
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl overflow-hidden text-xs">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-900 border-b border-slate-800 text-slate-400 font-mono">
                  <th className="py-2.5 px-3">Görsel Boyut</th>
                  <th className="py-2.5 px-3 text-right">Değer</th>
                  <th className="py-2.5 px-3">Semantik Eksen</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {Object.entries(DIMENSION_CONFIG).map(([key, cfg]) => {
                  const val = data.dimensions[key] ?? 0.5;
                  const pct = Math.round(val * 100);
                  return (
                    <tr key={key} className="hover:bg-slate-900/40">
                      <td className="py-2 px-3 font-semibold text-white">{cfg.label}</td>
                      <td className="py-2 px-3 text-right font-mono text-amber-300 font-bold">{pct} / 100</td>
                      <td className="py-2 px-3 text-[11px] text-slate-400">
                        {cfg.minEndpoint} ↔ {cfg.maxEndpoint}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Color Observation Palette */}
      {data.palette && data.palette.length > 0 && (
        <div className="space-y-4 pt-4 border-t border-slate-800">
          <h3 className="text-base font-bold text-white flex items-center space-x-2">
            <span>Gözlemlenen Renk Paleti</span>
            <span className="text-xs font-mono text-slate-400 font-normal">(Yalnızca Görsel Baskınlık)</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {data.palette.map((col, idx) => (
              <div key={idx} className="bg-slate-950/70 border border-slate-800/80 rounded-2xl p-3.5 flex items-center space-x-3">
                <div
                  className="w-10 h-10 rounded-xl border border-slate-700/80 flex-shrink-0 shadow-inner"
                  style={{ backgroundColor: col.hex_code || "#64748b" }}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-100">
                    <span className="truncate">{col.turkish_description}</span>
                    <span className="font-mono text-amber-400 ml-1">{col.coverage_percentage}%</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-1.5 mt-1.5 overflow-hidden">
                    <div
                      className="bg-amber-400 h-1.5 rounded-full"
                      style={{ width: `${Math.min(100, col.coverage_percentage)}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Catalog Visual Matches Subsection */}
      {data.catalog_matches && data.catalog_matches.length > 0 && (
        <div className="space-y-4 pt-6 border-t border-slate-800">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                <Layers className="w-5 h-5 text-amber-400" />
                <span>Görsel Olarak Benzer Güncel Halılar</span>
              </h3>
              <p className="text-xs text-slate-400">
                Stil kataloğumuzdaki 9 boyutlu estetik yakınlığı en yüksek ürünler
              </p>
            </div>

            <div className="inline-flex items-center space-x-1.5 px-3 py-1 bg-slate-950 border border-slate-800 rounded-xl text-[11px] text-slate-400 font-mono">
              <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
              <span>Görsel Yakınlık Score = 9D Vektör Mesafesi</span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.catalog_matches.map((item) => (
              <div key={item.catalog_id} className="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 space-y-3 flex flex-col justify-between hover:border-slate-700 transition-colors">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                      SKU: {item.sku}
                    </span>
                    <span className="text-xs font-mono font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
                      YAKINLIK: %{item.visual_proximity_score.toFixed(1)}
                    </span>
                  </div>

                  <h4 className="text-sm font-bold text-white truncate">{item.product_name}</h4>
                  <p className="text-xs text-slate-400">
                    {item.brand || "Merinos"} {item.collection ? `• ${item.collection}` : ""}
                  </p>
                </div>

                {item.closest_dimensions && item.closest_dimensions.length > 0 && (
                  <div className="space-y-1 pt-2 border-t border-slate-900">
                    <span className="text-[10px] font-mono text-slate-400">Benzer Özellikler:</span>
                    <div className="flex flex-wrap gap-1">
                      {item.closest_dimensions.map((dim) => (
                        <span key={dim} className="text-[10px] bg-slate-900 text-slate-300 px-2 py-0.5 rounded font-mono border border-slate-800">
                          {DIMENSION_CONFIG[dim]?.label || dim}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <a
                  href={`/catalog/${item.catalog_id}`}
                  className="inline-flex items-center justify-center space-x-1.5 w-full py-2 bg-slate-900 hover:bg-slate-800 text-slate-200 font-semibold text-xs rounded-xl border border-slate-800 transition-colors pt-2"
                >
                  <span>Ürünü Görüntüle</span>
                  <ArrowUpRight className="w-3.5 h-3.5 text-amber-400" />
                </a>
              </div>
            ))}
          </div>

          <p className="text-[11px] text-slate-400 italic bg-slate-950/60 p-3 rounded-xl border border-slate-800/60">
            * Bu değer yalnız 9 boyutlu görsel karakter yakınlığını gösterir; ürün önerisi, beğeni tahmini veya kalite puanı değildir.
          </p>
        </div>
      )}
    </div>
  );
}
