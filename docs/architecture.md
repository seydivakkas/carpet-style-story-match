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
