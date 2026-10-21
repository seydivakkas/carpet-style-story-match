import type { ProvenanceEnum, TextChoiceEnum, VisualChoiceEnum } from "./types/api";

/** Kullanıcı arayüzü için tekil kanonik sıralama (9D ve 8 tema). */
export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
export const CANONICAL_DIMENSIONS_ORDER = [
  "color_energy",
  "color_diversity",
  "contrast",
  "warmth",
  "visual_complexity",
  "structural_order",
  "rhythm_repetition",
  "focal_strength",
  "form_language"
] as const;
export const CANONICAL_NARRATIVE_THEMES_ORDER = [
  "nature_growth",
  "belonging_home",
  "journey_discovery",
  "continuity_connection",
  "balance_order",
  "renewal_transformation",
  "tradition_craft",
  "cultural_heritage"
] as const;

export const DIMENSION_DETAILS: Record<string, {code:string;label_tr:string;min_label:string;max_label:string}> = {
  color_energy: {code:"D1",label_tr:"Renk Enerjisi",min_label:"Sakin",max_label:"Canlı"},
  color_diversity: {code:"D2",label_tr:"Renk Çeşitliliği",min_label:"Sınırlı",max_label:"Zengin"},
  contrast: {code:"D3",label_tr:"Kontrast",min_label:"Yumuşak",max_label:"Güçlü"},
  warmth: {code:"D4",label_tr:"Renk Sıcaklığı",min_label:"Soğuk",max_label:"Sıcak"},
  visual_complexity: {code:"D5",label_tr:"Görsel Karmaşıklık",min_label:"Sade",max_label:"Detaylı"},
  structural_order: {code:"D6",label_tr:"Yapısal Düzen",min_label:"Serbest",max_label:"Düzenli"},
  rhythm_repetition: {code:"D7",label_tr:"Ritim ve Tekrar",min_label:"Tekil",max_label:"Tekrarlı"},
  focal_strength: {code:"D8",label_tr:"Odak Gücü",min_label:"Dağılmış",max_label:"Belirgin"},
  form_language: {code:"D9",label_tr:"Form Dili",min_label:"Geometrik",max_label:"Organik"},
};
export const NARRATIVE_THEME_DETAILS: Record<string,{code:string;label_tr:string;description:string;icon:string}> = {
  nature_growth: {code:"N1",label_tr:"Doğa ve Büyüme",description:"Doğa, çiçek ve gelişim anlatıları",icon:"◈"},
  belonging_home: {code:"N2",label_tr:"Aidiyet ve Yuva",description:"Yuva, korunma ve aidiyet anlatıları",icon:"◈"},
  journey_discovery: {code:"N3",label_tr:"Yolculuk ve Keşif",description:"Yolculuk, yön ve keşif temaları",icon:"◈"},
  continuity_connection: {code:"N4",label_tr:"Süreklilik ve Bağ",description:"Bağlar ve süreklilik temaları",icon:"◈"},
  balance_order: {code:"N5",label_tr:"Denge ve Düzen",description:"Düzen ve karşılıklı uyum temaları",icon:"◈"},
  renewal_transformation: {code:"N6",label_tr:"Yenilenme ve Dönüşüm",description:"Değişim ve yeniden başlama temaları",icon:"◈"},
  tradition_craft: {code:"N7",label_tr:"Gelenek ve Zanaat",description:"Zanaat pratiği ve gelenek aktarımı",icon:"◈"},
  cultural_heritage: {code:"N8",label_tr:"Kültürel Miras",description:"Kaynaklarla belgelenmiş kültürel miras",icon:"◈"},
};
export const TEXT_CHOICE_LABELS: Record<TextChoiceEnum,string> = {
 STRONGLY_A:"Kesinlikle A", SLIGHTLY_A:"Biraz A", NEUTRAL:"Kararsızım", SLIGHTLY_B:"Biraz B", STRONGLY_B:"Kesinlikle B"
};
export const VISUAL_CHOICE_LABELS: Record<VisualChoiceEnum,string> = {
 STRONGLY_LEFT:"Kesinlikle sol", SLIGHTLY_LEFT:"Biraz sol", NEUTRAL:"Eşit", SLIGHTLY_RIGHT:"Biraz sağ", STRONGLY_RIGHT:"Kesinlikle sağ"
};
export const PROVENANCE_LABELS: Record<ProvenanceEnum,{label_tr:string;color:string}> = {
 TEXT_ONLY:{label_tr:"Metin",color:"bg-blue-500/10 text-blue-300 border-blue-500/20"},
 VISUAL_ONLY:{label_tr:"Görsel",color:"bg-purple-500/10 text-purple-300 border-purple-500/20"},
 MULTIMODAL:{label_tr:"Çok modlu",color:"bg-emerald-500/10 text-emerald-300 border-emerald-500/20"},
 USER_OVERRIDE:{label_tr:"Kullanıcı onayı",color:"bg-amber-500/10 text-amber-300 border-amber-500/20"}
};
