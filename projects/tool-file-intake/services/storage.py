import hashlib
import re
from datetime import datetime
from pathlib import Path

from config import ALLOWED_MIME_TYPES, settings

MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024
_SAFE_NAME_RE = re.compile(r"[^\w.\-]")


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_file(filename: str, content: bytes, mime_type: str) -> None:
    if len(content) > MAX_FILE_SIZE:
        raise ValueError(f"Fichier trop volumineux ({len(content) // 1024 // 1024} Mo > {settings.MAX_FILE_SIZE_MB} Mo max)")
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Type MIME non autorisé : {mime_type}")


def safe_join(base: Path, user_path: str) -> Path:
    """Résout le chemin et vérifie qu'il reste dans base (anti path-traversal)."""
    target = (base / user_path).resolve()
    if not str(target).startswith(str(base.resolve())):
        raise ValueError("Chemin invalide : tentative de path traversal détectée")
    return target


def sanitize_filename(name: str) -> str:
    stem = Path(name).stem
    suffix = Path(name).suffix
    clean = _SAFE_NAME_RE.sub("_", stem)
    return f"{clean}{suffix}"


def default_relative_path() -> str:
    now = datetime.now()
    return f"{now.year}/{now.month:02d}/{now.day:02d}"


def store_file(content: bytes, filename: str, relative_path: str) -> Path:
    """Stocke le fichier dans STORAGE_BASE/relative_path/filename.
    Retourne le chemin absolu du fichier créé."""
    target_dir = safe_join(settings.STORAGE_BASE, relative_path)
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(filename)
    dest = target_dir / safe_name

    # Évite d'écraser un fichier existant
    if dest.exists():
        sha = compute_sha256(content)[:8]
        stem = dest.stem
        dest = target_dir / f"{stem}_{sha}{dest.suffix}"

    dest.write_bytes(content)
    return dest
