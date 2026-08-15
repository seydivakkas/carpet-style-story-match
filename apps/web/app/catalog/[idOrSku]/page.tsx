"use client";

import { use, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import StatusBadge from "@/components/StatusBadge";
import {
  useCatalogCarpet,
  useCarpetStoryAssociations,
  useCreateStyleMatch,
  useCreateNarrativeAffinity
} from "@/lib/api/catalog";
import {
  useUserPreferenceProfile,
  useImportanceProfile
} from "@/lib/api/preferences";
import { API_BASE_URL, DIMENSION_DETAILS, NARRATIVE_THEME_DETAILS } from "@/lib/constants";
import {
  VisualStyleMatchResultResponse,
  NarrativeAffinityDetailRead
} from "@/lib/types/api";
import {
  Sparkles,
  Layers,
  BookOpen,
  Compass,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Image as ImageIcon
} from "lucide-react";

function CatalogDetailContent({ idOrSku }: { idOrSku: string }) {
  const searchParams = useSearchParams();
  const assessmentId = searchParams.get("assessment");

  const { data: detail, isLoading: carpetLoading, error: carpetError } = useCatalogCarpet(idOrSku);
  const carpetData = detail?.carpet;
  const { data: storyAssociations } = useCarpetStoryAssociations(carpetData?.id || "");

  // Assessment related data if active
  const { data: userProfile } = useUserPreferenceProfile(assessmentId || "");
  const { data: importanceProfile } = useImportanceProfile(assessmentId || "");

  const createStyleMatch = useCreateStyleMatch(assessmentId || "");
  const createNarrativeAffinity = useCreateNarrativeAffinity(assessmentId || "");

  const [styleMatchResult, setStyleMatchResult] = useState<VisualStyleMatchResultResponse | null>(null);
  const [narrativeAffinityResult, setNarrativeAffinityResult] = useState<NarrativeAffinityDetailRead | null>(null);

  const resolveImageUrl = (storageKey?: string | null) => {
    if (!storageKey) return null;
    return `${API_BASE_URL}/static/${storageKey}`;
  };

  if (carpetLoading) {
    return <LoadingState message="Halı detayları yükleniyor..." />;
  }

  if (carpetError || !carpetData) {
    return <ErrorState error={carpetError} title="Halı Detayı Bulunamadı" />;
  }

  const handleCalculateMatch = async () => {
    if (!assessmentId || !userProfile || !detail.style_profile_id) return;
    try {
      const res = await createStyleMatch.mutateAsync({
        user_preference_profile_id: userProfile.id,
        carpet_style_profile_id: detail.style_profile_id,
        importance_profile_id: importanceProfile?.id || null
      });
      setStyleMatchResult(res);
    } catch {
      // Error handled by mutation
    }
  };

  const handleCalculateAffinity = async () => {
    if (!assessmentId || !carpetData.id) return;
    try {
      const res = await createNarrativeAffinity.mutateAsync({
        carpet_id: carpetData.id
      });
      setNarrativeAffinityResult(res);
    } catch {
      // Error handled by mutation
    }
  };

  return (
    <main className="max-w-6xl mx-auto w-full px-6 py-8 flex-1 space-y-8">
      {/* Back Button */}
      <Link
        href={assessmentId ? `/catalog?assessment=${assessmentId}` : "/catalog"}
        className="inline-flex items-center space-x-2 text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Kataloğa Geri Dön</span>
      </Link>

      {/* Main Product Card */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden grid grid-cols-1 lg:grid-cols-2 gap-6 p-6 lg:p-8">
        {/* Left: Image */}
        <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-4 flex items-center justify-center min-h-[300px] lg:min-h-[400px]">
          {detail.primary_image ? (
            <img
              src={resolveImageUrl(detail.primary_image.storage_key || detail.primary_image.file_path) || ""}
              alt={carpetData.name}
              className="max-h-[380px] w-auto object-contain rounded shadow-2xl"
            />
          ) : (
            <div className="flex flex-col items-center space-y-2 text-slate-600">
              <ImageIcon className="w-12 h-12" />
              <span className="text-sm font-mono">Görsel bulunmuyor</span>
            </div>
          )}
        </div>

        {/* Right: Info */}
        <div className="space-y-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs text-amber-400 font-bold px-2.5 py-1 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                SKU: {carpetData.sku}
              </span>
              <StatusBadge readiness={detail.style_dna_readiness} />
            </div>

            <h1 className="text-2xl lg:text-3xl font-bold tracking-tight text-white">
              {carpetData.name}
            </h1>

            <div className="grid grid-cols-2 gap-4 text-xs text-slate-300 bg-slate-950/60 border border-slate-800/60 rounded-xl p-4">
              {carpetData.manufacturer && (
                <div>
                  <span className="text-slate-500 block text-[10px]">Üretici</span>
                  <span className="font-semibold">{carpetData.manufacturer}</span>
                </div>
              )}
              {carpetData.collection && (
                <div>
                  <span className="text-slate-500 block text-[10px]">Koleksiyon</span>
                  <span className="font-semibold">{carpetData.collection}</span>
                </div>
              )}
              {carpetData.material && (
                <div>
                  <span className="text-slate-500 block text-[10px]">Malzeme</span>
                  <span className="font-semibold">{carpetData.material}</span>
                </div>
              )}
              {carpetData.style_label && (
                <div>
                  <span className="text-slate-500 block text-[10px]">Stil Etiketi</span>
                  <span className="font-semibold">{carpetData.style_label}</span>
                </div>
              )}
            </div>
          </div>

          {/* Motifs & Story Associations */}
          <div className="space-y-3 border-t border-slate-800/60 pt-4">
            <h3 className="text-xs font-mono text-slate-400 uppercase font-bold tracking-wider">
              Motif &amp; Anlatı Bilgisi
            </h3>

            {detail.motifs && detail.motifs.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {detail.motifs.map((m) => (
                  <span
                    key={m.id}
                    className="text-xs px-2.5 py-1 bg-slate-800/80 text-slate-200 border border-slate-700/80 rounded-lg"
                  >
                    {m.motif_name_tr || m.motif_key}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">Motif tanımı eklenmemiş.</p>
            )}

            {storyAssociations && storyAssociations.length > 0 && (
              <div className="space-y-2 pt-2">
                <span className="text-[11px] font-semibold text-amber-400 block">
                  Bağlı Motif Hikâyeleri:
                </span>
                <ul className="space-y-1 text-xs text-slate-300">
                  {storyAssociations.map((sa) => (
                    <li key={sa.id} className="flex items-start space-x-2">
                      <BookOpen className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                      <span>{sa.motif_name_tr} ({sa.claim_key})</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* THREE INDEPENDENT EVALUATION AXES SECTION */}
      {assessmentId && (
        <div className="space-y-8 pt-4">
          <div className="border-b border-slate-800/80 pb-3 flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-amber-400" />
            <h2 className="text-xl font-bold tracking-tight text-white">
              Üç Bağımsız Ürün Değerlendirme Ekseni
            </h2>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* AXIS 1: Görsel Stil Uyumu */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-6 flex flex-col justify-between">
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl">
                    <Layers className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-[10px] font-mono text-amber-400 uppercase font-bold">Eksen 1</span>
                    <h3 className="text-lg font-bold text-slate-100">Görsel Stil Uyumu</h3>
                  </div>
                </div>

                <p className="text-xs text-slate-400 leading-relaxed">
                  9 boyutlu Style DNA vektörünün sizin estetik tercihleriniz ve önem ağırlıklarınız ile karşılaştırılması.
                </p>

                {styleMatchResult ? (
                  <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <span className="text-[10px] font-mono text-slate-400">Style Match Skoru</span>
                        <div className="text-3xl font-mono font-bold text-amber-300">
                          {(styleMatchResult.score_100 ?? 0).toFixed(0)} <span className="text-sm font-normal text-slate-500">/ 100</span>
                        </div>
                      </div>
                      <StatusBadge status={styleMatchResult.match_label} />
                    </div>

                    {/* Pairwise breakdown */}
                    <div className="space-y-2 border-t border-slate-800/60 pt-3">
                      <span className="text-[11px] font-semibold text-slate-300 block">
                        9D Vektör Karşılaştırma Ayrıntısı:
                      </span>
                      <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
                        {styleMatchResult.dimensions.map((db) => {
                          const meta = DIMENSION_DETAILS[db.dimension_key] || { label_tr: db.dimension_key };
                          return (
                            <div
                              key={db.dimension_key}
                              className="flex items-center justify-between text-xs py-1 px-2 bg-slate-900/60 rounded border border-slate-800/40"
                            >
                              <span className="text-slate-300 font-medium">{meta.label_tr}</span>
                              <div className="flex items-center space-x-3 font-mono text-[11px]">
                                <span className="text-slate-400">Siz: {(db.user_value ?? 0).toFixed(2)}</span>
                                <span className="text-slate-400">Halı: {(db.carpet_value ?? 0).toFixed(2)}</span>
                                <span className="text-amber-400 font-bold">Fark: {(db.difference ?? 0).toFixed(2)}</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 bg-slate-950 border border-slate-800/60 rounded-xl text-center text-xs text-slate-500">
                    Henüz hesaplama yapılmadı.
                  </div>
                )}
              </div>

              <button
                onClick={handleCalculateMatch}
                disabled={createStyleMatch.isPending || !detail.style_profile_id}
                className="w-full py-3 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-xl transition-all shadow-lg shadow-amber-500/10 disabled:opacity-40"
              >
                {createStyleMatch.isPending ? "Hesaplanıyor..." : "Görsel Stil Uyumunu Hesapla"}
              </button>
            </div>

            {/* AXIS 2: Anlatı Yakınlığı */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-6 flex flex-col justify-between">
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2.5 bg-emerald-500/10 text-emerald-400 rounded-xl">
                    <BookOpen className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-[10px] font-mono text-emerald-400 uppercase font-bold">Eksen 2</span>
                    <h3 className="text-lg font-bold text-slate-100">Anlatı Yakınlığı</h3>
                  </div>
                </div>

                <p className="text-xs text-slate-400 leading-relaxed">
                  Seçtiğiniz kültürel motif temalarının halının belgelenmiş anlatı iddialarıyla uyumu (Kategorik Seviye).
                </p>

                {narrativeAffinityResult ? (
                  <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-400">Kategorik Uyumluluk Seviyesi:</span>
                      <StatusBadge status={narrativeAffinityResult.result.affinity_level} />
                    </div>

                    {/* Aligned themes */}
                    {narrativeAffinityResult.explanation.aligned_themes.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[11px] font-semibold text-emerald-400 block">
                          Örtüşen İlgi Temaları:
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {narrativeAffinityResult.explanation.aligned_themes.map((at) => {
                            const meta = NARRATIVE_THEME_DETAILS[at.theme_key] || { label_tr: at.theme_key, icon: "📜" };
                            return (
                              <span
                                key={at.theme_key}
                                className="text-xs px-2.5 py-1 bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 rounded-lg flex items-center space-x-1"
                              >
                                <span>{meta.icon}</span>
                                <span>{meta.label_tr}</span>
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Contested overlaps warning if present */}
                    {narrativeAffinityResult.explanation.contested_overlaps.length > 0 && (
                      <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-200 flex items-start space-x-2">
                        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                        <div>
                          <span className="font-bold block">⚠ Tartışmalı Motif Yorumları:</span>
                          <span className="text-[11px] text-amber-200/90">
                            Bazı motifler akademik literatürde birden fazla farklı kültürel anlamla yorumlanmaktadır.
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-4 bg-slate-950 border border-slate-800/60 rounded-xl text-center text-xs text-slate-500">
                    Henüz hesaplama yapılmadı.
                  </div>
                )}
              </div>

              <button
                onClick={handleCalculateAffinity}
                disabled={createNarrativeAffinity.isPending}
                className="w-full py-3 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs rounded-xl transition-all shadow-lg shadow-emerald-500/10 disabled:opacity-40"
              >
                {createNarrativeAffinity.isPending ? "Hesaplanıyor..." : "Anlatı Yakınlığını Hesapla"}
              </button>
            </div>
          </div>

          {/* AXIS 3: Tarihsel Referans Bağlantısı */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 bg-blue-500/10 text-blue-400 rounded-xl">
                <Compass className="w-5 h-5" />
              </div>
              <div>
                <span className="text-[10px] font-mono text-blue-400 uppercase font-bold">Eksen 3</span>
                <h3 className="text-lg font-bold text-slate-100">Tarihsel Referans Bağlantısı</h3>
              </div>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Bu katalog halısının Style DNA yapısını müze koleksiyonlarında (Met, V&amp;A, TİEM) yer alan doğrulanmış tarihi dokumalar ile boyut boyut karşılaştırın.
            </p>

            {detail.style_profile_id ? (
              <Link
                href={`/historical-references?target_carpet_id=${carpetData.id}&target_style_profile_id=${detail.style_profile_id}`}
                className="inline-flex items-center space-x-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-xl transition-all shadow-lg shadow-blue-600/20"
              >
                <span>Tarihsel Müze Referansı Bağlantılarını İncele</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            ) : (
              <span className="text-xs text-slate-500 italic block">
                Bu halının Style DNA profili tamamlanmadığından tarihsel bağlantı kurulamıyor.
              </span>
            )}
          </div>
        </div>
      )}
    </main>
  );
}

export default function CatalogDetailPage({ params }: { params: Promise<{ idOrSku: string }> }) {
  const { idOrSku } = use(params);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header />
      <Suspense fallback={<LoadingState message="Detaylar yükleniyor..." />}>
        <CatalogDetailContent idOrSku={idOrSku} />
      </Suspense>
      <Footer />
    </div>
  );
}
