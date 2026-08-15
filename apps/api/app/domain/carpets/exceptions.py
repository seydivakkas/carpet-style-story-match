import uuid

class CarpetDomainException(Exception):
    """Base domain exception for Carpet aggregate."""
    pass

class CarpetNotFoundError(CarpetDomainException):
    def __init__(self, carpet_id: uuid.UUID):
        self.carpet_id = carpet_id
        super().__init__(f"Carpet with ID '{carpet_id}' was not found.")

class CarpetSkuConflictError(CarpetDomainException):
    def __init__(self, sku: str):
        self.sku = sku
        super().__init__(f"A carpet with SKU '{sku}' already exists.")
