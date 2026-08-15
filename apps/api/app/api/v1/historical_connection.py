"""API endpoints for Historical Connection Engine v1."""
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.domain.historical_connection.exceptions import (
    HistoricalConnectionError,
    HistoricalConnectionNotFoundError,
    HistoricalConnectionTargetProfileNotFoundError,
    HistoricalConnectionTargetProfileFailedError,
    HistoricalConnectionInvalidTargetTypeError,
    HistoricalConnectionReferenceNotFoundError,
    HistoricalConnectionReferenceImageRequiredError,
    HistoricalConnectionReferenceProfileRequiredError,
    HistoricalConnectionReferenceProfileFailedError,
    HistoricalConnectionStyleVersionMismatchError,
    HistoricalConnectionInputInvalidError
)
from app.domain.historical_connection.schemas import (
    HistoricalConnectionCreateInput,
    HistoricalConnectionDetailRead,
    HistoricalConnectionListResponse,
    HistoricalConnectionMetaResponse
)
from app.domain.historical_connection.service import HistoricalConnectionService

router = APIRouter(tags=["historical-connections"])


@router.post(
    "/historical-connections",
    response_model=HistoricalConnectionDetailRead,
    status_code=status.HTTP_201_CREATED,
    summary="Evaluate pairwise visual Style DNA connection against a historical reference"
)
async def create_historical_connection(
    input_data: HistoricalConnectionCreateInput,
    db: AsyncSession = Depends(get_db)
) -> HistoricalConnectionDetailRead:
    service = HistoricalConnectionService(db)
    try:
        return await service.create_historical_connection(input_data)
    except HistoricalConnectionTargetProfileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "HISTORICAL_CONNECTION_TARGET_PROFILE_NOT_FOUND", "message": str(e)}
        )
    except HistoricalConnectionTargetProfileFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "HISTORICAL_CONNECTION_TARGET_PROFILE_FAILED", "message": str(e)}
        )
    except HistoricalConnectionInvalidTargetTypeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "HISTORICAL_CONNECTION_INVALID_TARGET_TYPE", "message": str(e)}
        )
    except HistoricalConnectionReferenceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "HISTORICAL_CONNECTION_REFERENCE_NOT_FOUND", "message": str(e)}
        )
    except HistoricalConnectionReferenceImageRequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "HISTORICAL_CONNECTION_REFERENCE_IMAGE_REQUIRED", "message": str(e)}
        )
    except HistoricalConnectionReferenceProfileRequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "HISTORICAL_CONNECTION_REFERENCE_PROFILE_REQUIRED", "message": str(e)}
        )
    except HistoricalConnectionReferenceProfileFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "HISTORICAL_CONNECTION_REFERENCE_PROFILE_FAILED", "message": str(e)}
        )
    except HistoricalConnectionStyleVersionMismatchError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "HISTORICAL_CONNECTION_STYLE_VERSION_MISMATCH", "message": str(e)}
        )
    except HistoricalConnectionInputInvalidError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "HISTORICAL_CONNECTION_INPUT_INVALID", "message": str(e)}
        )
    except HistoricalConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "HISTORICAL_CONNECTION_ERROR", "message": str(e)}
        )


@router.get(
    "/historical-connections/{connection_id}",
    response_model=HistoricalConnectionDetailRead,
    status_code=status.HTTP_200_OK,
    summary="Get historical connection evaluation detail & explanation"
)
async def get_historical_connection_detail(
    connection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> HistoricalConnectionDetailRead:
    service = HistoricalConnectionService(db)
    try:
        return await service.get_historical_connection_detail(connection_id)
    except HistoricalConnectionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "HISTORICAL_CONNECTION_NOT_FOUND", "message": str(e)}
        )


@router.get(
    "/historical-connections",
    response_model=HistoricalConnectionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List persisted pairwise historical connection evaluation results"
)
async def list_historical_connections(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    target_style_profile_id: Optional[uuid.UUID] = Query(None, description="Filter by target Style DNA profile ID"),
    historical_reference_id: Optional[str] = Query(None, description="Filter by historical reference ID or key"),
    db: AsyncSession = Depends(get_db)
) -> HistoricalConnectionListResponse:
    service = HistoricalConnectionService(db)
    return await service.list_historical_connections(
        limit=limit,
        offset=offset,
        target_style_profile_id=target_style_profile_id,
        historical_reference_id=historical_reference_id
    )


@router.get(
    "/meta/historical-connections",
    response_model=HistoricalConnectionMetaResponse,
    status_code=status.HTTP_200_OK,
    summary="Get historical connection engine version & enum metadata"
)
async def get_meta_historical_connections() -> HistoricalConnectionMetaResponse:
    return HistoricalConnectionService.get_meta_historical_connections()
