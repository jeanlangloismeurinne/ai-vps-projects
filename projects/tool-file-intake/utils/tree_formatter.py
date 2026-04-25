from pathlib import Path

from services.explorer import get_tree


def format_tree(base: Path | None = None, max_entries: int = 60) -> str:
    """Retourne une arborescence ASCII formatée pour Slack (bloc code)."""
    tree = get_tree(base)
    lines = ["Documents/"]
    count = [0]
    _render(tree, lines, prefix="", count=count, max_entries=max_entries)
    if count[0] >= max_entries:
        lines.append("    … (tronqué)")
    return "\n".join(lines)


def _render(node: dict, lines: list[str], prefix: str, count: list[int], max_entries: int) -> None:
    items = list(node.items())
    for i, (name, children) in enumerate(items):
        if count[0] >= max_entries:
            return
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{name}")
        count[0] += 1
        if children:
            extension = "    " if is_last else "│   "
            _render(children, lines, prefix + extension, count, max_entries)
