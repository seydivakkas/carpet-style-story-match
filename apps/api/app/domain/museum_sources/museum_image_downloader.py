"""Downloader and host validator module for official museum object images (The Met, V&A)."""
import re
import time
import urllib.request
import urllib.parse
from typing import Tuple, Set

# Approved museum image host allowlist
MUSEUM_ALLOWED_HOSTS: Set[str] = {
    "images.metmuseum.org",
    "metmuseum.org",
    "www.metmuseum.org",
    "framemark.vam.ac.uk",
    "media.vam.ac.uk",
    "vam.ac.uk",
    "www.vam.ac.uk",
}

# Maximum allowed image download size (15 MB)
MAX_IMAGE_SIZE_BYTES = 15 * 1024 * 1024

HEADERS = {
    "User-Agent": "CarpetStyleStoryMatch/1.0.0-rc.1 MuseumAssetIntegration/1.0 (+http://localhost)"
}


class InvalidHostError(ValueError):
    """Raised when an image URL host is not in the approved museum allowlist."""
    pass


class InvalidSchemeError(ValueError):
    """Raised when an image URL scheme is not HTTP/HTTPS."""
    pass


class RedirectHostError(ValueError):
    """Raised when a download redirect leads to a non-allowlisted host."""
    pass


class ImageOversizeError(ValueError):
    """Raised when downloaded image exceeds maximum allowed size."""
    pass


def is_museum_host_allowlisted(host: str) -> bool:
    """Check if host string is in the official museum asset allowlist."""
    if not host:
        return False
    clean_host = host.lower().split(":")[0].strip()
    if clean_host in MUSEUM_ALLOWED_HOSTS:
        return True
    if clean_host.endswith(".metmuseum.org") or clean_host.endswith(".vam.ac.uk"):
        return True
    return False


def validate_museum_image_url_host(url: str) -> str:
    """Validate that the URL scheme is HTTPS/HTTP and host is allowlisted."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise InvalidSchemeError(f"Disallowed URL scheme '{parsed.scheme}'. Only http and https are allowed.")

    if not is_museum_host_allowlisted(parsed.netloc):
        raise InvalidHostError(f"Disallowed museum image host '{parsed.netloc}'. Must belong to approved museum host allowlist.")

    return url


class SafeMuseumRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom HTTP redirect handler that enforces museum host allowlisting on all redirect hops."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme.lower() not in ("http", "https"):
            raise InvalidSchemeError(f"Redirect to disallowed URL scheme '{parsed.scheme}'")
        if not is_museum_host_allowlisted(parsed.netloc):
            raise RedirectHostError(f"Redirected to non-allowlisted museum host '{parsed.netloc}'")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_museum_image_bytes(
    url: str,
    timeout: int = 15,
    delay_sec: float = 0.2,
    max_bytes: int = MAX_IMAGE_SIZE_BYTES
) -> Tuple[bytes, str]:
    """Download museum image bytes safely with host allowlisting, redirect safety, size cap, and rate limit."""
    validate_museum_image_url_host(url)

    if delay_sec > 0:
        time.sleep(delay_sec)

    opener = urllib.request.build_opener(SafeMuseumRedirectHandler())
    req = urllib.request.Request(url, headers=HEADERS)

    with opener.open(req, timeout=timeout) as resp:
        final_url = resp.geturl()
        validate_museum_image_url_host(final_url)

        content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()

        content_length = resp.headers.get("Content-Length")
        if content_length and int(content_length) > max_bytes:
            raise ImageOversizeError(f"Image Content-Length {content_length} bytes exceeds max allowed size of {max_bytes} bytes")

        chunks = []
        downloaded = 0
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            downloaded += len(chunk)
            if downloaded > max_bytes:
                raise ImageOversizeError(f"Downloaded image size exceeded max allowed size of {max_bytes} bytes")
            chunks.append(chunk)

        file_bytes = b"".join(chunks)
        return file_bytes, content_type
