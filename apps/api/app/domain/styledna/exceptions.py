import uuid

class StyleDNADomainException(Exception):
    """Base exception for Style DNA domain."""
    pass

class StyleDNANotFoundError(StyleDNADomainException):
    def __init__(self, image_id: uuid.UUID):
        self.image_id = image_id
        super().__init__(f"Style DNA profile for image ID '{image_id}' was not found.")

class StyleDNAInputUnavailableError(StyleDNADomainException):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Style DNA input image unavailable: {reason}")

class StyleDNAAnalysisFailedError(StyleDNADomainException):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Style DNA analysis failed: {reason}")
