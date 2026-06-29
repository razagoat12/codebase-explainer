"""
GitHub repository ingestion via the public REST API.
Fetches file contents recursively without requiring authentication
for public repos. Private repos require a GITHUB_TOKEN in .env.
"""
import base64
from urllib.parse import urlparse

import httpx

from app.config import settings

READABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".kt",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift", ".scala",
    ".html", ".css", ".scss", ".json", ".yaml", ".yml", ".toml", ".md",
    ".sh", ".bash", ".zsh", ".dockerfile", ".tf", ".sql",
}

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", "vendor",
}

GITHUB_API = "https://api.github.com"


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repo from a GitHub URL. Returns (owner, repo)."""
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse GitHub URL: {url}")
    return parts[0], parts[1].removesuffix(".git")


def _get_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = getattr(settings, "github_token", None)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_tree(owner: str, repo: str, branch: str = "HEAD") -> list[dict]:
    """Fetch the full file tree using Git Trees API (recursive, one call)."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    resp = httpx.get(url, headers=_get_headers(), timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if data.get("truncated"):
        pass  # very large repos — we still get most files
    return [item for item in data.get("tree", []) if item["type"] == "blob"]


def _fetch_file(owner: str, repo: str, path: str) -> str | None:
    """Fetch a single file's content via Contents API."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    resp = httpx.get(url, headers=_get_headers(), timeout=15)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("encoding") != "base64":
        return None
    try:
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except Exception:
        return None


def _build_tree_string(files: list[dict]) -> str:
    """Build an indented tree string from flat file list."""
    lines = []
    for f in files:
        parts = f["path"].split("/")
        indent = "  " * (len(parts) - 1)
        lines.append(f"{indent}{'└── ' if len(parts) > 1 else ''}{parts[-1]}")
    return "\n".join(lines)


def ingest_github(repo_url: str) -> dict:
    """
    Fetch a GitHub repo and return the same shape as ingest_directory():
    { root, file_tree, files, stats }
    """
    owner, repo = parse_github_url(repo_url)

    # Get default branch
    meta = httpx.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=_get_headers(), timeout=15)
    meta.raise_for_status()
    default_branch = meta.json().get("default_branch", "main")

    all_blobs = _fetch_tree(owner, repo, default_branch)

    # Filter to readable files, skip large and skip dirs
    candidates = []
    for blob in all_blobs:
        path = blob["path"]
        parts = path.split("/")
        if any(p in SKIP_DIRS for p in parts[:-1]):
            continue
        from pathlib import Path
        ext = Path(path).suffix.lower()
        if ext not in READABLE_EXTENSIONS:
            continue
        size = blob.get("size", 0)
        if size > settings.max_file_size_bytes:
            continue
        candidates.append({"path": path, "size": size})

    # Fetch content up to total byte cap
    files = []
    total_bytes = 0
    skipped = 0
    language_counts: dict[str, int] = {}

    for c in candidates:
        if total_bytes + c["size"] > settings.max_total_content_bytes:
            skipped += 1
            continue
        content = _fetch_file(owner, repo, c["path"])
        if content is None:
            skipped += 1
            continue
        from pathlib import Path
        ext = Path(c["path"]).suffix.lower()
        files.append({"path": c["path"], "content": content, "size": c["size"]})
        total_bytes += c["size"]
        language_counts[ext] = language_counts.get(ext, 0) + 1

    file_tree = _build_tree_string([{"path": f["path"]} for f in files])

    stats = {
        "total_files": len(files),
        "skipped_files": skipped,
        "total_bytes": total_bytes,
        "language_counts": language_counts,
    }

    return {
        "root": f"https://github.com/{owner}/{repo}",
        "file_tree": file_tree,
        "files": files,
        "stats": stats,
    }
