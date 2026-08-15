"""Domain exceptions for Visual Style Match Engine."""

class StyleMatchError(Exception):
    """Base exception for style match errors."""
    def __init__(self, message: str, code: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

class StyleMatchRequiresImportanceCompleteError(StyleMatchError):
    def __init__(self, message: str = "Assessment importance profile must be complete to compute style match."):
        super().__init__(
            message=message,
            code="STYLE_MATCH_REQUIRES_IMPORTANCE_COMPLETE",
            status_code=409
        )

class StyleMatchPreferenceProfileNotFoundError(StyleMatchError):
    def __init__(self, message: str = "Reviewed user preference profile not found for assessment."):
        super().__init__(
            message=message,
            code="STYLE_MATCH_PREFERENCE_PROFILE_NOT_FOUND",
            status_code=404
        )

class StyleMatchImportanceProfileNotFoundError(StyleMatchError):
    def __init__(self, message: str = "Importance profile not found for assessment."):
        super().__init__(
            message=message,
            code="STYLE_MATCH_IMPORTANCE_PROFILE_NOT_FOUND",
            status_code=404
        )

class StyleMatchCarpetProfileNotFoundError(StyleMatchError):
    def __init__(self, message: str = "Carpet style profile not found."):
        super().__init__(
            message=message,
            code="STYLE_MATCH_CARPET_PROFILE_NOT_FOUND",
            status_code=404
        )

class StyleMatchCarpetProfileFailedError(StyleMatchError):
    def __init__(self, message: str = "Cannot compute style match against a failed carpet style profile."):
        super().__init__(
            message=message,
            code="STYLE_MATCH_CARPET_PROFILE_FAILED",
            status_code=409
        )

class StyleMatchNotFoundError(StyleMatchError):
    def __init__(self, message: str = "Visual style match result not found."):
        super().__init__(
            message=message,
            code="STYLE_MATCH_NOT_FOUND",
            status_code=404
        )
