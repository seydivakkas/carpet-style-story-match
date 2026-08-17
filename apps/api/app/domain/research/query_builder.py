"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 Research Query Builder.
Generates neutral, provenance-safe query plans (cultural-research-query-v1.0.0)
from verified ResearchSubject instances.

SAFETY INVARIANT:
Queries MUST NEVER inject unverified cultural, religious, or dynasty assumptions.
Visual taxonomy (e.g. repeating_geometric, prayer_niche_like) MUST NOT determine research culture.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.domain.research.models import ResearchQueryPlan, ResearchSubject, RESEARCH_QUERY_PLAN_VERSION

CANONICAL_MOTIF_ACADEMIC_ALIASES: Dict[str, List[str]] = {
    "tree_of_life": [
        "tree of life motif textile",
        "hayat ağacı motifi kilim halı",
        "arbor vitae carpet design museum"
    ],
    "prayer_niche": [
        "niche motif arch textile",
        "mihrap motifi halı dokuma",
        "arch design carpet catalogue"
    ],
    "star": [
        "eight pointed star carpet motif museum",
        "sekiz köşeli yıldız motifi dokuma",
        "geometric star textile museum collection"
    ],
    "medallion": [
        "central medallion carpet textile museum",
        "göbek madalyon motifi dokuma",
        "medallion carpet scholarly catalogue"
    ],
    "palmette": [
        "palmette motif floral carpet museum",
        "palmet motifi dokuma halı",
        "lotus palmette textile catalogue"
    ],
    "ram_horn": [
        "ram horn motif textile museum",
        "koçboynuzu motifi dokuma",
        "curved horn motif carpet scholarly"
    ],
    "hands_on_hips": [
        "hands on hips motif kilim",
        "elibelinde motifi dokuma halı",
        "stylized female figure textile museum"
    ],
    "running_water": [
        "running water meander motif textile",
        "akarsu motifi dokuma halı",
        "water stream motif carpet catalogue"
    ],
    "dragon": [
        "dragon motif textile museum",
        "ejder motifi dokuma halı",
        "serpentine dragon carpet catalogue"
    ],
    "phoenix": [
        "phoenix motif textile museum",
        "zümrüdü anka simurg motifi dokuma",
        "mythical bird carpet catalogue"
    ],
    "comb": [
        "comb motif weaving textile",
        "tarak motifi dokuma halı",
        "comb motif carpet catalogue"
    ],
    "hair_band": [
        "hair band motif weaving",
        "saç bağı motifi kilim",
        "headband motif textile museum"
    ],
    "hook": [
        "latch hook motif carpet",
        "çengel motifi dokuma halı",
        "geometric hook motif catalogue"
    ]
}


class ResearchQueryBuilder:
    """Builds neutral, provenance-safe query plans for cultural evidence retrieval."""

    @classmethod
    def build_query_plan(cls, subject: ResearchSubject) -> ResearchQueryPlan:
        motif_key = subject.canonical_motif_key.lower().strip()

        queries: List[str] = []

        # 1. Neutral motif-specific queries using academic aliases
        aliases = CANONICAL_MOTIF_ACADEMIC_ALIASES.get(motif_key, [
            f"{subject.display_name} carpet motif museum",
            f"{subject.display_name} textile scholarly catalogue"
        ])
        queries.extend(aliases)

        # 2. If subject has verified external source context, append explicit context-bound query
        if subject.known_source_context:
            verified_inst = subject.known_source_context.get("institution")
            if verified_inst:
                queries.append(f"{subject.display_name} {verified_inst} catalogue")

        timestamp = datetime.now(timezone.utc).isoformat()
        plan_id = f"plan-{uuid.uuid4().hex[:8]}"

        return ResearchQueryPlan(
            query_plan_id=plan_id,
            query_plan_version=RESEARCH_QUERY_PLAN_VERSION,
            subject_id=subject.subject_id,
            canonical_motif_key=subject.canonical_motif_key,
            queries=queries,
            created_at=timestamp
        )
