from pathlib import Path

from config import settings


def get_tree(base: Path | None = None, max_depth: int = 5) -> dict:
    """Retourne l'arborescence sous forme de dict imbriqué."""
    root = base or settings.STORAGE_BASE
    if not root.exists():
        return {}
    return _walk(root, root, 0, max_depth)


def _walk(node: Path, root: Path, depth: int, max_depth: int) -> dict:
    if depth >= max_depth:
        return {}
    result = {}
    try:
        children = sorted(node.iterdir())
    except PermissionError:
        return {}
    for child in children:
        rel = str(child.relative_to(root))
        if child.is_dir():
            result[child.name + "/"] = _walk(child, root, depth + 1, max_depth)
        else:
            result[child.name] = None
    return result


def list_subdirs(base: Path | None = None) -> list[str]:
    """Liste tous les sous-dossiers relatifs à STORAGE_BASE."""
    root = base or settings.STORAGE_BASE
    if not root.exists():
        return []
    dirs = []
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            dirs.append(str(p.relative_to(root)))
    return dirs
