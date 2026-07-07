import hashlib
import os
from pathlib import Path

from app.config import settings


def compute_content_hash(files: list[dict]) -> str:
    """Stable hash of all file contents — same code = same hash, regardless of path."""
    h = hashlib.sha256()
    for f in sorted(files, key=lambda x: x["path"]):
        h.update(f["path"].encode())
        h.update(b"\0")
        h.update(f["content"].encode("utf-8", errors="replace"))
        h.update(b"\0")
    return h.hexdigest()

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


# Absolute system directories that must never be handed to the ingestion
# pipeline (their contents would otherwise be read and forwarded to the LLM
# API, then persisted in the analysis record). This is a blocklist rather
# than an allowlist so legitimate project directories anywhere on disk
# (home dir, /opt, /srv, temp dirs used by the test suite, etc.) keep working.
#
# Two tiers:
# - _BLOCKED_EXACT: only the bare directory itself is refused. "/Users" and
#   "/home" hold *every* user's home directory, but each individual home
#   (e.g. /Users/alice) is a legitimate, common place to keep projects, so
#   only bulk access to the parent is blocked, not everything beneath it.
# - _BLOCKED_SUBTREES: the directory and everything nested inside it is
#   refused. Note "/" itself is handled by _BLOCKED_EXACT, not here — every
#   absolute path's ancestor chain ends at "/", so putting it in the
#   subtree set would make every path match.
_BLOCKED_EXACT = {Path(p) for p in ("/", "/Users", "/home")}
_BLOCKED_SUBTREES = {
    Path(p)
    for p in (
        "/etc", "/private/etc", "/root", "/System", "/Library",
        "/usr", "/bin", "/sbin", "/boot", "/sys", "/proc", "/Applications",
    )
}


def is_safe_path(directory: str) -> Path:
    """Resolve and validate the path is an existing directory outside any
    blocked system root (no traversal, no reading OS/config directories)."""
    p = Path(directory).resolve()
    if not p.exists():
        raise ValueError(f"Path does not exist: {directory}")
    if not p.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")
    if (
        p in _BLOCKED_EXACT
        or p in _BLOCKED_SUBTREES
        or any(root in p.parents for root in _BLOCKED_SUBTREES)
    ):
        raise ValueError(f"Refusing to analyze system directory: {directory}")
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
