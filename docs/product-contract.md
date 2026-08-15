# Product Contract — Carpet Style & Story Match

## 1. Product Purpose

### Core Question
> "Bir halının ölçülebilir görsel karakteri, kullanıcının açıkça belirttiği estetik tercihleriyle ne kadar örtüşüyor; kaynaklandırılmış motif hikâyeleri kullanıcının ilgilendiği temalarla nasıl bağ kuruyor ve bu halı hangi doğrulanmış tarihsel örneklerle ilişkilendirilebilir?"

### Distinct Outputs
The product produces three separate outputs. They MUST NEVER be combined into a single personality score or unified scalar score:

1. **VISUAL STYLE MATCH**: *"Görsel olarak bana yakın mı?"*
   - Computed exclusively using 9D Style DNA vectors.
2. **NARRATIVE AFFINITY**: *"Hikâyesi / temaları bana yakın mı?"*
   - Computed based on user interest in documented themes.
3. **HISTORICAL CONNECTION**: *"Hangi tarihsel örneklerle ilişki kurulabilir?"*
   - Traced against verified historical museum/archive artifacts.

---

## 2. Frozen Principles & Invariants

The following invariants are canonical and immutable across all components, APIs, and future features:

1. **STYLE DNA != METADATA**
   - Style DNA measures visual form characteristics (colors, contrast, symmetry, visual density), not metadata (origin, weaver, knot count, age).
2. **PREFERENCE != IMPORTANCE**
   - A user's preference for a dimension value is distinct from how heavily they weight (importance) that dimension.
3. **CONFIDENCE != IMPORTANCE**
   - Algorithmic confidence in a visual feature measurement does not equal user importance.
4. **VISUAL MATCH != PERSONALITY**
   - Visual matching is aesthetic distance evaluation, not a psychological personality test.
5. **NARRATIVE AFFINITY != PERSONALITY**
   - Narrative affinity reflects thematic interest in stories/motifs, not personality traits.
6. **HISTORICAL CONNECTION != AUTHENTICATION**
   - Establishing historical reference connections does not constitute formal appraisal, authentication, or age certification.
7. **UNKNOWN REMAINS UNKNOWN**
   - Missing data or unverified motif origins must be explicitly reported as unknown; never filled with guesses.
8. **CONTESTED REMAINS CONTESTED**
   - Contested origin theories or symbol meanings must preserve their contested status transparently.
9. **NO INVENTED MOTIF STORY**
   - Motif stories must derive from sourced, documented literature. Never generate fictional narratives.
10. **NO PSYCHOLOGICAL PROFILING**
    - The platform strictly avoids psychological profiling, astrology, or pseudoscientific personality mapping.
11. **NO BEAUTY SCORE**
    - There is no subjective quality or "beauty" score. Evaluation is strictly comparative against explicit user preferences.
12. **GPU = OPTIONAL**
    - Core algorithmic operations, feature extractions, and scoring must run efficiently on CPU. GPU acceleration is optional.
13. **LLM = OPTIONAL**
    - System integrity and deterministic scoring must function without LLMs. LLMs may only provide auxiliary explanatory text formatting.
14. **EXPLANATIONS MUST BE TRACEABLE TO COMPUTED OR SOURCED EVIDENCE**
    - Every explanation or score breakdown must trace directly back to computed Style DNA distances or referenced literature sources.
