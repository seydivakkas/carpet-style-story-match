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
