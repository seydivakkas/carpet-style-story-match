"""
User Upload Analysis Service & VLM Provider Factory.

Factory and orchestrator for visual motif analysis. Integrates image preparation,
quality validation, provider invocation, and contract enforcement.
"""
import logging
from typing import Dict, Any, Optional
import httpx

from app.core.config import Settings
from app.domain.upload_analysis.image_preparation import prepare_image_for_vlm, PreparedInferenceImage
from app.domain.upload_analysis.vlm_provider import (
    MotifVisionProvider,
    VLLMOpenAICompatibleVisionProvider,
    RemoteOpenAICompatibleVisionProvider,
    FixtureVisionProvider,
    LocalCVVisionProvider,
    HybridVisionProvider,
    VLMProviderError,
    ProviderType
)
from app.domain.upload_analysis.schemas import UploadAnalysisResult

logger = logging.getLogger(__name__)


def get_vlm_provider(settings: Settings) -> Optional[MotifVisionProvider]:
    """Factory creating configured VLM Provider instance."""
    mode = settings.MOTIF_VLM_PROVIDER.upper()

    if mode == "DISABLED":
        return None

    if mode in ("LOCAL_CV", "CV_PATTERN"):
        return LocalCVVisionProvider()

    if mode == "HYBRID":
        base_vlm = None
        if settings.MOTIF_VLM_BASE_URL:
            base_vlm = VLLMOpenAICompatibleVisionProvider(
                base_url=settings.MOTIF_VLM_BASE_URL,
                model_id=settings.MOTIF_VLM_MODEL,
                timeout_seconds=settings.MOTIF_VLM_TIMEOUT_SECONDS,
                max_retries=settings.MOTIF_VLM_MAX_RETRIES
            )
        return HybridVisionProvider(vlm_provider=base_vlm)

    if mode == "LOCAL_VLLM":
        if not settings.MOTIF_VLM_BASE_URL:
            return LocalCVVisionProvider()
        return VLLMOpenAICompatibleVisionProvider(
            base_url=settings.MOTIF_VLM_BASE_URL,
            model_id=settings.MOTIF_VLM_MODEL,
            timeout_seconds=settings.MOTIF_VLM_TIMEOUT_SECONDS,
            max_retries=settings.MOTIF_VLM_MAX_RETRIES
        )

    if mode == "REMOTE_OPENAI_COMPATIBLE":
        if not settings.MOTIF_VLM_BASE_URL:
            return LocalCVVisionProvider()
        return RemoteOpenAICompatibleVisionProvider(
            base_url=settings.MOTIF_VLM_BASE_URL,
            model_id=settings.MOTIF_VLM_MODEL,
            api_key=settings.MOTIF_VLM_API_KEY,
            timeout_seconds=settings.MOTIF_VLM_TIMEOUT_SECONDS,
            max_retries=settings.MOTIF_VLM_MAX_RETRIES
        )

    if mode == "TEST_FIXTURE":
        return FixtureVisionProvider()

    # Fallback to intelligent local CV provider rather than crashing
    return LocalCVVisionProvider()


async def get_vlm_provider_status(settings: Settings) -> Dict[str, Any]:
    """Check VLM provider configuration and reachability status without exposing secrets."""
    mode = settings.MOTIF_VLM_PROVIDER.upper()
    
    if mode == "DISABLED":
        return {
            "provider_type": "DISABLED",
            "configured": False,
            "reachable": False,
            "model_id": settings.MOTIF_VLM_MODEL,
            "inference_enabled": False,
            "message": "VLM inference service is disabled in configuration."
        }

    configured = bool(settings.MOTIF_VLM_BASE_URL or mode == "TEST_FIXTURE")
    reachable = False
    message = "Provider configured."

    if mode in ("TEST_FIXTURE", "LOCAL_CV", "CV_PATTERN"):
        reachable = True
        message = "Local visual motif detector provider active."
    elif mode == "HYBRID":
        reachable = True
        message = "Hybrid provider active (Local CV + VLM fallback)."
    elif configured and settings.MOTIF_VLM_BASE_URL:
        # Reachability ping check
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{settings.MOTIF_VLM_BASE_URL.rstrip('/')}/models")
                if res.status_code in (200, 401, 403):
                    reachable = True
                    message = "VLM endpoint reachable."
                else:
                    message = f"VLM endpoint returned HTTP {res.status_code}"
        except Exception as e:
            message = f"VLM endpoint unreachable: {type(e).__name__}"

    inference_enabled = (mode in ("TEST_FIXTURE", "LOCAL_CV", "CV_PATTERN", "HYBRID")) or (configured and reachable)

    return {
        "provider_type": mode,
        "configured": True if mode in ("LOCAL_CV", "HYBRID", "TEST_FIXTURE") else configured,
        "reachable": reachable,
        "model_id": settings.MOTIF_VLM_MODEL,
        "inference_enabled": inference_enabled,
        "message": message
    }


async def analyze_user_upload_image(
    raw_bytes: bytes,
    mime_type: str,
    settings: Settings
) -> UploadAnalysisResult:
    """Orchestrate full visual analysis of user upload image."""
    provider = get_vlm_provider(settings)
    if not provider:
        raise VLMProviderError("VLM inference provider is disabled or not configured.")

    # Prepare and sanitize image
    prepared_image = prepare_image_for_vlm(
        raw_bytes=raw_bytes,
        mime_type=mime_type,
        is_remote=(settings.MOTIF_VLM_PROVIDER.upper() == "REMOTE_OPENAI_COMPATIBLE")
    )

    # Perform analysis
    return await provider.analyze(prepared_image)
