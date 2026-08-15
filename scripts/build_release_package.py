"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Release Packaging & Deterministic Hash Generator for v1.0.0-rc.1.
- Generates release/source-manifest.sha256
- Packages release/carpet-style-story-match-1.0.0-rc.1-source.zip
- Generates release/carpet-style-story-match-1.0.0-rc.1-source.zip.sha256
- Inspects package for forbidden secrets/env files
"""
import os
import hashlib
import zipfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RELEASE_DIR = os.path.join(PROJECT_ROOT, "release")

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "uploads",
    "backups",
    "data",
    "release",
    "graphify-out",
    ".gemini"
}

EXCLUDE_FILES = {
    ".env",
    ".env.production",
    ".env.local",
    ".env.development",
    "tsconfig.tsbuildinfo"
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".log",
    ".zip",
    ".gz",
    ".tar",
    ".sql"
}


def file_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def is_included_file(rel_path: str) -> bool:
    parts = rel_path.replace("\\", "/").split("/")
    for p in parts:
        if p in EXCLUDE_DIRS:
            return False

    filename = parts[-1]
    if filename in EXCLUDE_FILES or filename.startswith(".env"):
        return False

    _, ext = os.path.splitext(filename)
    if ext.lower() in EXCLUDE_EXTENSIONS:
        return False

    return True


def collect_source_files():
    included = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Filter dirs in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            abs_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_path, PROJECT_ROOT).replace("\\", "/")
            if is_included_file(rel_path):
                included.append(rel_path)

    included.sort()
    return included


def generate_source_manifest(included_files):
    manifest_path = os.path.join(RELEASE_DIR, "source-manifest.sha256")
    lines = []
    for rel_path in included_files:
        abs_path = os.path.join(PROJECT_ROOT, rel_path)
        sha = file_sha256(abs_path)
        lines.append(f"{sha}  {rel_path}")

    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[MANIFEST GENERATED]: {manifest_path} ({len(lines)} files)")


def build_source_archive(included_files):
    zip_name = "carpet-style-story-match-1.0.0-rc.1-source.zip"
    zip_path = os.path.join(RELEASE_DIR, zip_name)
    hash_path = zip_path + ".sha256"

    # Include manifests in archive as well if present
    extra_files = ["release/release-manifest.json", "release/openapi.json", "release/source-manifest.sha256"]
    all_files = sorted(list(set(included_files + extra_files)))

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_path in all_files:
            abs_path = os.path.join(PROJECT_ROOT, rel_path)
            if os.path.exists(abs_path):
                zf.write(abs_path, arcname=f"carpet-style-story-match-1.0.0-rc.1/{rel_path}")

    archive_sha = file_sha256(zip_path)
    with open(hash_path, "w", encoding="utf-8") as f:
        f.write(f"{archive_sha}  {zip_name}\n")

    print(f"[ARCHIVE BUILT]: {zip_path}")
    print(f"[ARCHIVE SHA256]: {archive_sha}")

    # Inspect package security
    inspect_package(zip_path)


def inspect_package(zip_path: str):
    forbidden_found = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for item in zf.namelist():
            name = os.path.basename(item)
            _, ext = os.path.splitext(name)
            if name.startswith(".env") or name in EXCLUDE_FILES or ext.lower() in {".sql", ".gz", ".db", ".sqlite"}:
                forbidden_found.append(item)

    if forbidden_found:
        raise ValueError(f"SECURITY VIOLATION: Forbidden files found in release archive: {forbidden_found}")

    print("[SECURITY INSPECTION]: Archive clean. No secrets, .env files, or database dumps detected.")


if __name__ == "__main__":
    os.makedirs(RELEASE_DIR, exist_ok=True)
    files = collect_source_files()
    generate_source_manifest(files)
    build_source_archive(files)
