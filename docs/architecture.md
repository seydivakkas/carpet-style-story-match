# System Architecture — Carpet Style & Story Match

## Monorepo Layout

```text
carpet-style-story-match/
├── apps/
│   ├── api/                   # Backend FastAPI Application
│   │   ├── app/
│   │   │   ├── api/           # API routes & versioning (v1)
│   │   │   ├── core/          # App settings & global configs
│   │   │   ├── db/            # Database engine & Alembic migrations
│   │   │   ├── domain/        # Domain entities, value objects & frozen contracts
│   │   │   └── main.py        # FastAPI entrypoint
│   │   └── tests/             # Backend test suite (pytest)
│   │
│   └── web/                   # Frontend Next.js Application
│       ├── app/               # Next.js App Router pages
│       ├── components/        # UI components
│       ├── lib/               # API clients & utilities
│       └── package.json
│
├── packages/
│   └── contracts/             # Shared JSON schema contracts
│
├── docs/                      # Technical specifications & frozen contracts
├── docker/                    # Docker container build files
├── compose.yaml               # Orchestration file
├── Makefile                   # Developer CLI entrypoint
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Technology Stack

- **Frontend**: Next.js 15+ (App Router), TypeScript, React 19, Tailwind CSS, TanStack Query.
- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 (Async Engine with asyncpg), Alembic, Pytest.
- **Database**: PostgreSQL 16.
- **Infrastructure**: Docker & Docker Compose.

## Key Architectural Principles

1. **Clean Monorepo**: Decoupled backend and frontend services connected via REST contracts.
2. **Explicit Contracts**: All contracts are frozen and validated via unit tests.
3. **CPU-First Execution**: Core operations run without hardware dependencies. No hard requirement on GPUs or external proprietary LLMs.
4. **Honest Capabilities**: No fake scores, placeholder recommendation algorithms, or mock ratings are exposed in production endpoints.

## Multimodal Preference Pipeline

```text
TextPreferenceProfile (6 Text Cards)
          \
           ──> UserPreferenceProfile (9D D1..D9) <── User Override / Review Confirmation
          /            ├──> PreferenceConfidenceProfile (9D C1..C9) [Evidence Metric]
VisualPreferenceProfile └──> ImportanceProfile (9D W1..W9) [Explicit User Weights]
(6 Visual Stimuli)
```

- **Separation**: Preference values ($D_1 \dots D_9$) $\ne$ Confidence metrics ($C_1 \dots C_9$) $\ne$ Importance weights ($W_1 \dots W_9$).
- **Siblings**: ConfidenceProfile and ImportanceProfile are independent sibling metadata entities attached to UserPreferenceProfile.
- **Lifecycle**: `TEXT_PENDING` $\to$ `TEXT_COMPLETE` $\to$ `VISUAL_PENDING` $\to$ `VISUAL_COMPLETE` $\to$ `PROFILE_READY` $\to$ `PROFILE_REVIEWED` $\to$ `IMPORTANCE_COMPLETE`.

## Explainable Visual Style Match Pipeline

```text
UserPreferenceProfile (9D D1..D9) ─┐
                                   │
ImportanceProfile (9D W1..W9) ─────┼──► VisualStyleMatch Engine ──► VisualStyleMatchResult
                                   │     (similarity = 1 - |user - carpet|)  (score_100, label, Top Matches,
CarpetStyleProfile (9D D1..D9) ────┘                                          Main Differences)

ConfidenceProfile (9D C1..C9) ─────────► explanation metadata only (NEVER multiplied into score!)
```

- **Formula**: $\text{similarity}_i = 1 - |\text{user}_i - \text{carpet}_i|$, $\text{score} = \frac{\sum W_i \cdot \text{similarity}_i}{\sum W_i}$.
- **Invariant**: Confidence metrics are read ONLY for explanation metadata and NEVER alter match score.
- **Coverage Policy**: Minimum 6 comparable dimensions & %70 weighted coverage required for PARTIAL status; otherwise returns `NOT_AVAILABLE` with no fake score.

## User Narrative Profile Pipeline

```text
Reviewed UserPreferenceProfile
       │
       ├── ImportanceProfile (9D W1..W9) ──────► VisualStyleMatch (Visual Match Engine)
       │
       └── UserNarrativeProfile (8 Themes) ────► Future NarrativeAffinity
