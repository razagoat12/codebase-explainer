import os
from pathlib import Path

from app.config import settings

# Extensions we'll read; everything else is skipped
READABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".kt",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift", ".scala",
    ".html", ".css", ".scss", ".json", ".yaml", ".yml", ".toml", ".md",
    ".sh", ".bash", ".zsh", ".dockerfile", ".tf", ".sql",
}

SKIP_DIRS = {
    ".git", ".svn", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".nuxt", "vendor", ".idea", ".vscode",
}


def is_safe_path(directory: str) -> Path:
    """Resolve and validate the path is an existing directory (no traversal)."""
    p = Path(directory).resolve()
    if not p.exists():
        raise ValueError(f"Path does not exist: {directory}")
    if not p.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")
    return p


def build_file_tree(root: Path) -> str:
    """Return an indented text tree of the directory."""
    lines = [str(root)]
    _walk_tree(root, "", lines)
    return "\n".join(lines)


def _walk_tree(path: Path, prefix: str, lines: list[str]) -> None:
    entries = sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name))
    entries = [e for e in entries if e.name not in SKIP_DIRS]
    for i, entry in enumerate(entries):
        connector = "└── " if i == len(entries) - 1 else "├── "
        lines.append(f"{prefix}{connector}{entry.name}")
        if entry.is_dir():
            extension = "    " if i == len(entries) - 1 else "│   "
            _walk_tree(entry, prefix + extension, lines)


def ingest_directory(directory: str) -> dict:
    """
    Walk the directory and collect file contents up to the configured limits.
    Returns a dict with keys: root, file_tree, files, stats.
    """
    root = is_safe_path(directory)
    file_tree = build_file_tree(root)

    files: list[dict] = []
    total_bytes = 0
    skipped_count = 0
    language_counts: dict[str, int] = {}

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip dirs in-place so os.walk won't descend into them
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for filename in sorted(filenames):
            ext = Path(filename).suffix.lower()
            if ext not in READABLE_EXTENSIONS:
                continue

            filepath = Path(dirpath) / filename
            try:
                file_size = filepath.stat().st_size
            except OSError:
                continue

            if file_size > settings.max_file_size_bytes:
                skipped_count += 1
                continue

            if total_bytes + file_size > settings.max_total_content_bytes:
                skipped_count += 1
                continue

            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            rel_path = str(filepath.relative_to(root))
            files.append({"path": rel_path, "content": content, "size": file_size})
            total_bytes += file_size
            language_counts[ext] = language_counts.get(ext, 0) + 1

    stats = {
        "total_files": len(files),
        "skipped_files": skipped_count,
        "total_bytes": total_bytes,
        "language_counts": language_counts,
    }

    return {"root": str(root), "file_tree": file_tree, "files": files, "stats": stats}
