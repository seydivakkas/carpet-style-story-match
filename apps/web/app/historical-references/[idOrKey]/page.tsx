"use client";

import { use } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import StatusBadge from "@/components/StatusBadge";
import DisclaimerBanner from "@/components/DisclaimerBanner";
import { useHistoricalReference } from "@/lib/api/historical";
import { ExternalLink, ArrowLeft, Building2, Calendar, MapPin, FileText } from "lucide-react";

export default function HistoricalReferenceDetailPage({ params }: { params: Promise<{ idOrKey: string }> }) {
  const { idOrKey } = use(params);

  const { data: refItem, isLoading, error } = useHistoricalReference(idOrKey);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header />
        <LoadingState message="Tarihsel referans detayları yükleniyor..." />
        <Footer />
      </div>
    );
  }

  if (error || !refItem) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between">
        <Header />
        <main className="max-w-4xl mx-auto w-full p-6">
          <ErrorState error={error} title="Tarihsel Referans Bulunmadı" />
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header />

      <main className="max-w-4xl mx-auto w-full px-6 py-8 flex-1 space-y-6">
        <Link
          href="/historical-references"
          className="inline-flex items-center space-x-2 text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Tüm Tarihsel Referanslara Dön</span>
        </Link>

        <DisclaimerBanner />

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 space-y-6 shadow-xl">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
            <div>
              <span className="font-mono text-xs text-blue-400 font-bold px-2.5 py-1 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                {refItem.reference_key}
              </span>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mt-2">
                {refItem.object_title}
              </h1>
            </div>

            <StatusBadge readiness={refItem.style_dna_readiness} />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs text-slate-300 bg-slate-950/60 border border-slate-800/60 rounded-xl p-5">
            <div className="space-y-1">
              <span className="text-slate-500 text-[10px] block font-mono">MÜZE / KURUM</span>
              <div className="flex items-center space-x-2 font-semibold">
                <Building2 className="w-4 h-4 text-blue-400" />
                <span>{refItem.institution_name}</span>
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-slate-500 text-[10px] block font-mono">ENVANTER NUMARASI</span>
              <div className="flex items-center space-x-2 font-semibold font-mono">
                <FileText className="w-4 h-4 text-blue-400" />
                <span>{refItem.accession_number || refItem.object_identifier || "Belirtilmemiş"}</span>
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-slate-500 text-[10px] block font-mono">TARİHLENDİRME</span>
              <div className="flex items-center space-x-2 font-semibold">
                <Calendar className="w-4 h-4 text-blue-400" />
                <span>{refItem.date_display || "Tarih Belirtilmemiş"}</span>
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-slate-500 text-[10px] block font-mono">KÖKEN BÖLGESİ / KÜLTÜR</span>
              <div className="flex items-center space-x-2 font-semibold">
                <MapPin className="w-4 h-4 text-blue-400" />
                <span>{refItem.culture || refItem.geography || refItem.dynasty_or_tradition || "Belirtilmemiş"}</span>
              </div>
            </div>
          </div>

          {refItem.curation_note && (
            <div className="space-y-2 pt-2">
              <h3 className="text-xs font-mono text-slate-400 font-bold uppercase">Akademik / Arşiv Notları</h3>
              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed bg-slate-950/40 p-4 rounded-xl border border-slate-800/60">
                {refItem.curation_note}
              </p>
            </div>
          )}

          {refItem.object_url && (
            <div className="pt-4 border-t border-slate-800/60 flex justify-end">
              <a
                href={refItem.object_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-medium transition-colors"
              >
                <span>Müze Resmi Kaydını İncele</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
