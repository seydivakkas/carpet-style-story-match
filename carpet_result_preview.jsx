import React, { useState, useEffect } from "react";
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer,
} from "recharts";

/* ---------------------------------------------------------
   ÖRNEK VERİ — dokümandaki "Bölüm 16: Gerçek Bir Halı Senaryosu"
   senaryosuna dayanır. Backend henüz bağlı değil; bu değerler
   arayüzün nasıl doleceğini göstermek için elle yazılmıştır.
--------------------------------------------------------- */
const ANALYSIS = {
  id: "7c1e-90af-4b3d",
  createdAt: "19 Ağustos 2026, 14:22",
  status: "COMPLETED",
  styleDNA: [
    { code: "D1", label: "Renk Enerjisi", value: 0.88 },
    { code: "D2", label: "Renk Çeşitliliği", value: 0.62 },
    { code: "D3", label: "Kontrast", value: 0.71 },
    { code: "D4", label: "Sıcaklık", value: 0.95 },
    { code: "D5", label: "Görsel Karmaşıklık", value: 0.68 },
    { code: "D6", label: "Yapısal Düzen", value: 0.81 },
    { code: "D7", label: "Ritim / Tekrar", value: 0.74 },
    { code: "D8", label: "Odak Gücü", value: 0.86 },
    { code: "D9", label: "Form Dili", value: 0.34 },
  ],
  colors: [
    { hex: "#C81E1E", label: "Yakut kırmızısı tonu", pct: 52 },
    { hex: "#F5F5DC", label: "Fildişi krem tonu", pct: 28 },
    { hex: "#1E293B", label: "Çivit mavisi tonu", pct: 12 },
    { hex: "#B8923D", label: "Hardal altını tonu", pct: 8 },
  ],
  motif: {
    descriptor: "star_like",
    trLabel: "Yıldız Motifi",
    confidence: 0.91,
    bbox: [0.2, 0.3, 0.7, 0.8],
    status: "CURATOR_CONFIRMED",
  },
  culturalContext: {
    status: "DOCUMENTED",
    claim:
      "Yıldız formu, Anadolu dokuma geleneğinde tekrar eden geometrik bir düzenleyici motif olarak, yön bulma ve gökyüzü sembolizmiyle ilişkilendirilen kompozisyonlarda sıklıkla merkez veya köşe unsuru olarak kullanılmıştır.",
    source: "Met Museum, İslam Sanatı Koleksiyonu (örnek referans)",
  },
  motifStory: {
    paragraphs: [
      "Yıldız motifinin merkezi konumu, halının genel kompozisyonunda gözü önce ortaya, sonra dışa doğru yayılan çerçeve desenlerine yönlendiren klasik bir düzenleme stratejisidir.",
      "Bu düzenleme, 15-17. yüzyıl Anadolu halılarında madalyon-merkez geleneğinin bir varyasyonu olarak okunabilir; kırmızı zemin üzerine oturan geometrik form, dönemin saray ve pazar üretimi arasındaki ortak dağarcığı yansıtır.",
    ],
    source: "Kaynak: Müzebilimsel Hakikat Matrisi (örnek anlatı)",
  },
  historicalMatch: {
    name: "16. Yüzyıl Uşak Halısı (örnek)",
    museum: "Metropolitan Museum of Art",
    proximity: 89.4,
    note: "Bu eşleşme yalnızca görsel form ve renk yakınlığını ifade eder; köken veya tarihlendirme iddiası içermez.",
  },
};

const wrap = {
  fontFamily: "'IBM Plex Sans', sans-serif",
  background: "#F3ECDD",
  color: "#211C18",
  minHeight: "100%",
  padding: "0",
};

function useReveal(delay = 0) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setShow(true), delay);
    return () => clearTimeout(t);
  }, [delay]);
  return show;
}

function CardShell({ roman, title, subtitle, children, delay }) {
  const show = useReveal(delay);
  return (
    <section
      style={{
        display: "flex",
        border: "1px solid rgba(33,28,24,0.14)",
        background: "#FBF7EE",
        borderRadius: 3,
        overflow: "hidden",
        marginBottom: 22,
        opacity: show ? 1 : 0,
        transform: show ? "translateY(0)" : "translateY(10px)",
        transition: "opacity 0.5s ease, transform 0.5s ease",
        boxShadow: "0 1px 0 rgba(33,28,24,0.06)",
      }}
    >
      <div
        style={{
          width: 56,
          flexShrink: 0,
          background: "#263454",
          color: "#F3ECDD",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "'Fraunces', serif",
          fontSize: 22,
          letterSpacing: 1,
        }}
      >
        {roman}
      </div>
      <div style={{ flex: 1, padding: "22px 26px" }}>
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              fontFamily: "'Fraunces', serif",
              fontSize: 22,
              fontWeight: 600,
              color: "#211C18",
            }}
          >
            {title}
          </div>
          {subtitle && (
            <div
              style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 11,
                letterSpacing: 0.6,
                textTransform: "uppercase",
                color: "#A63025",
                marginTop: 4,
              }}
            >
              {subtitle}
            </div>
          )}
        </div>
        {children}
      </div>
    </section>
  );
}

