"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useState, Suspense } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";
import DisclaimerBanner from "@/components/DisclaimerBanner";
import { useHistoricalReferences, useCreateHistoricalConnection } from "@/lib/api/historical";
import { Compass, ArrowRight, Building2, Calendar, MapPin } from "lucide-react";

function HistoricalReferencesContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const targetCarpetId = searchParams.get("target_carpet_id");
  const targetStyleProfileId = searchParams.get("target_style_profile_id");

  const [museum, setMuseum] = useState("");
  const [region, setRegion] = useState("");
  const [styleGroup, setStyleGroup] = useState("");

  const { data, isLoading, error, refetch } = useHistoricalReferences({
    museum: museum || undefined,
    region: region || undefined,
    style_group: styleGroup || undefined
  });

  const createConnection = useCreateHistoricalConnection();

  const references = data?.references || [];

  const handleSelectReference = async (referenceKey: string) => {
    if (!targetStyleProfileId) return;
    try {
      const conn = await createConnection.mutateAsync({
        target_style_profile_id: targetStyleProfileId,
        historical_reference_id: referenceKey
      });
      router.push(`/historical-connections/${conn.id}`);
    } catch {
      // Error handled by mutation
    }
  };

  return (
    <main className="max-w-6xl mx-auto w-full px-6 py-8 flex-1 space-y-6">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center space-x-2 text-xs font-mono text-blue-400">
            <Compass className="w-3.5 h-3.5" />
            <span>Müze &amp; Arşiv Doğrulanmış Referanslar</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white mt-1">
            Tarihsel Referans Koleksiyonu
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Dünya müzelerindeki (Met, V&amp;A, TİEM vb.) tarihi dokumaların 9D görsel Style DNA profilleri.
          </p>
        </div>

        {targetStyleProfileId && (
          <div className="bg-blue-500/10 border border-blue-500/30 px-4 py-2 rounded-xl text-xs text-blue-300 font-mono">
            Tarihsel Bağlantı Kurma Modu Aktif
          </div>
        )}
      </div>

      <DisclaimerBanner />

      {/* Filter Bar */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label className="block text-[11px] font-mono text-slate-400 mb-1">Müze / Kurum</label>
          <input
            type="text"
            placeholder="Met, V&A, TIEM..."
            value={museum}
            onChange={(e) => setMuseum(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500/50"
          />
        </div>

        <div>
          <label className="block text-[11px] font-mono text-slate-400 mb-1">Köken Bölgesi</label>
          <input
            type="text"
            placeholder="Anadolu, İran, Kafkas..."
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500/50"
          />
        </div>

        <div>
          <label className="block text-[11px] font-mono text-slate-400 mb-1">Stil Grubu</label>
          <input
            type="text"
            placeholder="Filtrele..."
            value={styleGroup}
            onChange={(e) => setStyleGroup(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500/50"
          />
        </div>
      </div>

      {isLoading ? (
        <LoadingState message="Müze referansları yükleniyor..." />
      ) : error ? (
        <ErrorState error={error} title="Referanslar Yüklenemedi" onRetry={refetch} />
      ) : references.length === 0 ? (
        <EmptyState
          title="Tarihsel Referans Bulunmuyor"
          description="Arama kriterlerinize uygun veya veritabanında kayıtlı bir müze referansı bulunamadı."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {references.map((refItem) => {
            return (
              <div
                key={refItem.id}
                className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 flex flex-col justify-between space-y-4 hover:border-slate-700 transition-colors shadow-lg"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-blue-400 font-bold px-2.5 py-1 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                      {refItem.reference_key}
                    </span>
                    <StatusBadge readiness={refItem.style_dna_readiness} />
                  </div>

                  <h3 className="font-bold text-lg text-slate-100">{refItem.object_title}</h3>

                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-300 bg-slate-950/60 border border-slate-800/60 rounded-xl p-3">
                    <div className="flex items-center space-x-1.5">
                      <Building2 className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                      <span className="truncate">{refItem.institution_name}</span>
                    </div>

                    <div className="flex items-center space-x-1.5">
                      <Calendar className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                      <span className="truncate">{refItem.date_display || "Tarih Belirtilmemiş"}</span>
                    </div>

                    <div className="flex items-center space-x-1.5 col-span-2">
                      <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                      <span className="truncate">{refItem.culture || refItem.dynasty_or_tradition || "Bölge/Kültür Belirtilmemiş"}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-slate-800/60">
                  <Link
                    href={`/historical-references/${refItem.reference_key}`}
                    className="text-xs text-slate-400 hover:text-slate-200 font-mono flex items-center space-x-1"
                  >
                    <span>Detayları Oku</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>

                  {targetStyleProfileId && (
                    <button
                      onClick={() => handleSelectReference(refItem.reference_key)}
                      disabled={createConnection.isPending}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-xl transition-all shadow-md shadow-blue-600/20 disabled:opacity-40"
                    >
                      {createConnection.isPending ? "Hesaplanıyor..." : "Bu Referans ile Bağlantı Kur"}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </main>
  );
}

export default function HistoricalReferencesPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header />
      <Suspense fallback={<LoadingState message="Sayfa yükleniyor..." />}>
        <HistoricalReferencesContent />
      </Suspense>
      <Footer />
    </div>
  );
}
