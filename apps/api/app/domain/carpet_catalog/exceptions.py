"""Domain exceptions for Carpet Catalog & Story Associations."""

class CarpetCatalogError(Exception):
    """Base exception for carpet catalog domain."""
    pass

class CatalogCarpetNotFoundError(CarpetCatalogError):
    """Raised when a catalog carpet is not found."""
    pass

class CatalogSkuRequiredError(CarpetCatalogError):
    """Raised when a catalog carpet lacks a valid SKU."""
    pass

class CatalogConflictError(CarpetCatalogError):
    """Raised when an imported SKU conflicts with existing different catalog content."""
    pass

class CatalogSkuConflictError(CarpetCatalogError):
    """Raised when an imported SKU conflicts with a non-catalog carpet record."""
    pass

class CatalogUnknownMotifError(CarpetCatalogError):
    """Raised when an import references a motif key that does not exist."""
    pass

class CatalogUnknownSourceError(CarpetCatalogError):
    """Raised when an import references a source key that does not exist."""
    pass

class CatalogUnknownClaimError(CarpetCatalogError):
    """Raised when an import references a story claim key that does not exist."""
    pass

class CarpetMotifSourceRequiredError(CarpetCatalogError):
    """Raised when SOURCE_DOCUMENTED evidence type has 0 sources."""
    pass

class CarpetMotifCurationNoteRequiredError(CarpetCatalogError):
    """Raised when CURATOR_CONFIRMED evidence type lacks curation_note."""
    pass

class CarpetMotifUncertaintyNoteRequiredError(CarpetCatalogError):
    """Raised when UNCERTAIN evidence type lacks uncertainty_note."""
    pass

class CarpetUncertainMotifCannotHaveStoryError(CarpetCatalogError):
    """Raised when story associations are attached to an UNCERTAIN motif association."""
    pass

class CarpetStoryMotifMismatchError(CarpetCatalogError):
    """Raised when a story claim belongs to a different motif than the carpet motif association."""
    pass

class CarpetStoryUnknownClaimNotApplicableError(CarpetCatalogError):
    """Raised when an attempt is made to attach an UNKNOWN status claim to a carpet."""
    pass

class CarpetStoryApplicabilityNoteRequiredError(CarpetCatalogError):
    """Raised when CONTEXTUAL or CONTESTED claim association lacks applicability_note."""
    pass

class CurationConflictError(CarpetCatalogError):
    """Raised when an association is imported with conflicting existing data."""
    pass

class UnsupportedSchemaVersionError(CarpetCatalogError):
    """Raised when an import file uses an unsupported schema version."""
    pass
