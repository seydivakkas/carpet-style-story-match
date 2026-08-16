"use client";

import { useSearchParams } from "next/navigation";
import { useState, Suspense } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";
import { useCatalogCarpets, resolveCarpetImageUrl } from "@/lib/api/catalog";
import { API_BASE_URL } from "@/lib/constants";
import { BookOpen, Layers, ArrowRight, Image as ImageIcon } from "lucide-react";

function CatalogContent() {
  const searchParams = useSearchParams();
  const assessmentId = searchParams.get("assessment");

  const [manufacturer, setManufacturer] = useState("");
  const [collection, setCollection] = useState("");
  const [material, setMaterial] = useState("");
  const [styleLabel, setStyleLabel] = useState("");

  const { data, isLoading, error, refetch } = useCatalogCarpets({
    manufacturer: manufacturer || undefined,
    collection: collection || undefined,
    material: material || undefined,
    style_label: styleLabel || undefined
  });

  const carpets = data?.carpets || [];

  const resolveImageUrl = (storageKey?: string | null) => {
    if (!storageKey) return null;
    return `${API_BASE_URL}/static/${storageKey}`;
  };

  return (
    <main className="max-w-6xl mx-auto w-full px-6 py-8 flex-1 space-y-6">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center space-x-2 text-xs font-mono text-amber-400">
            <BookOpen className="w-3.5 h-3.5" />
            <span>Katalog Ürün Koleksiyonu</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white mt-1">
            Halı Kataloğu
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Görsel Style DNA profilleri ve belgelenmiş motif hikâyeleriyle zenginleştirilmiş halılar.
          </p>
        </div>

        {assessmentId && (
          <div className="bg-amber-500/10 border border-amber-500/30 px-4 py-2 rounded-xl text-xs text-amber-300 font-mono flex items-center space-x-2">
            <Layers className="w-4 h-4 text-amber-400" />
            <span>Aktif Değerlendirme ile Karşılaştırma Modu</span>
          </div>
        )}
      </div>

      {/* Filter Bar */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div>
          <label className="block text-[11px] font-mono text-slate-400 mb-1">Üretici / Marka</label>
          <input
            type="text"
            placeholder="Filtrele..."
            value={manufacturer}
            onChange={(e) => setManufacturer(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500/50"
          />
        </div>

        <div>
          <label className="block text-[11px] font-mono text-slate-400 mb-1">Koleksiyon</label>
          <input
            type="text"
            placeholder="Filtrele..."
            value={collection}
            onChange={(e) => setCollection(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500/50"
          />
        </div>

        <div>
          <label className="block text-[11px] font-mono text-slate-400 mb-1">Malzeme</label>
          <input
            type="text"
            placeholder="Filtrele..."
            value={material}
            onChange={(e) => setMaterial(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500/50"
          />
        </div>

        <div>
          <label className="block text-[11px] font-mono text-slate-400 mb-1">Stil Etiketi</label>
          <input
            type="text"
            placeholder="Filtrele..."
            value={styleLabel}
            onChange={(e) => setStyleLabel(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500/50"
          />
        </div>
      </div>

      {isLoading ? (
        <LoadingState message="Katalog halıları yükleniyor..." />
      ) : error ? (
        <ErrorState error={error} title="Katalog Yüklenemedi" onRetry={refetch} />
      ) : carpets.length === 0 ? (
        <EmptyState
          title="Katalog Ürünü Bulunmuyor"
          description="Arama kriterlerinize uygun veya veritabanında henüz kayıtlı bir katalog halısı bulunamadı."
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {carpets.map((carpet) => {
            const detailUrl = assessmentId
              ? `/catalog/${carpet.sku}?assessment=${assessmentId}`
              : `/catalog/${carpet.sku}`;

            return (
              <Link
                key={carpet.id}
                href={detailUrl}
                className="group bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden hover:border-slate-700 hover:bg-slate-900/90 transition-all flex flex-col justify-between shadow-lg"
              >
                <div>
                  {/* Image container */}
                  <div className="bg-slate-950 h-52 w-full border-b border-slate-800/80 flex items-center justify-center p-4 overflow-hidden relative">
                    {carpet.primary_image ? (
                      /* eslint-disable-next-line @next/next/no-img-element */
                      <img
                        src={resolveCarpetImageUrl(carpet.id, carpet.primary_image) || ""}
                        alt={carpet.name}
                        className="max-h-full w-auto object-contain rounded group-hover:scale-105 transition-transform duration-300"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                    ) : (
                      <div className="flex flex-col items-center space-y-2 text-slate-600">
                        <ImageIcon className="w-8 h-8" />
                        <span className="text-xs font-mono">Görsel mevcut değil</span>
                      </div>
                    )}

                    <div className="absolute top-3 right-3">
                      <StatusBadge readiness={carpet.style_dna_readiness} />
                    </div>
                  </div>

                  {/* Metadata info */}
                  <div className="p-5 space-y-3">
                    <div>
                      <span className="text-[10px] font-mono text-amber-400 font-bold tracking-wider">
                        {carpet.sku}
                      </span>
                      <h3 className="font-bold text-base text-slate-100 group-hover:text-amber-300 transition-colors line-clamp-1">
                        {carpet.name}
                      </h3>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs text-slate-400 border-t border-slate-800/60 pt-3">
                      {carpet.manufacturer && (
                        <div>
                          <span className="text-[10px] text-slate-500 block">Üretici</span>
                          <span className="text-slate-300 font-medium">{carpet.manufacturer}</span>
                        </div>
                      )}
                      {carpet.collection && (
                        <div>
                          <span className="text-[10px] text-slate-500 block">Koleksiyon</span>
                          <span className="text-slate-300 font-medium">{carpet.collection}</span>
                        </div>
                      )}
                      {carpet.material && (
                        <div>
                          <span className="text-[10px] text-slate-500 block">Malzeme</span>
                          <span className="text-slate-300 font-medium">{carpet.material}</span>
                        </div>
                      )}
                      {carpet.style_label && (
                        <div>
                          <span className="text-[10px] text-slate-500 block">Stil</span>
                          <span className="text-slate-300 font-medium">{carpet.style_label}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-slate-950/60 border-t border-slate-800/60 flex items-center justify-between text-xs font-medium text-amber-400 group-hover:text-amber-300">
                  <span>İncele &amp; Karşılaştır</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </main>
  );
}

export default function CatalogPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header />
      <Suspense fallback={<LoadingState message="Katalog yükleniyor..." />}>
        <CatalogContent />
      </Suspense>
      <Footer />
    </div>
  );
}