function StatusTag({ text, tone = "gold" }) {
  const palette = {
    gold: { bg: "#F1E4C3", fg: "#7A5E1E", border: "#B8923D" },
    red: { bg: "#F3DAD6", fg: "#7A2A20", border: "#A63025" },
    indigo: { bg: "#DDE2EC", fg: "#263454", border: "#263454" },
  }[tone];
  return (
    <span
      style={{
        display: "inline-block",
        fontFamily: "'IBM Plex Mono', monospace",
        fontSize: 11,
        padding: "3px 9px",
        borderRadius: 20,
        background: palette.bg,
        color: palette.fg,
        border: `1px solid ${palette.border}`,
        letterSpacing: 0.4,
      }}
    >
      {text}
    </span>
  );
}

export default function CarpetResultPreview() {
  return (
    <div style={wrap}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
      `}</style>

      {/* ÜST BAŞLIK / DOSYA ETİKETİ */}
      <div
        style={{
          borderBottom: "1px solid rgba(33,28,24,0.16)",
          padding: "26px 26px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div>
          <div
            style={{
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: 11,
              letterSpacing: 1,
              textTransform: "uppercase",
              color: "#A63025",
              marginBottom: 6,
            }}
          >
            Carpet Style &amp; Story Match — Analiz Dosyası
          </div>
          <h1
            style={{
              fontFamily: "'Fraunces', serif",
              fontSize: 32,
              fontWeight: 700,
              margin: 0,
              lineHeight: 1.15,
            }}
          >
            5 Kartlık Analiz Sonucu
          </h1>
        </div>
        <div
          style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 12,
            color: "#5A5148",
            textAlign: "right",
          }}
        >
          <div>ID: {ANALYSIS.id}</div>
          <div>{ANALYSIS.createdAt}</div>
          <div style={{ marginTop: 4 }}>
            <StatusTag text={ANALYSIS.status} tone="indigo" />
          </div>
        </div>
      </div>

      <div style={{ padding: "26px", maxWidth: 980, margin: "0 auto" }}>
        <p
          style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 12,
            color: "#7A6F5E",
            marginTop: 0,
            marginBottom: 24,
          }}
        >
          Not: Aşağıdaki değerler, dokümandaki "kırmızı ağırlıklı, geometrik desenli halı" senaryosuna dayanan
          örnek çıktıdır — canlı VLM / DB bağlantısı olmadan arayüzün nasıl dolacağını göstermek içindir.
        </p>

        {/* KART I — GÖRSEL KARAKTER */}
        <CardShell roman="I" title="Görsel Karakter" subtitle="Style DNA · 9 Boyutlu Vektör" delay={0}>
          <div style={{ display: "flex", gap: 28, flexWrap: "wrap" }}>
            <div style={{ width: 260, height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={ANALYSIS.styleDNA} outerRadius="75%">
                  <PolarGrid stroke="rgba(38,52,84,0.25)" />
                  <PolarAngleAxis
                    dataKey="code"
                    tick={{ fill: "#211C18", fontSize: 11, fontFamily: "IBM Plex Mono" }}
                  />
                  <Radar
                    dataKey="value"
                    stroke="#A63025"
                    fill="#A63025"
                    fillOpacity={0.28}
                    strokeWidth={2}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <div style={{ flex: 1, minWidth: 240 }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <tbody>
                  {ANALYSIS.styleDNA.map((d) => (
                    <tr key={d.code} style={{ borderBottom: "1px solid rgba(33,28,24,0.08)" }}>
                      <td style={{ padding: "5px 0", color: "#5A5148", width: 34 }}>{d.code}</td>
                      <td style={{ padding: "5px 0" }}>{d.label}</td>
                      <td
                        style={{
                          padding: "5px 0",
                          textAlign: "right",
                          fontFamily: "'IBM Plex Mono', monospace",
                          color: "#A63025",
                        }}
                      >
                        {d.value.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div style={{ marginTop: 20 }}>
            <div style={{ fontSize: 12, color: "#5A5148", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>
              Baskın Renkler
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              {ANALYSIS.colors.map((c) => (
                <div key={c.hex} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
                  <span
                    style={{
                      width: 22, height: 22, borderRadius: 4, background: c.hex,
                      border: "1px solid rgba(33,28,24,0.2)", display: "inline-block",
                    }}
                  />
                  <span>
                    {c.label} <span style={{ color: "#A63025", fontFamily: "'IBM Plex Mono', monospace" }}>%{c.pct}</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </CardShell>

        {/* KART II — MOTİFLER */}
        <CardShell roman="II" title="Motifler" subtitle="VLM Tespiti · Bounding Box" delay={120}>
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "center" }}>
            <div
              style={{
                width: 220, height: 180, position: "relative", borderRadius: 4,
                background:
                  "repeating-linear-gradient(45deg, #C81E1E 0 10px, #B8923D 10px 12px, #1E293B 12px 22px, #F5F5DC 22px 24px)",
                border: "1px solid rgba(33,28,24,0.15)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  left: `${ANALYSIS.motif.bbox[0] * 100}%`,
                  top: `${ANALYSIS.motif.bbox[1] * 100}%`,
                  width: `${(ANALYSIS.motif.bbox[2] - ANALYSIS.motif.bbox[0]) * 100}%`,
                  height: `${(ANALYSIS.motif.bbox[3] - ANALYSIS.motif.bbox[1]) * 100}%`,
                  border: "2px solid #F3ECDD",
                  boxShadow: "0 0 0 1px #211C18",
                }}
              />
              <span
                style={{
                  position: "absolute", bottom: 4, left: 4, fontSize: 10,
                  fontFamily: "'IBM Plex Mono', monospace", color: "#F3ECDD",
                  background: "rgba(33,28,24,0.55)", padding: "1px 5px", borderRadius: 2,
                }}
              >
                temsili desen
              </span>
            </div>
            <div>
              <div style={{ fontFamily: "'Fraunces', serif", fontSize: 20, marginBottom: 6 }}>
                {ANALYSIS.motif.trLabel}
              </div>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: "#5A5148", marginBottom: 10 }}>
                descriptor: {ANALYSIS.motif.descriptor} · confidence: {ANALYSIS.motif.confidence}
              </div>
              <StatusTag
                text={ANALYSIS.motif.status === "CURATOR_CONFIRMED" ? "KÜRATÖR ONAYLI" : "İNCELEME BEKLİYOR"}
                tone={ANALYSIS.motif.status === "CURATOR_CONFIRMED" ? "gold" : "red"}
              />
            </div>
          </div>
        </CardShell>

        {/* KART III — KÜLTÜREL BAĞLAM */}
        <CardShell roman="III" title="Kültürel Bağlam" subtitle="Müzebilimsel Hakikat Matrisi" delay={240}>
          <div style={{ marginBottom: 10 }}>
            <StatusTag text={ANALYSIS.culturalContext.status} tone="indigo" />
          </div>
          <p style={{ fontSize: 14, lineHeight: 1.6, margin: "10px 0" }}>
            {ANALYSIS.culturalContext.claim}
          </p>
          <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#7A6F5E" }}>
            {ANALYSIS.culturalContext.source}
          </div>
        </CardShell>

        {/* KART IV — MOTİF HİKÂYELERİ */}
        <CardShell roman="IV" title="Motif Hikâyeleri" subtitle="Kaynak Bağlantılı Anlatı" delay={360}>
          {ANALYSIS.motifStory.paragraphs.map((p, i) => (
            <p key={i} style={{ fontSize: 14, lineHeight: 1.7, margin: "0 0 10px" }}>
              {p}
            </p>
          ))}
          <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#7A6F5E" }}>
            {ANALYSIS.motifStory.source}
          </div>
        </CardShell>

        {/* KART V — TARİHSEL BAĞLANTILAR */}
        <CardShell roman="V" title="Tarihsel Bağlantılar" subtitle="9D Öklid Mesafesi · Met &amp; V&amp;A" delay={480}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16 }}>
            <div>
              <div style={{ fontFamily: "'Fraunces', serif", fontSize: 18 }}>
                {ANALYSIS.historicalMatch.name}
              </div>
              <div style={{ fontSize: 12, color: "#5A5148", marginTop: 2 }}>
                {ANALYSIS.historicalMatch.museum}
              </div>
            </div>
            <div
              style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 28,
                color: "#A63025",
                border: "1px solid #B8923D",
                borderRadius: 40,
                padding: "6px 18px",
              }}
            >
              %{ANALYSIS.historicalMatch.proximity}
            </div>
          </div>
          <p style={{ fontSize: 12, color: "#7A6F5E", marginTop: 14, lineHeight: 1.6 }}>
            {ANALYSIS.historicalMatch.note}
          </p>
        </CardShell>
      </div>
    </div>
  );
}
