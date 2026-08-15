# Carpet Image Input & Safe Upload Specification

## 1. Overview

The **Carpet Image Input** module handles multipart image uploads for `Carpet` records. It enforces strict byte-level and image-content validations, strips non-essential EXIF metadata, generates collision-resistant server-managed storage keys, and ensures atomic database and storage consistency.

> **CRITICAL BOUNDARY INVARIANT**:
> Uploading an image (`UPLOAD SUCCESS`) is strictly an asset input phase. It does NOT execute 9D Style DNA extraction or visual matching algorithms (`UPLOAD SUCCESS != STYLE DNA SUCCESS`).

---

## 2. Technical Limits & Validation Pipeline

| Parameter | Configuration Key | Default Value | Action on Violation |
|---|---|---|---|
| Max File Size | `MAX_IMAGE_UPLOAD_BYTES` | 15 MB (`15,728,640` bytes) | `413 Payload Too Large` (`IMAGE_TOO_LARGE`) |
| Min Dimensions | `MIN_IMAGE_WIDTH`, `MIN_IMAGE_HEIGHT` | 128 × 128 px | `422 Unprocessable Entity` (`IMAGE_DIMENSIONS_TOO_SMALL`) |
| Max Dimensions | `MAX_IMAGE_WIDTH`, `MAX_IMAGE_HEIGHT` | 12000 × 12000 px | `422 Unprocessable Entity` (`IMAGE_DIMENSIONS_TOO_LARGE`) |
| Max Total Pixels | `MAX_IMAGE_PIXELS` | 80,000,000 px | `422 Unprocessable Entity` (`IMAGE_DIMENSIONS_TOO_LARGE`) |
| Accepted Formats | MIME / Decoder | `image/jpeg`, `image/png`, `image/webp` | `415 Unsupported Media Type` (`IMAGE_UNSUPPORTED_MEDIA_TYPE`) |

---

## 3. Upload Pipeline Sequence

```text
1. Check Carpet Existence (GET /carpets/{carpet_id}) -> 404 if missing
2. Bounded Byte Read (Max 15 MB) -> 413 if exceeded
3. Compute SHA-256 Hash of original input bytes
4. Duplicate Check (carpet_id + sha256) -> 409 if exists
5. Header MIME & Image Content Validation (OpenCV / Pillow decode) -> 415 / 422 if invalid/corrupt
6. Dimension & Pixel Bounds Check -> 422 if out of bounds
7. EXIF Orientation Normalization & Privacy Stripping
8. Local Storage Persistence (data/uploads/carpets/{carpet_id}/{image_id}.jpg)
9. Database Record Creation (CarpetImageModel)
```

---

## 4. Security & Path Traversal Prevention

- **Server-Generated Storage Keys**: File paths on disk follow `carpets/{carpet_id}/{image_id}.{extension}`. The client-provided `original_filename` is stored purely as text metadata for display and is NEVER used to construct directory paths or file names.
- **Privacy Metadata Stripping**: EXIF GPS data and personal device identifiers are removed during canonical re-encoding.
- **No Path Leakage**: Absolute local file system paths (e.g., `C:\Users\...` or `/var/storage/...`) are strictly excluded from API responses.

---

## 5. Duplicate & Cascade Delete Policies

- **Duplicate Policy**: Uploading an identical image (matching `sha256`) to the **same** `carpet_id` returns `409 Conflict` (`IMAGE_DUPLICATE`).
- **Image Deletion**: `DELETE /api/v1/carpets/{carpet_id}/images/{image_id}` removes both the database record and the stored file on disk.
- **Carpet Cascade Deletion**: Deleting a `Carpet` record automatically triggers deletion of all associated `CarpetImage` database rows AND removes all corresponding image files from disk.

---

## 6. API Endpoints

- `POST /api/v1/carpets/{carpet_id}/images`: Accepts multipart `file` upload (201 Created).
- `GET /api/v1/carpets/{carpet_id}/images`: Lists all image metadata records for a carpet (200 OK).
- `GET /api/v1/carpets/{carpet_id}/images/{image_id}`: Gets single image metadata by UUID (200 OK).
- `GET /api/v1/carpets/{carpet_id}/images/{image_id}/content`: Streams image binary content with proper `Content-Type` (200 OK).
- `DELETE /api/v1/carpets/{carpet_id}/images/{image_id}`: Deletes image metadata & file on disk (204 No Content).
