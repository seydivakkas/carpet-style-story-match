"""Domain exceptions for Historical Connection Engine v1."""

class HistoricalConnectionError(Exception):
    """Base exception for historical connection domain errors."""
    pass


class HistoricalConnectionNotFoundError(HistoricalConnectionError):
    """Raised when requested historical connection result record is not found."""
    pass


class HistoricalConnectionTargetProfileNotFoundError(HistoricalConnectionError):
    """Raised when target Style DNA profile is not found in database."""
    pass


class HistoricalConnectionTargetProfileFailedError(HistoricalConnectionError):
    """Raised when target Style DNA profile status is FAILED."""
    pass


class HistoricalConnectionInvalidTargetTypeError(HistoricalConnectionError):
    """Raised when target carpet source_type is HISTORICAL."""
    pass


class HistoricalConnectionReferenceNotFoundError(HistoricalConnectionError):
    """Raised when historical reference record is not found."""
    pass


class HistoricalConnectionReferenceImageRequiredError(HistoricalConnectionError):
    """Raised when historical reference lacks a local primary CarpetImage."""
    pass


class HistoricalConnectionReferenceProfileRequiredError(HistoricalConnectionError):
    """Raised when historical reference local primary image lacks a current Style DNA profile."""
    pass


class HistoricalConnectionReferenceProfileFailedError(HistoricalConnectionError):
    """Raised when historical reference Style DNA profile status is FAILED."""
    pass


class HistoricalConnectionStyleVersionMismatchError(HistoricalConnectionError):
    """Raised when target and reference Style DNA profile algorithm versions differ."""
    pass


class HistoricalConnectionInputInvalidError(HistoricalConnectionError):
    """Raised when input parameters are invalid."""
    pass
