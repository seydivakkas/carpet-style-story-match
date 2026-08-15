# FRONTEND PRODUCT EXPERIENCE v1 SPECIFICATION

**ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR**  
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

---

## 1. Overview

`frontend-experience-v1` provides a Next.js 15 (App Router), React 19, TypeScript, TanStack Query, and Tailwind CSS Web Client for the **Carpet Style & Story Match** platform.

The frontend exposes three independent, un-combined product result axes:

1. **Görsel Stil Uyumu** (Visual Style Match — 9D Style DNA)
2. **Anlatı Yakınlığı** (Narrative Affinity — 8 Cultural Themes)
3. **Tarihsel Bağlantı** (Historical Connection — Verified Museum References)

---

## 2. Core Principles & Constraints

1. **No Combined Score / Overall Percentage**:
   - The UI never combines visual style score (0..100), narrative affinity level (categorical), and historical connection score (0..100) into a single composite percentage or total match score.
   - Each axis is presented as an independent evaluation panel.

2. **No Personality Language**:
   - Strictly avoids terms such as "kişilik testi", "karakter analizi", "personality match", or "ruh eşiniz".
   - Uses grounded terminology: "görsel tercih", "estetik eğilim", "anlatı ilgisi", "tarihsel referans yakınlığı".

3. **Truthful Data & Empty States**:
   - No mock catalog items or fake frontend numbers in production code.
   - Displays truthful empty states when database catalog or historical reference list is empty.

4. **URL-Backed Workflow State**:
   - Assessment ID is embedded in the URL path (`/assessment/[id]/...`) to allow browser refresh and state preservation.

5. **Non-Attribution Disclaimers**:
   - Every historical reference view and pairwise historical connection analysis displays a mandatory disclaimer banner:
     > "Bu sonuç yalnız ölçülen görsel Style DNA yakınlığını gösterir. Hedef halının kültürünü, dönemini, hanedanını, atölyesini veya özgünlüğünü doğrulamaz."

---

## 3. Route Inventory

| Path | Purpose | Key Components |
| font-mono | | |
| `/` | Platform overview, 3 independent axes introduction, CTAs | `Header`, `Footer` |
| `/assessment/new` | Start new assessment, creates ID via API | `useCreateAssessment` |
| `/assessment/[id]/text` | Step 1: 6 open-ended text preferences | `ProgressSteps`, `useTextQuestionsMeta`, `useSaveTextResponse` |
| `/assessment/[id]/visual` | Step 2: 6 visual controlled A/B presentations | `ProgressSteps`, `useStartVisualPhase`, `useSaveVisualResponse` |
| `/assessment/[id]/profile` | Step 3: Multimodal 9D profile review & slider overrides | `ProgressSteps`, `DimensionBar`, `useOverrideDimension`, `useConfirmProfile` |
| `/assessment/[id]/importance` | Step 4: Importance (max 3 priority, max 3 flexible) | `ProgressSteps`, `useCreateImportanceProfile` |
| `/assessment/[id]/narrative` | Step 5: Cultural motif themes (primary, secondary) | `ProgressSteps`, `useCreateNarrativeProfile` |
| `/assessment/[id]/complete` | Step 6: Completion summary & catalog CTAs | `ProgressSteps` |
| `/catalog` | Catalog carpets list & filters | `useCatalogCarpets`, `StatusBadge` |
| `/catalog/[idOrSku]` | Catalog item details & 3 independent match calculations | `useCatalogCarpet`, `useCreateStyleMatch`, `useCreateNarrativeAffinity` |
| `/historical-references` | Verified museum reference collection list & filters | `useHistoricalReferences`, `DisclaimerBanner` |
| `/historical-references/[idOrKey]` | Single historical reference detail | `useHistoricalReference`, `DisclaimerBanner` |
| `/historical-connections/[connectionId]` | Pairwise historical connection 9D breakdown | `useHistoricalConnection`, `DisclaimerBanner` |

---

## 4. API Integration Layer

- **Typed Client**: `apps/web/lib/api/client.ts` wraps fetch requests with backend error parsing (`ApiClientError`).
- **TanStack Query Hooks**:
  - `lib/api/preferences.ts`: Assessment state machine, text/visual phases, profile build, overrides, importance, narrative selection.
  - `lib/api/catalog.ts`: Catalog retrieval, pairwise style match, pairwise narrative affinity.
  - `lib/api/historical.ts`: Historical reference retrieval, pairwise historical connection creation and breakdown retrieval.

---

## 5. Quality Assurance & Verification

- **TypeScript Type Safety**: 100% strict typed schemas matching OpenAPI backend contracts.
- **Tailwind CSS Styling**: Curated dark theme palette using HSL-tailored slate, amber, emerald, and blue tones.
