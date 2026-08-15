"""Exceptions for Narrative Affinity v1."""

class NarrativeAffinityError(Exception):
    """Base exception for narrative affinity domain errors."""
    pass


class NarrativeProfileNotFoundError(NarrativeAffinityError):
    """Raised when UserNarrativeProfile is missing for assessment."""
    pass


class NarrativeAffinityCarpetNotFoundError(NarrativeAffinityError):
    """Raised when requested carpet is not found in database."""
    pass


class NarrativeAffinityRequiresCatalogCarpetError(NarrativeAffinityError):
    """Raised when requested carpet is not a CATALOG source_type carpet."""
    pass


class NarrativeAffinityNotFoundError(NarrativeAffinityError):
    """Raised when requested NarrativeAffinityResult is not found."""
    pass


class NarrativeAffinityInputInvalidError(NarrativeAffinityError):
    """Raised when input validation fails."""
    pass
