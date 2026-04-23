#!/usr/bin/env python3
"""Extract base64 images from Markdown files and rewrite image links.

Features:
1) Toggle between scanning all Markdown files in a directory or explicit file list.
2) Use short image folder names from bracket code (e.g. [NMAIex_1] -> images/NMAIex_1/).
3) Support both reference-style and inline base64 image links.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import re
from pathlib import Path
from typing import List, Tuple

REF_RE = re.compile(
    r"^\[(?P<label>[^\]]+)\]:\s*<?data:image/(?P<mime>[-+\w.]+);base64,(?P<data>[^>\s]+)>?\s*$"
)
INLINE_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\(\s*data:image/(?P<mime>[-+\w.]+);base64,(?P<data>[^)\s]+)\s*\)"
)
CODE_RE = re.compile(r"\[(?P<code>NMAIex(?:[_-]?\d*)?)\]", re.IGNORECASE)


def _mime_to_ext(mime: str) -> str:
    mime = mime.lower()
    mapping = {
        "png": "png",
        "jpeg": "jpg",
        "jpg": "jpg",
        "webp": "webp",
        "gif": "gif",
        "svg+xml": "svg",
    }
    return mapping.get(mime, "bin")


def _safe_stem(path: Path) -> str:
    stem = path.stem
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    if safe:
        return safe[:80]
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:8]
    return f"doc_{digest}"


def _decode_data(payload: str) -> bytes:
    compact = re.sub(r"\s+", "", payload)
    padding = (4 - len(compact) % 4) % 4
    compact += "=" * padding
    return base64.b64decode(compact)


def _folder_from_code(md_path: Path) -> str:
    """Return short folder name based on bracket code in filename.

    Examples:
    - [NMAIex_1] ... -> NMAIex_1
    - [NMAIex-2] ... -> NMAIex_2
    - [NMAIex] ...   -> NMAIex
    """
    match = CODE_RE.search(md_path.name)
    if not match:
        return _safe_stem(md_path)

    raw = match.group("code")
    m = re.match(r"(?i)^NMAIex(?:[_-]?(\d+))?$", raw)
    if not m:
        return _safe_stem(md_path)

    number = m.group(1)
    if number:
        return f"NMAIex_{number}"
    return "NMAIex"


def process_markdown(md_path: Path, output_root: Path, write: bool) -> Tuple[int, int]:
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=False)

    doc_dir = output_root / _folder_from_code(md_path)
    changed = False
    ref_count = 0

    for i, line in enumerate(lines):
        match = REF_RE.match(line)
        if not match:
            continue

        label = match.group("label")
        mime = match.group("mime")
        data = match.group("data")
        ext = _mime_to_ext(mime)

        raw = _decode_data(data)
        if write:
            doc_dir.mkdir(parents=True, exist_ok=True)
            out_file = doc_dir / f"{label}.{ext}"
            out_file.write_bytes(raw)

        rel = (doc_dir / f"{label}.{ext}").relative_to(md_path.parent).as_posix()
        lines[i] = f"[{label}]: {rel}"
        changed = True
        ref_count += 1

    inline_counter = 0

    def _inline_repl(match: re.Match[str]) -> str:
        nonlocal changed, inline_counter

        alt = match.group("alt")
        mime = match.group("mime")
        data = match.group("data")
        ext = _mime_to_ext(mime)
        inline_counter += 1

        raw = _decode_data(data)
        name = f"inline_{inline_counter:03d}.{ext}"

        if write:
            doc_dir.mkdir(parents=True, exist_ok=True)
            (doc_dir / name).write_bytes(raw)

        rel = (doc_dir / name).relative_to(md_path.parent).as_posix()
        changed = True
        return f"![{alt}]({rel})"

    new_text = "\n".join(lines)
    new_text = INLINE_RE.sub(_inline_repl, new_text)

    if write and changed:
        md_path.write_text(new_text + "\n", encoding="utf-8")

    return ref_count, inline_counter


def collect_markdown_files(targets: List[str]) -> List[Path]:
    files: List[Path] = []
    for target in targets:
        p = Path(target)
        if p.is_file() and p.suffix.lower() == ".md":
            files.append(p)
            continue

        if any(ch in target for ch in "*?[]"):
            files.extend(Path().glob(target))
            continue

        if p.is_dir():
            files.extend(sorted(p.rglob("*.md")))

    seen = set()
    unique_files: List[Path] = []
    for file_path in files:
        resolved = str(file_path.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_files.append(file_path)
    return unique_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract base64 images from Markdown files"
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Explicit Markdown files, directories, or glob patterns",
    )
    parser.add_argument(
        "--scan-all",
        action="store_true",
        help="Scan all .md files under --research-dir",
    )
    parser.add_argument(
        "--research-dir",
        default="docs/research",
        help="Root folder used when --scan-all is enabled",
    )
    parser.add_argument(
        "--output-root",
        default="docs/research/images",
        help="Directory to store extracted images",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.scan_all:
        files = sorted(Path(args.research_dir).rglob("*.md"))
    else:
        if not args.targets:
            print("No targets provided. Use explicit targets or --scan-all.")
            return 1
        files = collect_markdown_files(args.targets)

    if not files:
        print("No markdown files found.")
        return 1

    output_root = Path(args.output_root)
    write = not args.dry_run

    total_ref = 0
    total_inline = 0
    changed_files = 0

    for md_file in files:
        ref_count, inline_count = process_markdown(md_file, output_root, write)
        if ref_count or inline_count:
            changed_files += 1
        total_ref += ref_count
        total_inline += inline_count
        print(
            f"{md_file}: refs={ref_count}, inline={inline_count}, changed={bool(ref_count or inline_count)}"
        )

    mode = "WRITE" if write else "DRY-RUN"
    print(
        f"[{mode}] files_scanned={len(files)} changed_files={changed_files} refs={total_ref} inline={total_inline}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
