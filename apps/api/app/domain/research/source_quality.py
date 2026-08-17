"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 Source Quality Filter Implementation.
Evaluates source institutions, publication types, and canonical URLs against
source-quality-policy-v1.0.0.
"""
from urllib.parse import urlparse
from typing import Dict, Any, Tuple
from app.domain.research.models import SourceTier

REJECTED_DOMAINS = {
    "pinterest.com", "www.pinterest.com", "tr.pinterest.com",
    "instagram.com", "www.instagram.com",
    "facebook.com", "www.facebook.com",
    "etsy.com", "www.etsy.com",
    "ebay.com", "www.ebay.com",
    "amazon.com", "www.amazon.com", "amazon.com.tr",
    "merinos.com.tr", "www.merinos.com.tr",
    "dinarsu.com.tr", "www.dinarsu.com.tr"
}

TIER_1_DOMAINS = {
    "metmuseum.org", "www.metmuseum.org",
    "vam.ac.uk", "www.vam.ac.uk",
    "britishmuseum.org", "www.britishmuseum.org",
    "louvre.fr", "www.louvre.fr",
    "smb.museum", "www.smb.museum",
    "ktb.gov.tr", "www.ktb.gov.tr",
    "yok.gov.tr", "dergipark.org.tr"
}


class SourceQualityFilter:
    """Evaluates cultural source credibility against source-quality-policy-v1.0.0."""

    @classmethod
    def evaluate_source(
        self,
        canonical_url: str,
        institution_or_publisher: str,
        source_type: str
    ) -> Tuple[SourceTier, str]:
        """Returns (SourceTier, evaluation_reason)."""
        parsed = urlparse(canonical_url.lower())
        domain = parsed.netloc.lower()

        # 1. Check Explicit Rejections
        for rej in REJECTED_DOMAINS:
            if domain == rej or domain.endswith("." + rej):
                if "merinos" in domain or "dinarsu" in domain:
                    return SourceTier.REJECTED_SOURCE, f"Commercial manufacturer product site '{domain}' is not an authoritative cultural symbolism source."
                return SourceTier.REJECTED_SOURCE, f"Domain '{domain}' is in rejected sources policy."

        st_lower = source_type.lower()
        inst_lower = institution_or_publisher.lower()

        # 2. Check Tier 1 Primary Institutional
        for t1 in TIER_1_DOMAINS:
            if domain == t1 or domain.endswith("." + t1):
                return SourceTier.TIER_1_PRIMARY_INSTITUTIONAL, f"Institutional primary domain '{domain}'."

        if domain.endswith(".edu") or domain.endswith(".edu.tr") or domain.endswith(".gov") or domain.endswith(".gov.tr"):
            return SourceTier.TIER_1_PRIMARY_INSTITUTIONAL, f"Academic or government TLD '{domain}'."

        if "museum" in inst_lower or "müze" in inst_lower or "ministry" in inst_lower or "bakanlık" in inst_lower or st_lower in {"museum_object", "museum_catalogue"}:
            return SourceTier.TIER_1_PRIMARY_INSTITUTIONAL, f"Recognized institutional publisher '{institution_or_publisher}'."

        # 3. Check Tier 2 Scholarly
        if st_lower in {"academic_journal", "monograph", "scholarly_book", "peer_reviewed_paper", "scholarly_publication"}:
            return SourceTier.TIER_2_SCHOLARLY, f"Scholarly publication type '{source_type}'."

        if "university" in inst_lower or "üniversite" in inst_lower or "press" in inst_lower or "yayınları" in inst_lower:
            return SourceTier.TIER_2_SCHOLARLY, f"Academic publisher '{institution_or_publisher}'."

        # 4. Check Tier 3 Reputable Secondary
        if st_lower in {"cultural_archive", "reference_work", "encyclopedia", "heritage_catalog"}:
            return SourceTier.TIER_3_REPUTABLE_SECONDARY, f"Established heritage reference type '{source_type}'."

        # Default to Tier 3 if valid URL and non-commercial publisher, else Reject
        if canonical_url.startswith("http://") or canonical_url.startswith("https://") or canonical_url.startswith("file://") or canonical_url.startswith("curated://"):
            return SourceTier.TIER_3_REPUTABLE_SECONDARY, "Secondary cultural reference source."

        return SourceTier.REJECTED_SOURCE, "Source fails quality and verification guidelines."
