"""Domain exceptions for Historical Reference Collection v1."""

class HistoricalReferenceError(Exception):
    """Base exception for historical reference domain errors."""
    pass


class HistoricalReferenceNotFoundError(HistoricalReferenceError):
    """Raised when requested historical reference record is not found."""
    pass


class HistoricalReferenceInvalidSchemaVersionError(HistoricalReferenceError):
    """Raised when import dataset schema version is unsupported."""
    pass


class HistoricalReferencePrimarySourceRequiredError(HistoricalReferenceError):
    """Raised when historical reference item lacks a PRIMARY_OBJECT_RECORD source."""
    pass


class HistoricalReferenceMultiplePrimarySourcesError(HistoricalReferenceError):
    """Raised when historical reference item has more than 1 PRIMARY_OBJECT_RECORD source."""
    pass


class HistoricalReferenceInvalidPrimarySourceTypeError(HistoricalReferenceError):
    """Raised when primary source is not of type MUSEUM_OBJECT or ARCHIVE_RECORD."""
    pass


class HistoricalReferenceUnknownSourceError(HistoricalReferenceError):
    """Raised when a referenced source_key is not found in database."""
    pass


class HistoricalReferenceIdentityRequiredError(HistoricalReferenceError):
    """Raised when required identity fields (reference_key, institution_name, object_identifier, object_title) are missing."""
    pass


class HistoricalReferenceDateRangeInvalidError(HistoricalReferenceError):
    """Raised when date_start_year > date_end_year."""
    pass


class HistoricalReferenceConflictError(HistoricalReferenceError):
    """Raised when reference_key exists with conflicting metadata or sources."""
    pass


class HistoricalReferenceObjectConflictError(HistoricalReferenceError):
    """Raised when (institution_name, object_identifier) exists under a different reference_key."""
    pass


class HistoricalReferenceInvalidCarpetSourceTypeError(HistoricalReferenceError):
    """Raised when metadata is linked to a non-HISTORICAL CarpetModel."""
    pass
