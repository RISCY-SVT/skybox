#!/usr/bin/env python3
"""Keyword audit helper for Vulkan/OpenGL ecosystem traces in Skybox repository."""

from __future__ import annotations

import argparse
import os
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

KEYWORDS: Dict[str, str] = {
    "vulkan": r"vulkan",
    "vk": r"\bvk\b|vk_|VK_",
    "egl": r"\begl\b|EGL_",
    "gles": r"gles|GLES",
    "mesa": r"\bmesa\b",
    "drm": r"\bdrm\b|DRM_",
}

SKIP_DIR_PREFIXES = (
    ".git",
    "third_party",
)

SKIP_DIR_NAMES = {
    ".git",
    "third_party",
    ".cache",
    "__pycache__",
}

# Skip common binary/output formats to avoid false positives from random bytes.
SKIP_SUFFIXES = {
    ".db",
    ".a",
    ".o",
    ".so",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".bin",
    ".gold",
    ".bmp",
    ".ico",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".zip",
    ".xz",
    ".gz",
}

def should_skip_rel_parts(parts: Tuple[str, ...], hw_only: bool) -> bool:
    if not parts:
        return False
    if hw_only and parts[0] != "hw":
        return True
    if any(p.startswith("build") for p in parts):
        return True
    if "artifacts" in parts:
        return True
    if parts[0] in SKIP_DIR_PREFIXES:
        return True
    return False


def is_probably_text(path: Path, sample_size: int = 4096) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(sample_size)
    except OSError:
        return False
    if not chunk:
        return True
    if b"\x00" in chunk:
        return False
    # Heuristic: a text file should have mostly printable bytes or whitespace.
    printable = sum(
        1
        for b in chunk
        if b in (9, 10, 13) or 32 <= b <= 126 or b >= 128
    )
    return printable / len(chunk) >= 0.85


def iter_files(repo_root: Path, hw_only: bool, max_bytes: int, skip_relpaths: set[str]) -> Iterable[Path]:
    root = repo_root / "hw" if hw_only else repo_root
    for dirpath, dirnames, filenames in os.walk(root):
        dir_rel = Path(dirpath).resolve().relative_to(repo_root.resolve())
        dir_parts = dir_rel.parts
        if should_skip_rel_parts(dir_parts, hw_only):
            dirnames[:] = []
            continue

        pruned_dirs: List[str] = []
        for d in dirnames:
            if d in SKIP_DIR_NAMES:
                continue
            if d.startswith("build"):
                continue
            if d == "artifacts":
                continue
            pruned_dirs.append(d)
        dirnames[:] = pruned_dirs

        for name in filenames:
            path = Path(dirpath) / name
            rel = path.resolve().relative_to(repo_root.resolve())
            if str(rel) in skip_relpaths:
                continue
            if should_skip_rel_parts(rel.parts, hw_only):
                continue
            if path.suffix.lower() in SKIP_SUFFIXES:
                continue
            try:
                if path.stat().st_size > max_bytes:
                    continue
            except OSError:
                continue
            if not is_probably_text(path):
                continue
            yield path


def scan_scope(
    repo_root: Path,
    hw_only: bool,
    max_bytes: int,
    skip_relpaths: set[str],
) -> Tuple[Dict[str, int], Dict[str, List[Tuple[str, int, str]]]]:
    patterns = {k: re.compile(v, re.IGNORECASE) for k, v in KEYWORDS.items()}
    counts = {k: 0 for k in KEYWORDS}
    hits: Dict[str, List[Tuple[str, int, str]]] = {k: [] for k in KEYWORDS}

    for path in iter_files(repo_root, hw_only, max_bytes, skip_relpaths):
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        rel = str(path.relative_to(repo_root))
        for lineno, line in enumerate(lines, start=1):
            for key, regex in patterns.items():
                found = list(regex.finditer(line))
                if not found:
                    continue
                counts[key] += len(found)
                snippet = line.strip()
                if len(snippet) > 180:
                    snippet = snippet[:177] + "..."
                hits[key].append((rel, lineno, snippet))
    return counts, hits


def escape_md(text: str) -> str:
    return text.replace("|", "\\|")


def render_file_table(rows: List[Tuple[str, int]], max_rows: int) -> List[str]:
    out = ["| File | Hits |", "|---|---:|"]
    for path, cnt in rows[:max_rows]:
        out.append(f"| `{escape_md(path)}` | {cnt} |")
    if not rows:
        out.append("| - | 0 |")
    return out


def render_context_table(hits: List[Tuple[str, int, str]], max_rows: int) -> List[str]:
    out = ["| File:line | Context |", "|---|---|"]
    for path, lineno, snippet in hits[:max_rows]:
        out.append(f"| `{escape_md(path)}:{lineno}` | `{escape_md(snippet)}` |")
    if not hits:
        out.append("| - | - |")
    return out


def write_report(repo_root: Path, out_md: Path, top_files: int, top_context: int, max_bytes: int) -> None:
    skip_relpaths: set[str] = set()
    try:
        skip_relpaths.add(str(out_md.resolve().relative_to(repo_root.resolve())))
    except ValueError:
        pass
    hw_counts, hw_hits = scan_scope(repo_root, hw_only=True, max_bytes=max_bytes, skip_relpaths=skip_relpaths)
    all_counts, all_hits = scan_scope(repo_root, hw_only=False, max_bytes=max_bytes, skip_relpaths=skip_relpaths)

    lines: List[str] = []
    lines.append("# Skybox Vulkan/OpenGL keyword audit (RU)")
    lines.append("")
    lines.append("- Scope A (HW-only): `hw/**`")
    lines.append("- Scope B (Whole repo): all files except `.git`, `third_party`, `build*`, `*/artifacts/*`")
    lines.append(f"- Max scanned file size: `{max_bytes}` bytes")
    lines.append("- Keywords: `vulkan`, `vk`, `egl`, `gles`, `mesa`, `drm`")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Keyword | HW-only hits | Whole-repo hits | Notes |")
    lines.append("|---|---:|---:|---|")
    for key in KEYWORDS:
        note = "No HW evidence" if hw_counts[key] == 0 else "HW references found"
        lines.append(f"| `{key}` | {hw_counts[key]} | {all_counts[key]} | {note} |")
    lines.append("")

    lines.append("## HW-only evidence")
    lines.append("")
    for key in KEYWORDS:
        lines.append(f"### `{key}`")
        lines.append("")
        file_counts = Counter(path for path, _, _ in hw_hits[key]).most_common()
        lines.extend(render_file_table(file_counts, top_files))
        lines.append("")
        lines.extend(render_context_table(hw_hits[key], top_context))
        lines.append("")

    lines.append("## Whole-repo evidence (top files)")
    lines.append("")
    for key in KEYWORDS:
        lines.append(f"### `{key}`")
        lines.append("")
        file_counts = Counter(path for path, _, _ in all_hits[key]).most_common()
        lines.extend(render_file_table(file_counts, top_files))
        lines.append("")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Vulkan/OpenGL keyword audit markdown report")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--out-md",
        default="docs/skybox_vulkan_opengl_keyword_audit_ru.md",
        help="Output markdown file",
    )
    parser.add_argument("--top-files", type=int, default=12, help="Top files per keyword")
    parser.add_argument("--top-context", type=int, default=12, help="Context lines per keyword (HW scope)")
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=1_000_000,
        help="Skip files larger than this many bytes to keep audit deterministic and fast",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    out_md = (repo_root / args.out_md).resolve()
    write_report(repo_root, out_md, args.top_files, args.top_context, args.max_bytes)
    print(f"report={out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
