import uuid

class ImageDomainException(Exception):
    """Base exception for Image domain."""
    pass

class CarpetImageNotFoundError(ImageDomainException):
    def __init__(self, image_id: uuid.UUID):
        self.image_id = image_id
        super().__init__(f"Carpet image with ID '{image_id}' was not found.")

class ImageTooLargeError(ImageDomainException):
    def __init__(self, byte_size: int, max_bytes: int):
        self.byte_size = byte_size
        self.max_bytes = max_bytes
        super().__init__(f"Image byte size {byte_size} exceeds maximum allowed limit of {max_bytes} bytes.")

class ImageUnsupportedMediaTypeError(ImageDomainException):
    def __init__(self, media_type: str):
        self.media_type = media_type
        super().__init__(f"Media type '{media_type}' is not supported. Allowed formats: image/jpeg, image/png, image/webp.")

class ImageDecodeFailedError(ImageDomainException):
    def __init__(self, reason: str = "Failed to decode valid image array"):
        self.reason = reason
        super().__init__(f"Image decode failed: {reason}")

class ImageDimensionsTooSmallError(ImageDomainException):
    def __init__(self, width: int, height: int, min_w: int, min_h: int):
        self.width = width
        self.height = height
        super().__init__(f"Image dimensions ({width}x{height}) are smaller than minimum allowed ({min_w}x{min_h}).")

class ImageDimensionsTooLargeError(ImageDomainException):
    def __init__(self, width: int, height: int, max_w: int, max_h: int):
        self.width = width
        self.height = height
        super().__init__(f"Image dimensions ({width}x{height}) exceed maximum allowed limit ({max_w}x{max_h}).")

class ImageDuplicateError(ImageDomainException):
    def __init__(self, carpet_id: uuid.UUID, sha256: str):
        self.carpet_id = carpet_id
        self.sha256 = sha256
        super().__init__(f"Image with hash '{sha256}' has already been uploaded for carpet '{carpet_id}'.")

class ImageStorageFailedError(ImageDomainException):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Storage persistence failed: {reason}")
