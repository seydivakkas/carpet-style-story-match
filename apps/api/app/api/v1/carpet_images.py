import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.domain.carpets.repository import CarpetRepository
from app.domain.carpets.service import CarpetService
from app.domain.carpets.exceptions import CarpetNotFoundError
from app.domain.images.schemas import CarpetImageRead, CarpetImageListResponse
from app.domain.images.storage import LocalImageStorage
from app.domain.images.validation import ImageValidationService
from app.domain.images.repository import CarpetImageRepository
from app.domain.images.service import CarpetImageService
from app.domain.images.exceptions import (
    CarpetImageNotFoundError,
    ImageTooLargeError,
    ImageUnsupportedMediaTypeError,
    ImageDecodeFailedError,
    ImageDimensionsTooSmallError,
    ImageDimensionsTooLargeError,
    ImageDuplicateError,
    ImageStorageFailedError
)

router = APIRouter(prefix="/carpets/{carpet_id}/images", tags=["carpet-images"])

def get_carpet_image_service(db: AsyncSession = Depends(get_db)) -> CarpetImageService:
    carpet_repo = CarpetRepository(db)
    carpet_service = CarpetService(carpet_repo)
    image_repo = CarpetImageRepository(db)
    storage = LocalImageStorage()
    validator = ImageValidationService()
    return CarpetImageService(carpet_service, image_repo, storage, validator)

@router.post(
    "",
    response_model=CarpetImageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new carpet image"
)
async def upload_carpet_image(
    carpet_id: uuid.UUID,
    file: UploadFile = File(...),
    service: CarpetImageService = Depends(get_carpet_image_service)
):
    try:
        content = await file.read()
        filename = file.filename or "unnamed_image"
        content_type = file.content_type or "application/octet-stream"

        image = await service.upload_carpet_image(
            carpet_id=carpet_id,
            original_filename=filename,
            content_type=content_type,
            file_bytes=content
        )
        return image
    except CarpetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CARPET_NOT_FOUND", "message": str(exc)}
        )
    except ImageTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "IMAGE_TOO_LARGE", "message": str(exc)}
        )
    except ImageUnsupportedMediaTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"code": "IMAGE_UNSUPPORTED_MEDIA_TYPE", "message": str(exc)}
        )
    except ImageDecodeFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "IMAGE_DECODE_FAILED", "message": str(exc)}
        )
    except ImageDimensionsTooSmallError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "IMAGE_DIMENSIONS_TOO_SMALL", "message": str(exc)}
        )
    except ImageDimensionsTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "IMAGE_DIMENSIONS_TOO_LARGE", "message": str(exc)}
        )
    except ImageDuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "IMAGE_DUPLICATE", "message": str(exc)}
        )
    except ImageStorageFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "IMAGE_STORAGE_FAILED", "message": str(exc)}
        )

@router.get(
    "",
    response_model=CarpetImageListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all images for a carpet"
)
async def list_carpet_images(
    carpet_id: uuid.UUID,
    service: CarpetImageService = Depends(get_carpet_image_service)
):
    try:
        items = await service.list_carpet_images(carpet_id)
        return CarpetImageListResponse(items=items, total=len(items))
    except CarpetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CARPET_NOT_FOUND", "message": str(exc)}
        )

@router.get(
    "/{image_id}",
    response_model=CarpetImageRead,
    status_code=status.HTTP_200_OK,
    summary="Get metadata for a single carpet image"
)
async def get_carpet_image(
    carpet_id: uuid.UUID,
    image_id: uuid.UUID,
    service: CarpetImageService = Depends(get_carpet_image_service)
):
    try:
        image = await service.get_carpet_image(carpet_id, image_id)
        return image
    except CarpetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CARPET_NOT_FOUND", "message": str(exc)}
        )
    except CarpetImageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CARPET_IMAGE_NOT_FOUND", "message": str(exc)}
        )

@router.get(
    "/{image_id}/content",
    summary="Stream raw binary image file content"
)
async def get_carpet_image_content(
    carpet_id: uuid.UUID,
    image_id: uuid.UUID,
    service: CarpetImageService = Depends(get_carpet_image_service)
):
    try:
        content_bytes, media_type = await service.get_carpet_image_content(carpet_id, image_id)
        return Response(content=content_bytes, media_type=media_type)
    except CarpetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CARPET_NOT_FOUND", "message": str(exc)}
        )
    except CarpetImageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CARPET_IMAGE_NOT_FOUND", "message": str(exc)}
        )

@router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a carpet image record and its file"
)
async def delete_carpet_image(
    carpet_id: uuid.UUID,
    image_id: uuid.UUID,
    service: CarpetImageService = Depends(get_carpet_image_service)
):
    try:
        await service.delete_carpet_image(carpet_id, image_id)
        return None
    except CarpetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CARPET_NOT_FOUND", "message": str(exc)}
        )
    except CarpetImageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CARPET_IMAGE_NOT_FOUND", "message": str(exc)}
        )
