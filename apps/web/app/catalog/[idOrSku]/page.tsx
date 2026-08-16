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
  useCarpetMotifs,
  useCarpetStoryAssociations,
  useCarpetStyleDna,
  useCreateStyleMatch,
  useCreateNarrativeAffinity,
  resolveCarpetImageUrl
} from "@/lib/api/catalog";
import {
  useUserPreferenceProfile,
  useImportanceProfile
} from "@/lib/api/preferences";
import { DIMENSION_DETAILS, NARRATIVE_THEME_DETAILS } from "@/lib/constants";
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
  Image as ImageIcon,
  ExternalLink,
  Info,
  CheckCircle2,
  HelpCircle,
  BarChart3,
  Loader2
} from "lucide-react";

// Dimension labels for 9D Style DNA
const STYLE_DNA_DIMENSION_LABELS: Record<string, { label_tr: string; desc_tr: string }> = {
  color_energy: {
    label_tr: "Renksel Enerji",
    desc_tr: "Renk canlılığı ve kroma yoğunluğu"
  },
  color_diversity: {
    label_tr: "Renk Çeşitliliği",
    desc_tr: "Renk palet zenginliği ve renk entropisi"
  },
  contrast: {
    label_tr: "Kontrast",
    desc_tr: "Işık-gölge ve ton parlaklığı farkı"
  },
  warmth: {
    label_tr: "Sıcaklık",
    desc_tr: "Sıcak ve soğuk ton dengesi"
  },
  visual_complexity: {
    label_tr: "Görsel Karmaşıklık",
    desc_tr: "Kenar yoğunluğu ve detay katmanı"
  },
  structural_order: {
    label_tr: "Yapısal Düzen",
    desc_tr: "Simetri ve eksenel kompozisyon dengesi"
  },
  rhythm_repetition: {
    label_tr: "Ritim & Tekrar",
    desc_tr: "Motif ve desen tekrarlama frekansı"
  },
  focal_strength: {
    label_tr: "Odak Gücü",
    desc_tr: "Merkezi göbek vurgusu ve görsel çekim"
  },
  form_language: {
    label_tr: "Form Dili",
    desc_tr: "Geometrik hatlar ile organik formlar dengesi"
  }
};

