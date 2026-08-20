"use client";

import { useState } from "react";
import { UnifiedUploadResult } from "@/lib/result-experience-api";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import VisualCharacterCard from "./VisualCharacterCard";
import MotifCard from "./MotifCard";
import CulturalContextCard from "./CulturalContextCard";
import MotifStoryCard from "./MotifStoryCard";
import HistoricalConnectionsCard from "./HistoricalConnectionsCard";
import { Sparkles, Layers, Shapes, BookOpen, Compass, ShieldCheck, ChevronDown, ChevronUp, Code2, AlertTriangle } from "lucide-react";

interface Props {
  result: UnifiedUploadResult;
}

export default function UnifiedUploadResultPage({ result }: Props) {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header />

      <main className="max-w-6xl mx-auto w-full px-4 sm:px-6 py-8 flex-1 space-y-10">
        {/* Top Hero Banner */}
        <section className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-2xl">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="space-y-3 max-w-2xl">
              <div className="inline-flex items-center space-x-2 px-3 py-1 bg-amber-500/10 border border-amber-500/30 rounded-full text-xs font-mono text-amber-400">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Yüklenen Halı Değerlendirme Raporu v1</span>
              </div>
              <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
                5 Kartlı Analiz ve Eşleşme Sonuçları
              </h1>
              <p className="text-slate-400 text-sm leading-relaxed">
                Yüklediğiniz halı görseli; 9 boyutlu görsel karakter, tespit edilen motifler, kaynaklandırılmış kültürel bağlam, motif hikâyeleri ve müze koleksiyonlarındaki tarihsel referanslar ile 5 ayrı eksende sunulmaktadır.
              </p>
            </div>

            <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800 space-y-2 min-w-[240px] text-xs font-mono">
              <div className="flex items-center justify-between text-slate-400">
                <span>Analiz ID:</span>
                <span className="text-amber-300 font-bold">{result.analysis_id.slice(0, 8)}...</span>
              </div>
              <div className="flex items-center justify-between text-slate-400">
                <span>Sözleşme:</span>
                <span className="text-slate-200">{result.schema_version}</span>
              </div>
              <div className="flex items-center justify-between text-slate-400">
                <span>Görsel SHA256:</span>
                <span className="text-slate-200">{result.image_meta.original_sha256.slice(0, 8)}...</span>
              </div>
            </div>
          </div>

          {/* Quick Navigation Anchor Bar */}
          <div className="flex items-center space-x-2 overflow-x-auto pt-4 border-t border-slate-800 text-xs font-medium no-scrollbar">
            <a
              href="#card-1-visual-character"
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-xl text-amber-400 whitespace-nowrap transition-colors"
            >
              <PaletteIcon className="w-3.5 h-3.5" />
              <span>1. Görsel Karakter</span>
            </a>
            <a
              href="#card-2-motifs"
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-xl text-purple-300 whitespace-nowrap transition-colors"
            >
              <Shapes className="w-3.5 h-3.5" />
              <span>2. Motifler</span>
            </a>
            <a
              href="#card-3-cultural-context"
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-xl text-emerald-400 whitespace-nowrap transition-colors"
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>3. Kültürel Bağlam</span>
            </a>
            <a
              href="#card-4-motif-story"
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-xl text-amber-300 whitespace-nowrap transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>4. Motif Hikâyeleri</span>
            </a>
            <a
              href="#card-5-historical-connections"
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-xl text-blue-400 whitespace-nowrap transition-colors"
            >
              <Compass className="w-3.5 h-3.5" />
              <span>5. Tarihsel Bağlantılar</span>
            </a>
          </div>
        </section>

        {/* 5 Primary Semantic Cards */}
        <section className="space-y-12">
          <VisualCharacterCard
            data={result.visual_character}
            primaryImageUrl={result.image_meta.primary_image_url}
          />
          {(result.provenance?.vlm_provider_version === "TEST_FIXTURE" ||
            result.provenance?.vlm_provider_version === "DISABLED" ||
            result.warnings?.some((w) => w.includes("MOTIF_ANALYSIS_UNAVAILABLE"))) && (
            <div className="flex items-center space-x-2.5 px-4 py-3 bg-amber-950/40 border border-amber-500/30 rounded-2xl text-amber-300 text-xs font-semibold shadow-lg">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>Demo verisi — canlı VLM bağlantısı yok</span>
            </div>
          )}
          <MotifCard data={result.motifs} />
          <CulturalContextCard data={result.cultural_context} />
          <MotifStoryCard data={result.motif_story} />
          <HistoricalConnectionsCard data={result.historical_connections} />
        </section>

        {/* Technical Provenance Accordion */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6 space-y-4">
          <button
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            className="flex items-center justify-between w-full text-left font-mono text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            <div className="flex items-center space-x-2">
              <Code2 className="w-4 h-4 text-amber-400" />
              <span className="font-bold uppercase tracking-wider text-slate-200">
                Teknik Sürüm &amp; Provenance Detayları
              </span>
            </div>
            {showTechnicalDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {showTechnicalDetails && (
            <div className="pt-4 border-t border-slate-800 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
              <div className="space-y-2 bg-slate-950 p-4 rounded-2xl border border-slate-800">
                <span className="text-amber-400 font-bold block">Sözleşmeler &amp; Servisler</span>
                <p>Analiz Sözleşmesi: {result.provenance.analysis_contract_version}</p>
                <p>Style DNA: {result.provenance.style_dna_version}</p>
                <p>Renk Analizi: {result.provenance.color_version}</p>
                <p>VLM Sağlayıcı: {result.provenance.vlm_provider_version || "n/a"}</p>
              </div>

              <div className="space-y-2 bg-slate-950 p-4 rounded-2xl border border-slate-800">
                <span className="text-emerald-400 font-bold block">Veri &amp; Korpus Parmak İzleri</span>
                <p>İnceleme Sözleşmesi: {result.provenance.review_version || "n/a"}</p>
                <p>Görsel Arama Sürümü: {result.provenance.visual_retrieval_version}</p>
                <p>Katalog Korpus SHA256: {result.provenance.catalog_corpus_fingerprint?.slice(0, 16) || "n/a"}...</p>
                <p>Tarihsel Korpus SHA256: {result.provenance.historical_corpus_fingerprint?.slice(0, 16) || "n/a"}...</p>
              </div>
            </div>
          )}
        </section>
      </main>

      <Footer />
    </div>
  );
}

function PaletteIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="13.5" cy="6.5" r=".5" fill="currentColor" />
      <circle cx="17.5" cy="10.5" r=".5" fill="currentColor" />
      <circle cx="8.5" cy="7.5" r=".5" fill="currentColor" />
      <circle cx="6.5" cy="12.5" r=".5" fill="currentColor" />
      <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.92 0 1.7-.71 1.7-1.63 0-.44-.18-.85-.47-1.16-.29-.31-.47-.73-.47-1.21 0-.92.71-1.7 1.63-1.7H17c2.76 0 5-2.24 5-5 0-4.42-4.03-8.1-10-8.1z" />
    </svg>
  );
}
