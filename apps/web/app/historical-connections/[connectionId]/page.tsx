"use client";

import { use } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import StatusBadge from "@/components/StatusBadge";
import DisclaimerBanner from "@/components/DisclaimerBanner";
import { useHistoricalConnection } from "@/lib/api/historical";
import { DIMENSION_DETAILS } from "@/lib/constants";
import { Compass, ArrowLeft, Layers } from "lucide-react";

export default function HistoricalConnectionDetailPage({ params }: { params: Promise<{ connectionId: string }> }) {
  const { connectionId } = use(params);

  const { data: conn, isLoading, error } = useHistoricalConnection(connectionId);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header />
        <LoadingState message="Tarihsel bağlantı analizi yükleniyor..." />
        <Footer />
      </div>
    );
  }

  if (error || !conn) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header />
        <main className="max-w-4xl mx-auto w-full p-6">
          <ErrorState error={error} title="Tarihsel Bağlantı Bulunamadı" />
        </main>
        <Footer />
      </div>
    );
  }

  const score100 = conn.style_similarity != null ? conn.style_similarity * 100 : 0;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header />

      <main className="max-w-4xl mx-auto w-full px-6 py-8 flex-1 space-y-6">
        <Link
          href="/historical-references"
          className="inline-flex items-center space-x-2 text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Tarihsel Referanslara Dön</span>
        </Link>

        {/* Mandatory Non-Attribution Disclaimer */}
        <DisclaimerBanner disclaimerText={conn.explanation?.disclaimer} />

        {/* Main Connection Overview Card */}
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 space-y-6 shadow-xl">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
            <div>
              <div className="flex items-center space-x-2 text-xs font-mono text-blue-400">
                <Compass className="w-3.5 h-3.5" />
                <span>Pairwise Historical Style DNA Connection</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mt-1">
                Tarihsel Referans Bağlantı Analizi
              </h1>
            </div>

            <StatusBadge status={conn.connection_level} />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-slate-950/60 border border-slate-800/60 rounded-xl p-5 text-center">
            <div className="space-y-1">
              <span className="text-[10px] font-mono text-slate-500 uppercase">Style Connection Skoru</span>
              <div className="text-3xl font-mono font-bold text-blue-400">
                {score100.toFixed(0)} <span className="text-sm font-normal text-slate-500">/ 100</span>
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-[10px] font-mono text-slate-500 uppercase">Bağlantı Derecesi</span>
              <div className="text-sm font-semibold text-slate-200 mt-2">
                {conn.explanation?.connection_level_label_tr || conn.connection_level}
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-[10px] font-mono text-slate-500 uppercase">Vektör Kapsamı</span>
              <div className="text-sm font-mono font-bold text-slate-200 mt-2">
                %{(conn.dimension_coverage * 100).toFixed(0)}
              </div>
            </div>
          </div>

          {/* 9D Pairwise Dimension Table */}
          <div className="space-y-3 pt-4">
            <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2">
              <Layers className="w-4 h-4 text-blue-400" />
              <span>9 Boyutlu Style DNA Karşılaştırma Tablosu</span>
            </h3>

            <div className="overflow-x-auto border border-slate-800/80 rounded-xl bg-slate-950/60">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 font-mono">
                  <tr>
                    <th className="p-3">BOYUT</th>
                    <th className="p-3 text-right">HEDEF HALI</th>
                    <th className="p-3 text-right">MÜZE REFERANSI</th>
                    <th className="p-3 text-right">UZAKLIK (DISTANCE)</th>
                    <th className="p-3 text-right">BENZERLİK</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50 text-slate-300">
                  {conn.dimensions.map((d) => {
                    const meta = DIMENSION_DETAILS[d.dimension_key] || { label_tr: d.dimension_key, code: d.dimension_key };
                    return (
                      <tr key={d.dimension_key} className="hover:bg-slate-900/40 transition-colors">
                        <td className="p-3">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono text-[10px] font-bold text-blue-400 px-1.5 py-0.5 bg-blue-500/10 border border-blue-500/20 rounded">
                              {meta.code}
                            </span>
                            <span className="font-semibold text-slate-200">{meta.label_tr}</span>
                          </div>
                        </td>
                        <td className="p-3 text-right font-mono text-slate-300">
                          {d.target_value != null ? d.target_value.toFixed(2) : "-"}
                        </td>
                        <td className="p-3 text-right font-mono text-slate-300">
                          {d.reference_value != null ? d.reference_value.toFixed(2) : "-"}
                        </td>
                        <td className="p-3 text-right font-mono font-bold text-blue-400">
                          {d.difference != null ? d.difference.toFixed(2) : "-"}
                        </td>
                        <td className="p-3 text-right font-mono text-slate-400">
                          {d.similarity != null ? d.similarity.toFixed(2) : "-"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
