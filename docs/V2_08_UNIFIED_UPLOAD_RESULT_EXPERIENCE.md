# V2-08 — Unified 5-Card User Upload Result Experience Architecture

## Executive Overview

V2-08 defines the unified 5-card presentation and orchestration layer for uploaded carpet images. It composes existing domain outputs into a single coherent, explainable user interface without introducing new inference algorithms, automatic network research, VLM fine-tuning, auto-review promotions, or database migrations.

---

## The 5 Semantic Cards

The presentation strictly exposes **five primary cards**:

1. 🎨 **Card 1: Görsel Karakter** (`VisualCharacterCard`)
   - 9D Style DNA dimensions (`style-dna-v1.0.0`) with Turkish labels and responsive Radar Chart + Accessible Table.
   - Perceptual visible color palette (`color-observation-v1.0.0`).
   - Visual composition attributes.
   - Subsection: *"Görsel Olarak Benzer Güncel Halılar"* (`CATALOG_VISUAL_RETRIEVAL` top 5).

2. 🧩 **Card 2: Motifler** (`MotifCard`)
   - AI motif candidates with bounding overlays and *"AI Güveni"* confidence indicators.
   - Controlled status badges: `AI adayı`, `İnsan incelemesi bekleniyor`, `Doğrulandı`, `Belirsiz`, `Reddedildi`.
   - *"Küratöryel doğrulama"* badge for `CURATOR_CONFIRMED` motifs.

3. 📚 **Card 3: Kültürel Bağlam** (`CulturalContextCard`)
   - Consumes ONLY `ValidatedCulturalClaim` derived from server-verified `EvidencePack`.
   - Statuses: `DOCUMENTED` (Belgelenmiş), `CONTEXTUAL` (Bağlama Bağlı), `CONTESTED` (Tartışmalı), `UNKNOWN` (Bilinmiyor).
   - Expandable source drawer with institutional locators and excerpts.
   - Gated states: `WAITING_FOR_REVIEW` (when motifs remain AI candidates) and `WAITING_FOR_RESEARCH` (when confirmed motif has no EvidencePack).

4. ✨ **Card 4: Motif Hikâyeleri** (`MotifStoryCard`)
   - Consumes ONLY `source-bound-story-v1.0.0`.
   - Structured sections with explicit citation badges.
   - Visibly flags contested or unknown narrative sections.
   - Optional secondary subsection: *"Tematik Yakınlık"* for user preference affinity.

5. 🏛️ **Card 5: Tarihsel Bağlantılar** (`HistoricalConnectionsCard`)
   - Top 5 visual historical reference matches (`HISTORICAL_VISUAL_RETRIEVAL`).
   - **Mandatory Visible Disclaimer**: *"Görsel yakınlık tarihsel köken, dönem veya özgünlük doğrulaması değildir."*
   - Source-backed museum record metadata badges (`Müze kaydı`).

---

## Safety Invariants

- **NO COMPOSITE SCORES**: Never calculate an "Overall Score", "Authenticity Score", or "Personality Score".
- **NO AUTO-RESEARCH ON RENDER**: GET/render does not call external research networks or remote APIs.
- **NO AUTO-REVIEW PROMOTION**: AI candidates (`AI_CANDIDATE`) are never automatically promoted to `CURATOR_CONFIRMED` to make cards look complete.
- **NO DB MIGRATIONS**: Alembic head remains `2026_08_17_017`.
- **READ-ONLY GET**: Unified result endpoint is read-only and idempotent.
