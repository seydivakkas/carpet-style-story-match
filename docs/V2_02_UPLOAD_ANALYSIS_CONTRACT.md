# V2-02 User Upload Analysis Contract & Motif Ontology Architecture

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
```

## 1. Frozen Invariants & Core Principles

The complete V2 evidence pipeline follows a strict, non-negotiable unidirectional chain:

```
PIXEL
  ↓
VISUAL OBSERVATION
  ↓
MOTIF CANDIDATE
  ↓
HUMAN / RULED VERIFICATION
  ↓
SOURCE RESEARCH
  ↓
CULTURAL CLAIM
  ↓
STORY PRESENTATION
```

### Frozen Principles
- **PIXEL != CULTURAL CLAIM**
- **MOTIF CANDIDATE != VERIFIED MOTIF**
- **CONFIDENCE != CURATOR CONFIRMATION**
- **VISUAL SIMILARITY != ORIGIN**
- **VISUAL CATEGORY != HISTORICAL PERIOD**
- **VISUAL CATEGORY != DYNASTY**
- **HIGH CONFIDENCE != HISTORICAL TRUTH**
- **GEOMETRIC != SELJUK**
- **FLORAL != SAFAVID**
- **PRAYER_NICHE_LIKE != PRAYER RUG / NAMAZ HALISI**
- **TREE_LIKE_FORM != TREE OF LIFE**
- **HORN_LIKE_FORM != RAM'S HORN**
- **HUMAN_LIKE_GEOMETRIC_FORM != ELİBELİNDE**
- **UNKNOWN REMAINS UNKNOWN**
- **UNCERTAIN REMAINS UNCERTAIN**

No cultural meaning, historical origin, dynasty, symbolism, or story may EVER be inferred directly from pixels by an AI model.

---

## 2. Contract Versioning
- **Upload Analysis Contract Schema**: `upload-analysis-v1.0.0`
- **Visual Category Taxonomy**: `visual-category-taxonomy-v1.0.0`
- **Motif Ontology**: `motif-ontology-v1.0.0`

---

## 3. Allowed Visual Evidence vs Forbidden Cultural Inference

### Allowed Visual Evidence
- Purely geometric observations (e.g. "central radial medallion structure", "8-pointed star form", "repeating diamond lattice").
- Regional coordinates and bounding boxes in normalized `[0,1] x [0,1]` canonical space.
- Composition metrics (symmetry, repetition strength, focal strength).
- Visual candidate keys (e.g. `medallion_like`, `niche_like`, `star_like`, `tree_like`).
- Model provenance (model ID, prompt version, inference timestamp).
- Explicit abstentions (`CROPPED_REGION`, `OCCLUDED_REGION`, `MOTIF_VISUALLY_AMBIGUOUS`).

### Forbidden Fields (Strict Pydantic Rejection)
The contract strictly forbids and rejects:
`culture`, `cultural_origin`, `dynasty`, `historical_period`, `symbolism`, `meaning`, `story`, `personality`, `ethnicity`, `religion`, `authentication`, `authenticated_origin`, `verified_period`, `verified_culture`, `predicted_brand`, `predicted_collection`.

---

## 4. Visual Category Taxonomy (11 Categories)

1. `central_medallion` ("Merkezi Madalyonlu")
2. `all_over` ("Tüm Yüzeye Dağılan")
3. `prayer_niche_like` ("Mihrap/Niş Benzeri Kompozisyon") — *Purely visual geometry; never implies religious usage or 'prayer rug'.*
4. `panel_layout` ("Panelli Kompozisyon")
5. `lattice` ("Kafes / Izgara Düzeni")
6. `repeating_geometric` ("Tekrarlı Geometrik")
7. `repeating_floral` ("Tekrarlı Bitkisel")
8. `border_dominant` ("Bordür Ağırlıklı")
9. `minimal_contemporary` ("Minimal / Çağdaş")
10. `mixed` ("Karma")
11. `unknown` ("Güvenle Sınıflandırılamadı")

---

## 5. Two-Layer Motif Mapping

1. **Visual Motif Candidate (Pixel Layer)**: Visually descriptive candidate key detected from pixel features (e.g. `tree_like`, `niche_like`, `horn_like`).
2. **Proposed Canonical Motif (Ontology Layer)**: Optional mapping proposal to the 13 canonical production motifs.

Detection modes:
- `VISUAL_DIRECT`: High-confidence geometric matches (e.g. `geometric-star`, `rosette`).
- `REVIEW_REQUIRED_SEMANTIC`: Culturally loaded motifs (e.g. `mihrab`, `tree-of-life`, `elibelinde`, `ram-horn`). Model predictions default to status `AI_CANDIDATE` and require human/ruled verification before confirmation.

Model-originated predictions can NEVER set status to `CURATOR_CONFIRMED`.

---

## 6. Abstention & Null Semantics
- `AnalysisAbstention` handles quality issues, occlusion, cropping, or visual ambiguity.
- `CROPPED_REGION` or `OCCLUDED_REGION` abstention MUST NOT generate an absence claim (`motif_absent = true`).
- `unknown` category is a valid successful result.

---

## 7. Machine-Readable Artifacts
- Taxonomy: `data/taxonomies/visual-category-taxonomy-v1.json`
- Ontology: `data/taxonomies/motif-ontology-v1.json`
- JSON Schema: `data/schemas/upload-analysis-v1.schema.json`

---

## 8. API Endpoints
- `GET /api/v1/taxonomies/visual-categories`
- `GET /api/v1/taxonomies/motifs`
- `GET /api/v1/upload-analysis/schema`
