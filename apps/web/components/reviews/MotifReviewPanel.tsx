"use client";

import { useState } from "react";
import {
  MotifReviewDetail,
  MotifReviewEvent,
  ReviewDecision,
  MotifReviewReasonCode,
  submitMotifReviewDecision,
  ReviewApiError
} from "@/lib/api/motif_review";
import Link from "next/link";
import {
  CheckCircle2,
  HelpCircle,
  XCircle,
  AlertTriangle,
  History,
  Info,
  RefreshCw,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  Eye,
  ArrowUpRight,
  ArrowLeft
} from "lucide-react";

export const CANONICAL_MOTIF_OPTIONS = [
  { key: "medallion", label: "Madalyon (medallion)" },
  { key: "mihrab", label: "Mihrap (mihrab)" },
  { key: "palmette", label: "Palmet (palmette)" },
  { key: "lotus", label: "Lotus (lotus)" },
  { key: "rosette", label: "Rozet (rosette)" },
  { key: "cloud-band", label: "Bulut Kümesi (cloud-band)" },
  { key: "scrolling-vine", label: "Kıvrımdal (scrolling-vine)" },
  { key: "geometric-star", label: "Geometrik Yıldız (geometric-star)" },
  { key: "ram-horn", label: "Koçboynuzu (ram-horn)" },
  { key: "tree-of-life", label: "Hayat Ağacı (tree-of-life)" },
  { key: "elibelinde", label: "Elibelinde (elibelinde)" },
  { key: "comb", label: "Tarak (comb)" },
  { key: "mystery-hook", label: "Çengel (mystery-hook)" }
];

export const REASON_CODE_OPTIONS: { key: MotifReviewReasonCode; label: string }[] = [
  { key: "VISUAL_MATCH_CONFIRMED", label: "Görsel eşleşme doğrulandı (VISUAL_MATCH_CONFIRMED)" },
  { key: "INSUFFICIENT_VISUAL_EVIDENCE", label: "Yetersiz görsel kanıt (INSUFFICIENT_VISUAL_EVIDENCE)" },
  { key: "AMBIGUOUS_WITH_OTHER_MOTIF", label: "Başka bir motif ile belirsiz (AMBIGUOUS_WITH_OTHER_MOTIF)" },
  { key: "REGION_INCORRECT", label: "Bölge / Bounding box hatalı (REGION_INCORRECT)" },
  { key: "ONTOLOGY_MAPPING_INCORRECT", label: "Ontoloji haritalaması hatalı (ONTOLOGY_MAPPING_INCORRECT)" },
  { key: "NOT_A_MOTIF", label: "Motif deseni değil (NOT_A_MOTIF)" },
  { key: "CROP_OR_OCCLUSION_LIMITATION", label: "Kırpma / örtüşme kısıtı (CROP_OR_OCCLUSION_LIMITATION)" },
  { key: "OTHER", label: "Diğer operasyonel neden (OTHER)" }
];

interface MotifReviewPanelProps {
  detail: MotifReviewDetail;
  history: MotifReviewEvent[];
  onRefresh: () => void;
}