```

- **Explicit User Selection**: Derived ONLY from explicit user choices (`PRIMARY`, `SECONDARY`, `NOT_SELECTED`). Zero system inference!
- **Independence**: Independent of 9D preference values, confidence metrics, importance weights, and visual style match score.
- **Separate Branches**: `UserPreferenceProfile ──► VisualStyleMatch` vs `UserNarrativeProfile ──► Future NarrativeAffinity`.

## Curated Motif Story + Source Provenance Knowledge Pipeline

```text
CuratedSource (MUSEUM_CATALOG, ACADEMIC_BOOK, etc.)
       │
       ▼
Motif (Neutral Visual Description) ──────► MotifStoryClaim (DOCUMENTED, CONTEXTUAL, CONTESTED, UNKNOWN)
                                                  │
                                                  ├──► Source Links (Citation + Locator)
                                                  │
                                                  └──► Narrative Themes (Frozen N1..N8)
```

- **Separation**: Neutral Motif identity (`MotifModel`) is decoupled from Motif Story Claims (`MotifStoryClaimModel`).
- **Status Invariants**: `DOCUMENTED` ($\ge 1$ source), `CONTEXTUAL` ($\ge 1$ source + context note), `CONTESTED` ($\ge 2$ sources + contest note), `UNKNOWN` (0 claim text, 0 theme links).
- **Public API**: Read-only endpoints for motifs, claims, and sources. Knowledge curation imports use CLI script with dry-run and atomic transactions.

---

## 12. Carpet Catalog & Curated Story Associations v1 (GÖREV 11)

```text
+-------------------+       +-------------------------------+       +------------------+
|   CarpetModel     |-----> | CarpetMotifAssociationModel   |-----> |   MotifModel     |
+-------------------+       +-------------------------------+       +------------------+
  (source_type=             (CURATOR_CONFIRMED /                     (neutral visual)
   CATALOG, unique           SOURCE_DOCUMENTED /
   sku)                      UNCERTAIN)
                                           │
                                           ▼
                            +-------------------------------+       +------------------+
                            | CarpetStoryAssociationModel   |-----> |MotifStoryClaim   |
                            +-------------------------------+       +------------------+
                             (no auto-inheritance,                   (DOCUMENTED /
                              explicit link only)                     CONTEXTUAL /
                                                                      CONTESTED)
```

- **Single Entity Invariant**: Re-uses `CarpetModel` where `source_type == CATALOG` with trimmed, unique `sku` business keys.
- **Two-Layer Association Invariant**: `CarpetMotifAssociationModel` (carpet $\leftrightarrow$ motif presence) and `CarpetStoryAssociationModel` (motif association $\leftrightarrow$ claim).
- **Explicit Story Invariant**: No auto-inheritance of motif claims; every carpet story association is explicitly declared and validated.
- **Readiness State**: Side-effect-free dynamic calculation of `StyleDnaReadinessEnum` (`NO_PRIMARY_IMAGE`, `STYLE_DNA_MISSING`, `STYLE_DNA_FAILED`, `STYLE_DNA_PARTIAL`, `STYLE_DNA_COMPLETE`).
- **Read-Only API**: `/api/v1/catalog/carpets`, `/api/v1/catalog/carpets/{id}`, `/api/v1/catalog/carpets/{id}/motifs`, `/api/v1/catalog/carpets/{id}/story-associations`.

## 13. Explainable Narrative Affinity Engine v1 (GÖREV 12)

```text
+----------------------------+        +------------------------------+
| UserNarrativeProfileModel  |        | CarpetStoryAssociationModel  |
+----------------------------+        +------------------------------+
  (N1..N8 interest weights)             (Explicit story claims)
              │                                      │
              └──────────────────┬───────────────────┘
                                 ▼
               +-----------------------------------+
               |    NarrativeAffinityEngine v1     |
               +-----------------------------------+
                                 │
                                 ▼
               +-----------------------------------+
               |   NarrativeAffinityResultModel    |
               +-----------------------------------+
                 (status, level, coverage, 8 rows)
