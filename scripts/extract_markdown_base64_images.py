#!/usr/bin/env python3
"""Extract base64 images from Markdown files and rewrite image links.

Features:
1) Toggle between scanning all Markdown files in a directory or explicit file list.
2) Use short image folder names from bracket code (e.g. [NMAIex_1] -> images/NMAIex_1/).
3) Support both reference-style and inline base64 image links.

Quick usage:
1) Scan all markdown files with default config:
    python scripts/extract_markdown_base64_images.py --scan-all
2) Scan all with NMAIex_th naming mode (files will be numbered by sorted order):
    python scripts/extract_markdown_base64_images.py --scan-all --code-mode th
3) Dry-run preview (no file writes):
    python scripts/extract_markdown_base64_images.py --scan-all --dry-run
4) Explicit targets (file/dir/glob):
    python scripts/extract_markdown_base64_images.py docs/research/*.md
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import re
from pathlib import Path
from typing import List, Tuple

# ============================================================================
# USER CONFIG (chinh sua nhanh tai day)
# ============================================================================

# Chon format ma trong ten file:
# - "standard": [NMAIex_1], [NMAIex-2], [NMAIex]
# - "th":       [NMAIex_th] files se duoc danh so theo thu tu tu dien
CODE_FORMAT_MODE = "standard"

# Duong dan mac dinh khi dung --scan-all va --output-root
DEFAULT_RESEARCH_DIR = "docs/research"
DEFAULT_OUTPUT_ROOT = "docs/research/images"

# In toi da bao nhieu file de xem nhanh script dang xu ly gi
PREVIEW_FILE_LIMIT = 12


# ============================================================================
# REGEX / PARSING RULES
# ============================================================================

REF_RE = re.compile(
    r"^\[(?P<label>[^\]]+)\]:\s*<?data:image/(?P<mime>[-+\w.]+);base64,(?P<data>[^>\s]+)>?\s*$"
)
INLINE_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\(\s*data:image/(?P<mime>[-+\w.]+);base64,(?P<data>[^)\s]+)\s*\)"
)
CODE_RE = re.compile(r"\[(?P<code>NMAIex[^\]]*)\]", re.IGNORECASE)
STANDARD_CODE_RE = re.compile(r"(?i)^NMAIex(?:[_-]?(\d+))?$")
TH_CODE_RE = re.compile(r"(?i)^NMAIex[_-]?th(?:[_-]?(\d+))?$")


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


def _folder_from_code(
    md_path: Path,
    code_mode: str,
    th_number: int | None = None,
) -> str:
    """Return short folder name based on bracket code in filename.

    Examples:
    - [NMAIex_1] ...    -> NMAIex_1
    - [NMAIex-2] ...    -> NMAIex_2
    - [NMAIex] ...      -> NMAIex/<doc_stem>
    - [NMAIex_th] ...   -> NMAIex_th_1 (or assigned order)
    - [NMAIex_th_1] ... -> NMAIex_th_1
    """
    match = CODE_RE.search(md_path.name)
    if not match:
        return _safe_stem(md_path)

    raw = match.group("code")

    normalized_mode = code_mode.strip().lower()
    if normalized_mode == "th":
        m = TH_CODE_RE.match(raw)
        if not m:
            return _safe_stem(md_path)

        number = m.group(1)
        if number:
            return f"NMAIex_th_{number}"
        if th_number is not None:
            return f"NMAIex_th_{th_number}"
        return f"NMAIex_th/{_safe_stem(md_path)}"

    m = STANDARD_CODE_RE.match(raw)
    if not m:
        return _safe_stem(md_path)

    number = m.group(1)
    if number:
        return f"NMAIex_{number}"
    return f"NMAIex/{_safe_stem(md_path)}"


def process_markdown(
    md_path: Path,
    output_root: Path,
    write: bool,
    code_mode: str,
    th_number: int | None = None,
) -> Tuple[int, int]:
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=False)

    doc_dir = output_root / _folder_from_code(md_path, code_mode, th_number=th_number)
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


def _build_th_numbering(files: List[Path]) -> dict[str, int]:
    """Assign sequential numbers to NMAIex_th markdown files by sorted order."""
    numbered: dict[str, int] = {}
    counter = 0

    for file_path in files:
        match = CODE_RE.search(file_path.name)
        if not match:
            continue

        raw = match.group("code")
        if not TH_CODE_RE.match(raw):
            continue

        if re.search(r"(?i)^NMAIex[_-]?th[_-]?(\d+)$", raw):
            continue

        counter += 1
        numbered[str(file_path.resolve())] = counter

    return numbered


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
        default=DEFAULT_RESEARCH_DIR,
        help="Root folder used when --scan-all is enabled",
    )
    parser.add_argument(
        "--output-root",
        default=DEFAULT_OUTPUT_ROOT,
        help="Directory to store extracted images",
    )
    parser.add_argument(
        "--code-mode",
        choices=["standard", "th"],
        default=CODE_FORMAT_MODE,
        help="Folder naming mode based on bracket code in filename",
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

    th_numbering = _build_th_numbering(files) if args.code_mode == "th" else {}

    print("=== Config ===")
    print(f"code_mode={args.code_mode}")
    print(f"scan_all={args.scan_all}")
    print(f"research_dir={args.research_dir}")
    print(f"output_root={output_root.as_posix()}")
    print(f"dry_run={args.dry_run}")
    print(f"files_found={len(files)}")

    preview = files[:PREVIEW_FILE_LIMIT]
    if preview:
        print("sample_files:")
        for file_path in preview:
            print(f"  - {file_path.as_posix()}")
        if len(files) > PREVIEW_FILE_LIMIT:
            extra = len(files) - PREVIEW_FILE_LIMIT
            print(f"  ... (+{extra} more)")

    total_ref = 0
    total_inline = 0
    changed_files = 0

    for md_file in files:
        ref_count, inline_count = process_markdown(
            md_file,
            output_root,
            write,
            args.code_mode,
            th_number=th_numbering.get(str(md_file.resolve())),
        )
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
