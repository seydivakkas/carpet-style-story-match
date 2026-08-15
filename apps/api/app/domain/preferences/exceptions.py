import uuid
from typing import List

class PreferenceDomainException(Exception):
    """Base exception for Preference Assessment domain."""
    pass

class AssessmentNotFoundError(PreferenceDomainException):
    def __init__(self, assessment_id: uuid.UUID):
        self.assessment_id = assessment_id
        super().__init__(f"Preference assessment ID '{assessment_id}' was not found.")

class TextPreferencesIncompleteError(PreferenceDomainException):
    def __init__(self, assessment_id: uuid.UUID, answered_count: int, missing_keys: List[str]):
        self.assessment_id = assessment_id
        self.answered_count = answered_count
        self.missing_keys = missing_keys
        super().__init__(
            f"Cannot complete text assessment '{assessment_id}': answered {answered_count}/6. "
            f"Missing questions: {', '.join(missing_keys)}."
        )

class TextPreferencesAlreadyCompletedError(PreferenceDomainException):
    def __init__(self, assessment_id: uuid.UUID):
        self.assessment_id = assessment_id
        super().__init__(
            f"Assessment '{assessment_id}' is already TEXT_COMPLETE. Responses cannot be modified."
        )

class InvalidQuestionKeyError(PreferenceDomainException):
    def __init__(self, question_key: str):
        self.question_key = question_key
        super().__init__(f"Invalid text preference question key: '{question_key}'.")
