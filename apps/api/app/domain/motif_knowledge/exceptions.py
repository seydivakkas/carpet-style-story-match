"""Domain exceptions for Motif Knowledge."""

class MotifKnowledgeError(Exception):
    """Base exception for motif knowledge domain."""
    pass

class MotifNotFoundError(MotifKnowledgeError):
    """Raised when a motif is not found."""
    pass

class ClaimNotFoundError(MotifKnowledgeError):
    """Raised when a motif story claim is not found."""
    pass

class SourceNotFoundError(MotifKnowledgeError):
    """Raised when a curated source is not found."""
    pass

class CurationValidationError(MotifKnowledgeError):
    """Raised when a curated dataset violates status or structural invariants."""
    pass

class CurationConflictError(MotifKnowledgeError):
    """Raised when an imported key conflicts with existing different content."""
    pass

class UnsupportedSchemaVersionError(MotifKnowledgeError):
    """Raised when an import file uses an unsupported schema version."""
    pass
