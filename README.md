# Carpet Style & Story Match

![License](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)

**Carpet Style & Story Match** is a modern platform that quantifies the visual character of carpets, evaluates narrative affinities with user aesthetic themes, and connects carpets to documented historical reference artifacts.

---

## Core Product Outputs

The system evaluates three independent dimensions without combining them into a single personality score:

1. **Visual Style Match**: "Is it visually close to my preferences?" (Driven by 9D Style DNA)
2. **Narrative Affinity**: "Is its story / theme meaningful to me?" (Driven by 8 Narrative Themes)
3. **Historical Connection**: "Which verified historical artifacts does this carpet connect with?"

---

## Frozen System Contracts

- **9D Style DNA**:
  - D1 `color_energy` (Renk Enerjisi)
  - D2 `color_diversity` (Renk Çeşitliliği)
  - D3 `contrast` (Kontrast)
  - D4 `warmth` (Renk Sıcaklığı)
  - D5 `visual_complexity` (Görsel Karmaşıklık)
  - D6 `structural_order` (Düzen & Simetri)
  - D7 `rhythm_repetition` (Ritim & Tekrar)
  - D8 `focal_strength` (Odak Gücü)
  - D9 `form_language` (Form Dili)

- **8 Narrative Themes**:
  - N1 `nature_growth` ( Doğa & Büyüme)
  - N2 `belonging_home` ( Aidiyet & Yuva)
  - N3 `journey_discovery` ( Yolculuk & Keşif)
  - N4 `continuity_connection` ( Süreklilik & Bağ)
  - N5 `balance_order` ( Denge & Düzen)
  - N6 `renewal_transformation` ( Yenilenme & Dönüşüm)
  - N7 `tradition_craft` ( Gelenek & Zanaat)
  - N8 `cultural_heritage` ( Kültürel Miras)

---

## Monorepo Architecture

```text
carpet-style-story-match/
├── apps/
│   ├── api/          # FastAPI Backend (Python 3.11+, SQLAlchemy 2 Async, Alembic)
│   └── web/          # Next.js 15+ Frontend (TypeScript, Tailwind CSS, TanStack Query)
├── packages/
│   └── contracts/    # Shared contract schemas and definitions
├── docs/             # Technical specifications & frozen invariants
├── docker/           # Docker service configurations
├── compose.yaml      # Docker Compose setup (PostgreSQL, API, Web)
└── Makefile          # Project workflow automation
```

---

## Quickstart

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ & npm
- Python 3.11+

### Running locally
```bash
# Start PostgreSQL, API, and Web containers
make up

# Run full project verification checks
make check
```

---

## License

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR. Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas). Details in [LICENSE](file:///c:/Users/seydieryilmaz/Desktop/carpet-style-story-match/LICENSE).
