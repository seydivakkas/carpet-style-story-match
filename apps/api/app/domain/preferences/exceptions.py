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

# ---------------------------------------------------------
# VISUAL PREFERENCE EXCEPTIONS (GÖREV 05)
# ---------------------------------------------------------

class VisualPhaseRequiresTextCompleteError(PreferenceDomainException):
    def __init__(self, assessment_id: uuid.UUID, current_status: str):
        self.assessment_id = assessment_id
        self.current_status = current_status
        super().__init__(
            f"Cannot start visual phase for assessment '{assessment_id}': status is '{current_status}'. "
            "Visual phase requires status 'TEXT_COMPLETE'."
        )

class VisualPreferencesIncompleteError(PreferenceDomainException):
    def __init__(self, assessment_id: uuid.UUID, answered_count: int, missing_keys: List[str]):
        self.assessment_id = assessment_id
        self.answered_count = answered_count
        self.missing_keys = missing_keys
        super().__init__(
            f"Cannot complete visual assessment '{assessment_id}': answered {answered_count}/6. "
            f"Missing stimuli: {', '.join(missing_keys)}."
        )

class VisualPreferencesAlreadyCompletedError(PreferenceDomainException):
    def __init__(self, assessment_id: uuid.UUID):
        self.assessment_id = assessment_id
        super().__init__(
            f"Assessment '{assessment_id}' is already VISUAL_COMPLETE. Responses cannot be modified."
        )

class InvalidStimulusKeyError(PreferenceDomainException):
    def __init__(self, stimulus_key: str):
        self.stimulus_key = stimulus_key
        super().__init__(f"Invalid visual preference stimulus key: '{stimulus_key}'.")

class VisualProfileNotFoundError(PreferenceDomainException):
    def __init__(self, assessment_id: uuid.UUID):
        self.assessment_id = assessment_id
        super().__init__(f"Visual preference profile for assessment '{assessment_id}' was not found.")

# ---------------------------------------------------------
# MULTIMODAL PREFERENCE EXCEPTIONS (GÖREV 06)
# ---------------------------------------------------------

class MultimodalProfileRequiresVisualCompleteError(PreferenceDomainException):
    def __init__(self, assessment_id: uuid.UUID, current_status: str):
        self.assessment_id = assessment_id
        self.current_status = current_status
        super().__init__(
            f"Cannot build multimodal profile for assessment '{assessment_id}': status is '{current_status}'. "
            "Multimodal profile requires status 'VISUAL_COMPLETE'."
        )

class PreferenceProfileNotFoundError(PreferenceDomainException):
    def __init__(self, assessment_id: uuid.UUID):
        self.assessment_id = assessment_id
        super().__init__(f"User preference profile for assessment '{assessment_id}' was not found.")

class PreferenceConfidenceProfileNotFoundError(PreferenceDomainException):
    def __init__(self, assessment_id: uuid.UUID):
        self.assessment_id = assessment_id
        super().__init__(f"Preference confidence profile for assessment '{assessment_id}' was not found.")

class PreferenceDimensionNotFoundError(PreferenceDomainException):
    def __init__(self, dimension_key: str):
        self.dimension_key = dimension_key
        super().__init__(f"Invalid preference dimension key: '{dimension_key}'. Must be one of D1...D9.")

class PreferenceValueError(PreferenceDomainException):
    def __init__(self, value: float):
        self.value = value
        super().__init__(f"Preference dimension value '{value}' is out of range [0.0, 1.0].")

class PreferenceProfileAlreadyReviewedError(PreferenceDomainException):
    def __init__(self, assessment_id: uuid.UUID):
        self.assessment_id = assessment_id
        super().__init__(
            f"Preference profile for assessment '{assessment_id}' is already PROFILE_REVIEWED and immutable."
        )