function CatalogDetailContent({ idOrSku }: { idOrSku: string }) {
  const searchParams = useSearchParams();
  const assessmentId = searchParams.get("assessment");

  const { data: detail, isLoading: carpetLoading, error: carpetError } = useCatalogCarpet(idOrSku);
  const carpetData = detail?.carpet;
  const carpetId = carpetData?.id || "";

  const { data: motifs } = useCarpetMotifs(idOrSku);
  const { data: storyAssociations } = useCarpetStoryAssociations(idOrSku);
  const { data: styleDnaProfile } = useCarpetStyleDna(carpetId, detail?.primary_image?.image_id);

  // Active assessment data if in assessment mode
  const { data: userProfile } = useUserPreferenceProfile(assessmentId || "");
  const { data: importanceProfile } = useImportanceProfile(assessmentId || "");

  const createStyleMatch = useCreateStyleMatch(assessmentId || "");
  const createNarrativeAffinity = useCreateNarrativeAffinity(assessmentId || "");

  const [styleMatchResult, setStyleMatchResult] = useState<VisualStyleMatchResultResponse | null>(null);
  const [narrativeAffinityResult, setNarrativeAffinityResult] = useState<NarrativeAffinityDetailRead | null>(null);
  const [styleMatchError, setStyleMatchError] = useState<string | null>(null);
  const [narrativeAffinityError, setNarrativeAffinityError] = useState<string | null>(null);

  if (carpetLoading) {
    return <LoadingState message="Halı detayları ve Style DNA verileri yükleniyor..." />;
  }

  if (carpetError || !carpetData) {
    return <ErrorState error={carpetError} title="Halı Detayı Bulunamadı" />;
  }

  const primaryImageUrl = resolveCarpetImageUrl(carpetData.id, detail.primary_image);

  const handleCalculateMatch = async () => {
    if (!assessmentId || !userProfile || !detail.style_profile_id) return;
    setStyleMatchError(null);
    try {
      const res = await createStyleMatch.mutateAsync({
        user_preference_profile_id: userProfile.id,
        carpet_style_profile_id: detail.style_profile_id,
        importance_profile_id: importanceProfile?.id || null
      });
      setStyleMatchResult(res);
    } catch (err: unknown) {
      setStyleMatchError((err as Error)?.message || "Görsel stil uyumu hesaplanırken bir hata oluştu.");
    }
  };

  const handleCalculateAffinity = async () => {
    if (!assessmentId || !carpetData.id) return;
    setNarrativeAffinityError(null);
    try {
      const res = await createNarrativeAffinity.mutateAsync({
        carpet_id: carpetData.id
      });
      setNarrativeAffinityResult(res);
    } catch (err: unknown) {
      setNarrativeAffinityError((err as Error)?.message || "Anlatı yakınlığı hesaplanırken bir hata oluştu.");
    }
  };

  return (
    <main className="max-w-6xl mx-auto w-full px-4 sm:px-6 py-8 flex-1 space-y-8">
      {/* Top Header & Navigation */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <Link
          href={assessmentId ? `/catalog?assessment=${assessmentId}` : "/catalog"}
          className="inline-flex items-center space-x-2 text-xs font-mono text-slate-400 hover:text-amber-400 transition-colors bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-800"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Kataloğa Geri Dön</span>
        </Link>

        {assessmentId && (
          <div className="bg-amber-500/10 border border-amber-500/30 px-3.5 py-1.5 rounded-xl text-xs text-amber-300 font-mono flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-amber-400 animate-pulse" />
            <span>Aktif Değerlendirme Karşılaştırma Modu</span>
          </div>
        )}
      </div>

      {/* Main Product Hero Card (45/55 Desktop Grid Layout) */}
      <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl overflow-hidden grid grid-cols-1 lg:grid-cols-12 gap-8 p-6 lg:p-8 shadow-2xl">
        {/* Left: Image Container (5 cols on lg) */}
        <div className="lg:col-span-5 flex flex-col items-center justify-center bg-slate-950 border border-slate-800/80 rounded-xl p-4 min-h-[340px] lg:min-h-[440px] relative overflow-hidden shadow-inner group">
          {primaryImageUrl ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={primaryImageUrl}
              alt={carpetData.name}
              className="max-h-[420px] w-auto object-contain rounded-lg shadow-2xl transition-transform duration-300 group-hover:scale-105"
            />
          ) : (
            <div className="flex flex-col items-center justify-center space-y-3 p-8 text-center">
              <div className="w-16 h-16 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500">
                <ImageIcon className="w-8 h-8" />
              </div>
              <div className="space-y-1">
                <span className="text-sm font-semibold text-slate-300 block">Görsel Hazırlanıyor</span>
                <p className="text-xs text-slate-500 max-w-[220px]">
                  Bu halı ürünü için resmi görsel henüz sisteme aktarılmamıştır.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Right: Product Metadata & Info (7 cols on lg) */}
        <div className="lg:col-span-7 space-y-6 flex flex-col justify-between">
          <div className="space-y-5">
            {/* Header Badges */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/60 pb-3">
              <div className="flex items-center space-x-2">
                <span className="font-mono text-xs text-amber-400 font-bold px-3 py-1 bg-amber-500/10 border border-amber-500/30 rounded-lg shadow-sm">
                  SKU: {carpetData.sku}
                </span>
                <span className="text-[11px] font-mono text-slate-400 px-2.5 py-1 bg-slate-800/60 border border-slate-700/60 rounded-lg">
                  {carpetData.source_type}
                </span>
              </div>
              <StatusBadge readiness={detail.style_dna_readiness} />
            </div>

            {/* Product Title */}
            <div>
              <h1 className="text-2xl lg:text-3xl font-extrabold tracking-tight text-white">
                {carpetData.name}
              </h1>
              {carpetData.description && (
                <p className="text-xs text-slate-400 leading-relaxed mt-2">
                  {carpetData.description}
                </p>
              )}
            </div>

            {/* Structured Specifications Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs text-slate-300 bg-slate-950/80 border border-slate-800/70 rounded-xl p-4">
              {carpetData.manufacturer && (
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-mono">Üretici / Marka</span>
                  <span className="font-semibold text-slate-200">{carpetData.manufacturer}</span>
                </div>
              )}
              {carpetData.collection && (
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-mono">Koleksiyon</span>
                  <span className="font-semibold text-slate-200">{carpetData.collection}</span>
                </div>
              )}
              {carpetData.material && (
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-mono">Malzeme</span>
                  <span className="font-semibold text-slate-200">{carpetData.material}</span>
                </div>
              )}
              {carpetData.style_label && (
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-mono">Stil Etiketi</span>
                  <span className="font-semibold text-amber-300">{carpetData.style_label}</span>
                </div>
              )}
              {(carpetData.width_cm || carpetData.height_cm) && (
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-mono">Ebatlar</span>
                  <span className="font-semibold text-slate-200">
                    {carpetData.width_cm || "?"} x {carpetData.height_cm || "?"} cm
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Source Reference Link */}
          {carpetData.source_reference && (
            <div className="pt-2">
              <a
                href={carpetData.source_reference}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-2 text-xs font-mono text-amber-400 hover:text-amber-300 transition-colors"
              >
                <span>Resmi Ürün Sayfasını İncele (Merinos)</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          )}
        </div>
      </div>

      {/* VISIBLE 9D STYLE DNA BREAKDOWN SECTION */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 lg:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl border border-amber-500/20">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">
                9 Boyutlu Görsel Style DNA Profili
              </h2>
              <p className="text-xs text-slate-400">
                Halı görselinin matematiksel görüntü işleme algoritmalarıyla hesaplanmış 9 boyutlu estetik vektörü.
              </p>
            </div>
          </div>

          <StatusBadge readiness={detail.style_dna_readiness} />
        </div>

        {styleDnaProfile?.dimensions && styleDnaProfile.dimensions.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {styleDnaProfile.dimensions.map((dim) => {
              const meta = STYLE_DNA_DIMENSION_LABELS[dim.key] || {
                label_tr: dim.key,
                desc_tr: "Style DNA parametresi"
              };
              const numVal = dim.value ?? 0;
              const percentVal = Math.round(numVal * 100);

              return (
                <div
                  key={dim.key}
                  className="bg-slate-950/70 border border-slate-800/70 rounded-xl p-4 space-y-2 flex flex-col justify-between"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-xs font-bold text-slate-200 block">
                        {meta.label_tr}
                      </span>
                      <span className="text-[10px] text-slate-500 leading-tight block mt-0.5">
                        {meta.desc_tr}
                      </span>
                    </div>
                    <span className="font-mono text-xs font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                      {numVal.toFixed(2)}
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div className="space-y-1 pt-1">
                    <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden border border-slate-800">
                      <div
                        className="h-full bg-gradient-to-r from-amber-600 to-amber-400 rounded-full transition-all duration-500"
                        style={{ width: `${Math.min(100, Math.max(0, percentVal))}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
                      <span>0.00</span>
                      <span>Güven: %{Math.round(dim.confidence * 100)}</span>
                      <span>1.00</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-6 bg-slate-950/60 border border-slate-800/60 rounded-xl text-center space-y-2">
            <Info className="w-8 h-8 text-slate-500 mx-auto" />
            <p className="text-xs text-slate-400">
              Bu halı için 9D Style DNA vektör detayları henüz yüklenemedi veya hesaplanma aşamasında.
            </p>
          </div>
        )}
      </div>

      {/* MOTIF & ANLATIBILGI SECTION (UNCERTAIN MOTIF CURATION HANDLING) */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 lg:p-8 space-y-6">
        <div className="flex items-center space-x-3 border-b border-slate-800/80 pb-4">
          <div className="p-2.5 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-100">
              Motif &amp; Anlatı Bilgisi Kürasyonu
            </h2>
            <p className="text-xs text-slate-400">
              Akademik literatür kaynaklarına göre belgelenmiş motif varlığı ve kültürel anlatı iddiaları.
            </p>
          </div>
        </div>

        {/* Motifs Listing */}
        <div className="space-y-4">
          <h3 className="text-xs font-mono text-slate-400 uppercase font-bold tracking-wider">
            Halı Üzerinde İncelenen Motifler
          </h3>

          {motifs && motifs.length > 0 ? (
            <div className="space-y-3">
              {motifs.map((m) => {
                const isUncertain = m.evidence_type === "UNCERTAIN";
                return (
                  <div
                    key={m.id}
                    className={`p-4 rounded-xl border transition-all ${
                      isUncertain
                        ? "bg-amber-500/10 border-amber-500/30 text-amber-200"
                        : "bg-slate-950/70 border-slate-800 text-slate-200"
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center space-x-2.5">
                        <span className="font-bold text-sm text-slate-100">
                          {m.motif_name_tr}
                        </span>
                        <span className="text-xs font-mono text-slate-400">
                          ({m.motif_key})
                        </span>
                      </div>

                      {/* Evidence Badge */}
                      {isUncertain ? (
                        <span className="inline-flex items-center space-x-1.5 text-xs font-bold px-2.5 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded-lg">
                          <HelpCircle className="w-3.5 h-3.5" />
                          <span>Kesinleştirilmemiş</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1.5 text-xs font-semibold px-2.5 py-1 bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 rounded-lg">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          <span>{m.evidence_type}</span>
                        </span>
                      )}
                    </div>

                    {/* Uncertainty Note Callout for UNCERTAIN evidence */}
                    {isUncertain && (
                      <div className="mt-3 p-3 bg-amber-950/40 border border-amber-500/30 rounded-lg text-xs space-y-1">
                        <div className="flex items-center space-x-2 text-amber-400 font-semibold">
                          <AlertTriangle className="w-4 h-4 shrink-0" />
                          <span>Küratör Değerlendirme Notu:</span>
                        </div>
                        <p className="text-amber-200/90 text-xs leading-relaxed pl-6">
                          {m.uncertainty_note || "Bu motif ilişkilendirmesi henüz kesinleşmemiştir ve ilave inceleme gerektirmektedir."}
                        </p>
                      </div>
                    )}

                    {/* Curation Note if present */}
                    {m.curation_note && !isUncertain && (
                      <p className="text-xs text-slate-400 mt-2 italic">
                        {m.curation_note}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-slate-500 italic bg-slate-950/50 p-4 rounded-xl border border-slate-800/50">
              Bu halı için henüz motif ve anlatı kaydı girilmemiştir.
            </p>
          )}
        </div>

        {/* Story Associations Listing */}
        <div className="space-y-3 border-t border-slate-800/60 pt-4">
          <h3 className="text-xs font-mono text-slate-400 uppercase font-bold tracking-wider">
            Bağlı Kültürel Motif Hikâyeleri
          </h3>

          {storyAssociations && storyAssociations.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {storyAssociations.map((sa) => (
                <div
                  key={sa.id}
                  className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-amber-400">
                      {sa.motif_name_tr}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                      {sa.claim_key}
                    </span>
                  </div>

                  {sa.claim_text_tr && (
                    <p className="text-xs text-slate-300 leading-relaxed">
                      {sa.claim_text_tr}
                    </p>
                  )}

                  {sa.themes && sa.themes.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {sa.themes.map((th) => {
                        const meta = NARRATIVE_THEME_DETAILS[th] || { label_tr: th, icon: "📜" };
                        return (
                          <span
                            key={th}
                            className="text-[10px] px-2 py-0.5 bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 rounded flex items-center space-x-1"
                          >
                            <span>{meta.icon}</span>
                            <span>{meta.label_tr}</span>
                          </span>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 bg-slate-950/50 border border-slate-800/50 rounded-xl text-xs text-slate-400 space-y-1">
              <p>
                {motifs?.some((m) => m.evidence_type === "UNCERTAIN")
                  ? "Kesinleştirilmemiş motifler için hikâye anlatısı türetilmemektedir."
                  : "Bu halı için belgelenmiş anlatı hikâyesi kaydı bulunmamaktadır."}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* RESTRUCTURED THREE INDEPENDENT EVALUATION AXES SECTION */}
      <div className="space-y-6 pt-4">
        <div className="border-b border-slate-800/80 pb-3 flex items-center space-x-3">
          <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              Bu Halıyı 3 Ayrı Eksende İncele
            </h2>
            <p className="text-xs text-slate-400">
              Görsel stil, kültürel anlatı ve tarihi müze dokumaları ile bağımsız 3 eksen analizi.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* AXIS 1: Görsel Stil Uyumu (Amber Theme) */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-5 flex flex-col justify-between shadow-lg hover:border-amber-500/40 transition-colors">
            <div className="space-y-4">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl border border-amber-500/20">
                  <Layers className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-mono text-amber-400 uppercase font-bold tracking-wider">Eksen 1</span>
                  <h3 className="text-base font-bold text-slate-100">Görsel Stil Uyumu</h3>
                </div>
              </div>

              <p className="text-xs text-slate-400 leading-relaxed">
                9 boyutlu Style DNA vektörünün estetik tercihleriniz ve önem ağırlıklarınız ile karşılaştırılması.
              </p>

              {/* State 1: Prerequisite Missing */}
              {!assessmentId && (
                <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-200 space-y-2">
                  <p className="font-semibold">Görsel Stil Uyumunu Hesaplama Prereq:</p>
                  <p className="text-[11px] text-amber-200/90">
                    Estetik stil profilinizin hesaplanabilmesi için aktif bir Değerlendirme oturumu gereklidir.
                  </p>
                  <Link
                    href="/assessment/start"
                    className="inline-flex items-center space-x-1.5 font-bold text-amber-400 hover:text-amber-300 transition-colors pt-1"
                  >
                    <span>Değerlendirme Başlat</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              )}

              {/* State 2: Ready / Loaded Result */}
              {assessmentId && (
                <>
                  {styleMatchResult ? (
                    <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-4">
                      <div className="flex items-center justify-between border-b border-slate-800/60 pb-3">
                        <div>
                          <span className="text-[10px] font-mono text-slate-400 block uppercase">Stil Uyum Skoru</span>
                          <div className="text-3xl font-mono font-bold text-amber-300">
                            {(styleMatchResult.score_100 ?? 0).toFixed(0)}{" "}
                            <span className="text-xs font-normal text-slate-500">/ 100</span>
                          </div>
                        </div>
                        <StatusBadge status={styleMatchResult.match_label} />
                      </div>

                      {/* Dimension Differences Breakdown */}
                      <div className="space-y-2">
                        <span className="text-[11px] font-semibold text-slate-300 block">
                          Vektör Karşılaştırma Özeti:
                        </span>
                        <div className="space-y-1.5 max-h-44 overflow-y-auto pr-1">
                          {styleMatchResult.dimensions.map((db) => {
                            const meta = STYLE_DNA_DIMENSION_LABELS[db.dimension_key] || { label_tr: db.dimension_key };
                            return (
                              <div
                                key={db.dimension_key}
                                className="flex items-center justify-between text-xs py-1 px-2.5 bg-slate-900/80 rounded-lg border border-slate-800/50"
                              >
                                <span className="text-slate-300 font-medium text-[11px]">
                                  {meta.label_tr}
                                </span>
                                <span className="font-mono text-[11px] font-bold text-amber-400">
                                  Fark: {(db.difference ?? 0).toFixed(2)}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 bg-slate-950/60 border border-slate-800/60 rounded-xl text-center text-xs text-slate-500">
                      Henüz görsel stil uyumu hesaplanmadı.
                    </div>
                  )}
                </>
              )}

              {styleMatchError && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-300">
                  {styleMatchError}
                </div>
              )}
            </div>

            {assessmentId && (
              <button
                onClick={handleCalculateMatch}
                disabled={createStyleMatch.isPending || !detail.style_profile_id}
                className="w-full py-3 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-xl transition-all shadow-lg shadow-amber-500/10 disabled:opacity-40 flex items-center justify-center space-x-2"
              >
                {createStyleMatch.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Hesaplanıyor...</span>
                  </>
                ) : (
                  <span>Görsel Stil Uyumunu Hesapla</span>
                )}
              </button>
            )}
          </div>

          {/* AXIS 2: Anlatı Yakınlığı (Emerald Theme) */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-5 flex flex-col justify-between shadow-lg hover:border-emerald-500/40 transition-colors">
            <div className="space-y-4">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20">
                  <BookOpen className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-mono text-emerald-400 uppercase font-bold tracking-wider">Eksen 2</span>
                  <h3 className="text-base font-bold text-slate-100">Anlatı Yakınlığı</h3>
                </div>
              </div>

              <p className="text-xs text-slate-400 leading-relaxed">
                Seçtiğiniz kültürel motif temalarının halının belgelenmiş anlatı iddialarıyla uyumu.
              </p>

              {/* State 1: Prerequisite Missing */}
              {!assessmentId && (
                <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs text-emerald-200 space-y-2">
                  <p className="font-semibold">Anlatı Yakınlığı Hesaplama Prereq:</p>
                  <p className="text-[11px] text-emerald-200/90">
                    Kültürel anlatı ilgi alanlarınızı belirlemek için bir Değerlendirme başlatın.
                  </p>
                  <Link
                    href="/assessment/start"
                    className="inline-flex items-center space-x-1.5 font-bold text-emerald-400 hover:text-emerald-300 transition-colors pt-1"
                  >
                    <span>Değerlendirme Başlat</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              )}

              {/* State 2: Truthful Notice for 0 Story Associations or Uncertain Motif */}
              {assessmentId && detail.story_association_count === 0 && (
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-400 space-y-2">
                  <div className="flex items-center space-x-2 text-amber-400 font-semibold">
                    <Info className="w-4 h-4 shrink-0" />
                    <span>Anlatı İddiası Bulunmuyor</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    Bu halı için belgelenmiş anlatı hikâyesi bulunmadığından anlatı yakınlığı türetilememektedir.
                  </p>
                </div>
              )}

              {/* State 3: Ready / Loaded Result */}
              {assessmentId && detail.story_association_count > 0 && (
                <>
                  {narrativeAffinityResult ? (
                    <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
                      <div className="flex items-center justify-between border-b border-slate-800/60 pb-3">
                        <span className="text-xs text-slate-400 font-medium">Kategorik Uyum:</span>
                        <StatusBadge status={narrativeAffinityResult.result.affinity_level} />
                      </div>

                      {/* Aligned Themes */}
                      {narrativeAffinityResult.explanation.aligned_themes.length > 0 && (
                        <div className="space-y-1.5">
                          <span className="text-[11px] font-semibold text-emerald-400 block">
                            Örtüşen Kültürel Temalar:
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

                      {/* Contested Overlaps Callout */}
                      {narrativeAffinityResult.explanation.contested_overlaps.length > 0 && (
                        <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs text-amber-200 flex items-start space-x-2">
                          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                          <span className="text-[11px]">
                            Bazı motifler akademik literatürde birden fazla farklı anlamla yorumlanmaktadır.
                          </span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-4 bg-slate-950/60 border border-slate-800/60 rounded-xl text-center text-xs text-slate-500">
                      Henüz anlatı yakınlığı hesaplanmadı.
                    </div>
                  )}
                </>
              )}

              {narrativeAffinityError && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-300">
                  {narrativeAffinityError}
                </div>
              )}
            </div>

            {assessmentId && detail.story_association_count > 0 && (
              <button
                onClick={handleCalculateAffinity}
                disabled={createNarrativeAffinity.isPending}
                className="w-full py-3 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs rounded-xl transition-all shadow-lg shadow-emerald-500/10 disabled:opacity-40 flex items-center justify-center space-x-2"
              >
                {createNarrativeAffinity.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Hesaplanıyor...</span>
                  </>
                ) : (
                  <span>Anlatı Yakınlığını Hesapla</span>
                )}
              </button>
            )}
          </div>

          {/* AXIS 3: Tarihsel Referans Bağlantısı (Blue Theme) */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-5 flex flex-col justify-between shadow-lg hover:border-blue-500/40 transition-colors">
            <div className="space-y-4">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 bg-blue-500/10 text-blue-400 rounded-xl border border-blue-500/20">
                  <Compass className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-mono text-blue-400 uppercase font-bold tracking-wider">Eksen 3</span>
                  <h3 className="text-base font-bold text-slate-100">Tarihsel Referans Bağlantısı</h3>
                </div>
              </div>

              <p className="text-xs text-slate-400 leading-relaxed">
                Bu halının Style DNA profilini Met, V&amp;A ve TİEM müze koleksiyonlarındaki doğrulanmış tarihi dokumalar ile karşılaştırın.
              </p>

              <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-2 text-xs text-slate-300">
                <div className="flex items-center space-x-2 font-semibold text-blue-400">
                  <Info className="w-4 h-4 shrink-0" />
                  <span>Doğrulanmış Müze Veritabanı</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  100 tarihi müze dokumasının 9D Style DNA profilleri ile boyut boyut benzerlik matrisi karşılaştırması.
                </p>
              </div>
            </div>

            {detail.style_profile_id ? (
              <Link
                href={`/historical-references?target_carpet_id=${carpetData.id}&target_style_profile_id=${detail.style_profile_id}`}
                className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-xl transition-all shadow-lg shadow-blue-600/20 flex items-center justify-center space-x-2"
              >
                <span>Tarihsel Müze Bağlantılarını İncele</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            ) : (
              <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl text-center text-xs text-slate-500 italic">
                Style DNA profili tamamlanmadığından tarihsel bağlantı kurulamıyor.
              </div>
            )}
          </div>
        </div>
      </div>
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