export default function MotifReviewPanel({ detail, history, onRefresh }: MotifReviewPanelProps) {
  const [selectedDecision, setSelectedDecision] = useState<ReviewDecision | null>(null);
  const [selectedCanonicalKey, setSelectedCanonicalKey] = useState<string>(
    detail.proposed_canonical_motif_key || ""
  );
  const [selectedReasonCode, setSelectedReasonCode] = useState<MotifReviewReasonCode | "">("");
  const [noteText, setNoteText] = useState<string>("");
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorState, setErrorState] = useState<{ code: string; message: string } | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showHistoryModal, setShowHistoryModal] = useState<boolean>(false);

  const [imageError, setImageError] = useState<boolean>(false);

  // Parse region bounding box if available
  const region = detail.candidate_region || {};
  const box2d = Array.isArray(region.box_2d) ? (region.box_2d as number[]) : null;

  // Bounding box percentages [ymin, xmin, ymax, xmax] -> normalized 0..100 or 0..1000
  let boxStyle: React.CSSProperties | null = null;
  if (box2d && box2d.length === 4) {
    let [ymin, xmin, ymax, xmax] = box2d;
    // Normalize if scale is 0..1000
    if (ymax > 100 || xmax > 100) {
      ymin = ymin / 10;
      xmin = xmin / 10;
      ymax = ymax / 10;
      xmax = xmax / 10;
    }
    boxStyle = {
      top: `${ymin}%`,
      left: `${xmin}%`,
      height: `${ymax - ymin}%`,
      width: `${xmax - xmin}%`
    };
  }

  const handleDecisionSubmit = async () => {
    if (!selectedDecision) return;
    setErrorState(null);
    setSuccessMessage(null);

    // Validation checks
    if (selectedDecision === "CONFIRM") {
      const isUnmapped = detail.effective_status === "UNMAPPED_MOTIF_CANDIDATE" || detail.original_candidate_status === "UNMAPPED_MOTIF_CANDIDATE";
      if (isUnmapped && !selectedCanonicalKey) {
        setErrorState({
          code: "UNMAPPED_REQUIRES_REMAP",
          message: "Haritalanmamış adayları onaylamak için lütfen kanonik bir motif seçin."
        });
        return;
      }
    }

    setSubmitting(true);
    // Generate fresh idempotency key per submit attempt
    const idempotencyKey = `idemp-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

    try {
      await submitMotifReviewDecision(
        detail.review_subject_id,
        {
          decision: selectedDecision,
          selected_canonical_motif_key: selectedDecision === "CONFIRM" ? selectedCanonicalKey || null : null,
          reason_code: selectedReasonCode ? (selectedReasonCode as MotifReviewReasonCode) : null,
          note: noteText.trim() ? noteText.trim() : null,
          expected_version: detail.review_version
        },
        idempotencyKey
      );

      setSuccessMessage("İnceleme kararı başarıyla kaydedildi.");
      setSelectedDecision(null);
      setNoteText("");
      onRefresh();
    } catch (err: unknown) {
      if (err instanceof ReviewApiError) {
        setErrorState({
          code: err.code,
          message: err.message
        });
      } else {
        setErrorState({
          code: "UNKNOWN_ERROR",
          message: "Karar kaydedilirken beklenmeyen bir hata oluştu."
        });
      }
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadge = (statusStr: string) => {
    switch (statusStr) {
      case "AUTO_CONFIRMED":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 bg-blue-500/20 text-blue-300 border border-blue-500/40 rounded-full text-xs font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Otomatik Doğrulandı</span>
          </span>
        );
      case "CURATOR_CONFIRMED":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 rounded-full text-xs font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Küratör Onaylı</span>
          </span>
        );
      case "UNCERTAIN":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded-full text-xs font-semibold">
            <HelpCircle className="w-3.5 h-3.5" />
            <span>Belirsiz</span>
          </span>
        );
      case "REJECTED":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 bg-red-500/20 text-red-300 border border-red-500/40 rounded-full text-xs font-semibold">
            <XCircle className="w-3.5 h-3.5" />
            <span>Reddedildi</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 bg-purple-500/20 text-purple-300 border border-purple-500/40 rounded-full text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>İnceleme Bekliyor</span>
          </span>
        );
    }
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-6">
      {/* Top Bar / Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-bold text-white tracking-tight">
              Aday Motif: {detail.visual_candidate_key}
            </h2>
            {getStatusBadge(detail.effective_status)}
          </div>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Subject ID: {detail.review_subject_id} | Versiyon: v{detail.review_version}
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {detail.analysis_id && (
            <Link
              href={`/analysis/${detail.analysis_id}`}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded-xl text-xs font-semibold transition-all shadow-sm"
              title="Bu halının 5 kartlı analiz sonucuna dön"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Analiz Raporuna Git</span>
              <ArrowUpRight className="w-3.5 h-3.5 text-amber-400" />
            </Link>
          )}

          <button
            onClick={() => setShowHistoryModal(true)}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-xl text-xs font-medium transition-colors"
          >
            <History className="w-4 h-4 text-purple-400" />
            <span>Geçmiş ({history.length})</span>
          </button>

          <button
            onClick={onRefresh}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded-xl transition-colors"
            title="Yenile"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Image & Region Overlay */}
        <div className="space-y-4">
          <div className="relative bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden aspect-square flex items-center justify-center">
            {detail.image_url && !imageError ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={detail.image_url}
                alt={detail.visual_candidate_key}
                onError={() => setImageError(true)}
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="text-center p-6 space-y-2 text-slate-500">
                <Eye className="w-10 h-10 mx-auto text-slate-600" />
                <p className="text-xs font-mono">Görsel önizlemesi kullanılamıyor.</p>
                <p className="text-[10px] text-slate-600">Adayın bölgesel verileri ve gözlemleri aşağıda listelenmiştir.</p>
              </div>
            )}

            {/* Bounding Box Overlay */}
            {boxStyle && (
              <div
                style={boxStyle}
                className="absolute border-2 border-amber-400 bg-amber-400/10 pointer-events-none rounded-sm shadow-sm flex items-start justify-start p-1"
              >
                <span className="bg-amber-500 text-slate-950 font-mono text-[9px] font-bold px-1 rounded">
                  {detail.proposed_canonical_motif_key || detail.visual_candidate_key}
                </span>
              </div>
            )}
          </div>

          {/* Research Eligibility Banner */}
          <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl flex items-center justify-between text-xs">
            <span className="text-slate-400 font-medium">Kaynak Araştırması Durumu:</span>
            {detail.research_eligibility === "SOURCE_RESEARCH_ALLOWED" ? (
              <span className="inline-flex items-center space-x-1.5 text-emerald-400 font-bold font-mono">
                <ShieldCheck className="w-4 h-4" />
                <span>Uygun (SOURCE_RESEARCH_ALLOWED)</span>
              </span>
            ) : (
              <span className="inline-flex items-center space-x-1.5 text-slate-400 font-mono">
                <ShieldAlert className="w-4 h-4 text-amber-500" />
                <span>Kapalı (BLOCKED)</span>
              </span>
            )}
          </div>
        </div>

        {/* Right: Inspection Data & Decision Form */}
        <div className="space-y-6">
          {/* Metadata Cards */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl space-y-1">
              <span className="text-slate-400 block text-[10px] uppercase tracking-wider">AI Güveni</span>
              <span className="text-slate-100 font-mono font-bold text-sm">
                %{(detail.candidate_confidence * 100).toFixed(1)}
              </span>
            </div>

            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl space-y-1">
              <span className="text-slate-400 block text-[10px] uppercase tracking-wider">Önerilen Motif</span>
              <span className="text-amber-400 font-mono font-bold text-sm">
                {detail.proposed_canonical_motif_key || "Belirtilmedi"}
              </span>
            </div>

            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl space-y-1 col-span-2">
              <span className="text-slate-400 block text-[10px] uppercase tracking-wider">VLM Model Provenance</span>
              <div className="text-slate-300 font-mono text-[11px]">
                {String(detail.model_provenance.provider_type || "LOCAL_VLLM")} / {String(detail.model_provenance.model_id || "vllm")} (Prompt: {String(detail.model_provenance.prompt_version || "v1.2")})
              </div>
            </div>
          </div>

          {/* Visual Observations List */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-300 block">Görsel Gözlemler (Visual Evidence):</span>
            {detail.visual_evidence.length > 0 ? (
              <ul className="space-y-1 text-xs text-slate-300 bg-slate-950/40 p-3 rounded-xl border border-slate-800/80">
                {detail.visual_evidence.map((ev, i) => (
                  <li key={i} className="flex items-start space-x-2">
                    <span className="text-amber-400">•</span>
                    <span>{ev}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-500 italic">Belgelenmiş özel görsel gözlem yok.</p>
            )}
          </div>

          {/* Curator Decision Form */}
          <div className="space-y-4 pt-4 border-t border-slate-800">
            <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
              <span>Küratör Karar Formu</span>
            </h3>

            {/* Error / Conflict Alert */}
            {errorState && (
              <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl space-y-2">
                <div className="flex items-center space-x-2 text-red-400 text-xs font-bold">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>Hata: {errorState.code}</span>
                </div>
                <p className="text-xs text-red-300 leading-relaxed">{errorState.message}</p>
                {(errorState.code === "REVIEW_CONFLICT" || errorState.code === "STALE_REVIEW_SUBJECT") && (
                  <button
                    onClick={onRefresh}
                    className="inline-flex items-center space-x-2 px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-200 border border-red-500/40 rounded-lg text-xs font-semibold transition-colors mt-2"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Son Halini Görmek İçin Yenile</span>
                  </button>
                )}
              </div>
            )}

            {/* Success Message */}
            {successMessage && (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs text-emerald-300 font-semibold flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>{successMessage}</span>
                </div>
                {detail.analysis_id && (
                  <Link
                    href={`/analysis/${detail.analysis_id}`}
                    className="inline-flex items-center space-x-1 px-3 py-1 bg-emerald-500 hover:bg-emerald-400 text-slate-950 rounded-lg font-bold text-xs transition-colors self-start sm:self-auto"
                  >
                    <span>Analizi Görüntüle</span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </Link>
                )}
              </div>
            )}

            {/* Decision Action Buttons */}
            <div className="grid grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => setSelectedDecision("CONFIRM")}
                className={`py-3 px-2 rounded-xl text-xs font-bold flex flex-col items-center justify-center space-y-1 transition-all border ${
                  selectedDecision === "CONFIRM"
                    ? "bg-emerald-500 text-slate-950 border-emerald-400 shadow-lg shadow-emerald-500/20 scale-[1.02]"
                    : "bg-slate-950 hover:bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                }`}
              >
                <CheckCircle2 className="w-5 h-5" />
                <span>Doğrula (CONFIRM)</span>
              </button>

              <button
                type="button"
                onClick={() => setSelectedDecision("UNCERTAIN")}
                className={`py-3 px-2 rounded-xl text-xs font-bold flex flex-col items-center justify-center space-y-1 transition-all border ${
                  selectedDecision === "UNCERTAIN"
                    ? "bg-amber-500 text-slate-950 border-amber-400 shadow-lg shadow-amber-500/20 scale-[1.02]"
                    : "bg-slate-950 hover:bg-amber-500/10 text-amber-400 border-amber-500/30"
                }`}
              >
                <HelpCircle className="w-5 h-5" />
                <span>Belirsiz (UNCERTAIN)</span>
              </button>

              <button
                type="button"
                onClick={() => setSelectedDecision("REJECT")}
                className={`py-3 px-2 rounded-xl text-xs font-bold flex flex-col items-center justify-center space-y-1 transition-all border ${
                  selectedDecision === "REJECT"
                    ? "bg-red-500 text-slate-950 border-red-400 shadow-lg shadow-red-500/20 scale-[1.02]"
                    : "bg-slate-950 hover:bg-red-500/10 text-red-400 border-red-500/30"
                }`}
              >
                <XCircle className="w-5 h-5" />
                <span>Reddet (REJECT)</span>
              </button>
            </div>

            {/* Controlled Canonical Motif Dropdown (if CONFIRM) */}
            {selectedDecision === "CONFIRM" && (
              <div className="space-y-1 bg-emerald-500/5 border border-emerald-500/20 p-3 rounded-xl">
                <label className="text-xs font-semibold text-emerald-300 block">
                  Kanonik Motif Seçimi (Gerekli / Remap):
                </label>
                <select
                  value={selectedCanonicalKey}
                  onChange={(e) => setSelectedCanonicalKey(e.target.value)}
                  className="w-full bg-slate-950 border border-emerald-500/40 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-emerald-400"
                >
                  <option value="">-- Kanonik Motif Seçin --</option>
                  {CANONICAL_MOTIF_OPTIONS.map((opt) => (
                    <option key={opt.key} value={opt.key}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Reason Code Dropdown */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-400 block">
                Operasyonel Neden Kodu (İsteğe Bağlı):
              </label>
              <select
                value={selectedReasonCode}
                onChange={(e) => setSelectedReasonCode(e.target.value as MotifReviewReasonCode | "")}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
              >
                <option value="">-- Neden Kodu Seçilmedi --</option>
                {REASON_CODE_OPTIONS.map((opt) => (
                  <option key={opt.key} value={opt.key}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Note Input */}
            <div className="space-y-1">
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span>Küratör Notu (İsteğe Bağlı):</span>
                <span className="font-mono text-[10px] text-slate-500">{noteText.length} / 1000</span>
              </div>
              <textarea
                value={noteText}
                onChange={(e) => setNoteText(e.target.value.slice(0, 1000))}
                rows={3}
                placeholder="Görsel karara dair teknik/operasyonel açıklama..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-purple-500 resize-none"
              />
            </div>

            {/* Submit Button */}
            <button
              type="button"
              disabled={!selectedDecision || submitting}
              onClick={handleDecisionSubmit}
              className="w-full py-3 px-4 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-xs rounded-xl transition-all shadow-lg shadow-purple-600/20 flex items-center justify-center space-x-2"
            >
              {submitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Karar Kaydediliyor...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  <span>Kararı Kaydet ve Güncelle</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* History Audit Modal */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center space-x-2">
                <History className="w-5 h-5 text-purple-400" />
                <span>Denetim İzleme Geçmişi (Append-Only Audit Trail)</span>
              </h3>
              <button
                onClick={() => setShowHistoryModal(false)}
                className="text-slate-400 hover:text-white text-sm font-mono p-1"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-2">
              {history.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-xs italic">
                  Henüz kaydedilmiş bir insan inceleme olayı yok.
                </div>
              ) : (
                history.map((ev) => (
                  <div key={ev.review_id} className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-purple-400 font-bold">v{ev.version}</span>
                        {getStatusBadge(ev.resulting_status)}
                      </div>
                      <span className="text-[10px] font-mono text-slate-500">
                        {new Date(ev.created_at).toLocaleString("tr-TR")}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400 font-mono bg-slate-900/60 p-2 rounded-lg">
                      <div>İnceleyen: <span className="text-slate-200">{ev.reviewer_ref}</span></div>
                      <div>Sınır: <span className="text-slate-200">{ev.reviewer_boundary}</span></div>
                      <div>Karar: <span className="text-slate-200">{ev.decision}</span></div>
                      <div>Kanonik Key: <span className="text-amber-300">{ev.selected_canonical_motif_key || "-"}</span></div>
                    </div>

                    {ev.reason_code && (
                      <div className="text-slate-400 text-[11px]">
                        Neden Kodu: <span className="text-slate-200 font-mono">{ev.reason_code}</span>
                      </div>
                    )}

                    {ev.note && (
                      <div className="text-slate-300 italic bg-slate-900/40 p-2 rounded-lg border border-slate-800/60">
                        &quot;{ev.note}&quot;
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-between items-center text-[10px] text-slate-500 font-mono">
              <span>* Geçmiş kayıtları silinemez veya değiştirilemez.</span>
              <button
                onClick={() => setShowHistoryModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-medium text-xs transition-colors"
              >
                Kapat
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