```

- **Absolute Separation**: Narrative Affinity is completely independent of Visual Style Match, Style DNA, Importance Profile, or Preference Confidence. No numeric product score or percentage is exposed.
- **Strict Input Scope**: Operates only on `UserNarrativeProfile` and catalog carpet explicit `CarpetStoryAssociation` records.
- **Categorical Output**: Categorizes affinity as `VERY_STRONG` ($\ge 0.80$), `STRONG` ($\ge 0.60$), `MODERATE` ($\ge 0.35$), or `LIMITED` ($< 0.35$).
- **Contested Policy**: `CONTESTED` claims do not enter the confirmed coverage numerator; tracked as `contested_overlap`.
- **Snapshot & Idempotency**: Persisted with SHA-256 snapshot hash `(user_narrative_profile_id, carpet_id, snapshot_hash, affinity_version)`.
- **API Endpoints**: `/api/v1/preference-assessments/{id}/narrative-affinities` (POST, GET, LIST).

## 14. Verified Historical Reference Collection v1 (GÖREV 13)

```text
+-----------------------+       +-----------------------------------+
|  CuratedSourceModel   | <──── | HistoricalReferenceSourceModel   |
+-----------------------+       +-----------------------------------+
  (MUSEUM_OBJECT /                        (PRIMARY_OBJECT_RECORD /
   ARCHIVE_RECORD)                         SUPPORTING_REFERENCE)
                                                     │
                                                     ▼
+-----------------------+ 1:1   +-----------------------------------+
|      CarpetModel      | <───> | HistoricalReferenceMetadataModel  |
+-----------------------+       +-----------------------------------+
  (source_type=                  (reference_key, institution_name,
   HISTORICAL)                    object_identifier, culture, period,
                                  dates, geography, medium, URLs)
```

- **CarpetModel Reuse**: Reuses `CarpetModel` with `source_type = HISTORICAL` for institutional historical reference objects.
- **Source-Reported Invariant**: Preserves institutional metadata without auto-normalization, period parsing, or culture guessing. `UNKNOWN REMAINS UNKNOWN`.
- **Primary Source Link Constraint**: Exactly 1 `PRIMARY_OBJECT_RECORD` link required per reference item, pointing to a `CuratedSourceModel` of type `MUSEUM_OBJECT` or `ARCHIVE_RECORD`.
- **Deterministic Importer & Dry-Run**: CLI importer script `import_historical_references.py` supporting dry-run validation, atomic transaction, idempotency, and conflict detection.
- **Side-Effect-Free Public APIs**: `/api/v1/historical-references`, `/api/v1/historical-references/{id_or_key}`, `/api/v1/meta/historical-references`.
- **Style DNA Readiness**: Shared `derive_style_dna_readiness` helper dynamically computes readiness state without side effects.

## 15. Explainable Historical Connection Engine v1 (GÖREV 14)

```text
+------------------------------+        +-----------------------------------+
|  CarpetStyleProfileModel     |        | HistoricalReferenceMetadataModel  |
|  (Catalog Target Profile)    |        | + Primary Image Style DNA Profile |
+------------------------------+        +-----------------------------------+
               │                                          │
               └────────────────────┬─────────────────────┘
                                    ▼
                 +--------------------------------------+
                 |    HistoricalConnectionEngine v1     |
                 +--------------------------------------+
                                    │
                                    ▼
                 +--------------------------------------+
                 |  HistoricalConnectionResultModel     |
                 +--------------------------------------+
                   (status, level, coverage, 9D rows)
```

- **Domain Boundaries**: Style DNA similarity comparison only. NO historical probability, authenticity scoring, or claim of attribution.
- **Strict Target Type Guard**: Target carpet must be of `source_type != HISTORICAL`. `HISTORICAL` targets are strictly rejected.
- **Unweighted Metric**: Absolute difference $\Delta_d = |v_{\text{target}, d} - v_{\text{reference}, d}|$, similarity $= 1.0 - \Delta_d$, overall similarity $= \text{mean}(\text{similarity})$.
- **Truthful Coverage Rules**: $\ge 6$ comparable dimensions required. 6–8 comparable dimensions $\to$ status `PARTIAL`. $< 6$ comparable dimensions $\to$ status `NOT_AVAILABLE`.
- **Disclaimer Enforcement**: Every API response includes a mandatory Turkish disclaimer explicitly clarifying visual similarity $\neq$ attribution/authentication.
- **API Endpoints**: `/api/v1/historical-connections` (POST, GET, LIST) and `/api/v1/meta/historical-connections`.
