"""Domain exceptions for Narrative Profile."""

class NarrativeProfileError(Exception):
    """Base exception for narrative profile domain."""
    pass

class NarrativeProfileRequiresReviewedPreferenceProfileError(NarrativeProfileError):
    """Raised when preference profile is not reviewed."""
    pass

class NarrativeProfileNotFoundError(NarrativeProfileError):
    """Raised when narrative profile is not found."""
    pass

class NarrativeProfileAlreadyExistsError(NarrativeProfileError):
    """Raised when narrative profile already exists for assessment."""
    pass

class NarrativeSelectionEmptyError(NarrativeProfileError):
    """Raised when skip=false but no themes are selected."""
    pass

class NarrativeSelectionOverlapError(NarrativeProfileError):
    """Raised when a theme is present in both primary and secondary lists."""
    pass

class NarrativeSelectionDuplicateError(NarrativeProfileError):
    """Raised when a theme is duplicated in primary or secondary lists."""
    pass

class NarrativeSelectionTooManyPrimaryError(NarrativeProfileError):
    """Raised when more than 3 primary themes are selected."""
    pass

class NarrativeSelectionTooManySecondaryError(NarrativeProfileError):
    """Raised when more than 3 secondary themes are selected."""
    pass

class NarrativeSelectionUnknownThemeError(NarrativeProfileError):
    """Raised when an unknown theme key is provided."""
    pass

class NarrativeSkipConflictError(NarrativeProfileError):
    """Raised when skip=true but themes are provided."""
    pass
