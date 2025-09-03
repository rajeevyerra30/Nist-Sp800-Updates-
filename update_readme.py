#!/usr/bin/env python3
"""
update_readme.py
- Auto-finds your summary (supports .me/.md in 'source code' or docs/)
- Writes docs/latest-sp800-summary.md
- Updates README.md by replacing a marked block
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import sys, re

START = "<!-- START:LATEST_SP800_SUMMARY -->"
END   = "<!-- END:LATEST_SP800_SUMMARY -->"
PREVIEW_LINES = 200

def repo_root(start: Path) -> Path:
    p = start.resolve()
    for _ in range(10):
        if (p / ".git").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    return start.resolve()

def autodetect_summary(root: Path) -> Path | None:
    # Prefer canonical docs file
    cand = root / "docs" / "latest-sp800-summary.md"
    if cand.exists(): return cand

    # Common locations/names
    candidates = [
        root / "source code" / "_sp800_updates.me",
        root / "source code" / "latest-sp800-summary.md",
        root / "source code" / "summary.md",
        root / "docs" / "summary.md",
        root / "docs" / "sp800_summary.md",
        root / "latest-sp800-summary.md",
        root / "summary.md",
    ]
    for c in candidates:
        if c.exists():
            return c

    # Broad glob search
    globs = [
        "docs/*summary*.md", "docs/*sp800*.md",
        "source code/*summary*.*", "source code/*sp800*.*",
        "*summary*.md", "*sp800*.md", "*sp800*.*",
    ]
    for pat in globs:
        for c in root.glob(pat):
            if c.is_file():
                return c
    return None

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def update_readme_block(readme: Path, full_md_path: Path, content: str) -> None:
    base = readme.read_text(encoding="utf-8")
    preview = "\n".join([ln.rstrip() for ln in content.splitlines()][:PREVIEW_LINES]).strip()
    stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    block = (
        f"{START}\n\n"
        f"## Latest NIST SP 800 Summary\n"
        f"_Last updated: {stamp}_  ·  "
        f"[Open as a standalone file]({full_md_path.as_posix()})\n\n"
        f"<details>\n"
        f"<summary>Preview (first {PREVIEW_LINES} lines)</summary>\n\n"
        f"{preview}\n\n"
        f"</details>\n\n"
        f"{END}"
    )
    if START in base and END in base:
        base = re.sub(re.escape(START)+r".*?"+re.escape(END), block, base, flags=re.DOTALL)
    else:
        base = base.rstrip() + "\n\n" + block + "\n"
    write(readme, base)

def main():
    root = repo_root(Path.cwd())
    readme = root / "README.md"
    if not readme.exists():
        sys.exit("README.md not found at repo root.")

    # 1) Choose input: use argv if valid, otherwise auto-detect
    src_arg = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    if src_arg and not src_arg.exists():
        print(f"⚠️  Provided path not found: {src_arg}")
        src_arg = None

    src = src_arg or autodetect_summary(root)
    if not src:
        # Print some hints before exiting
        print("❌ Could not find a summary file.")
        print("Look for something like:")
        print("  - source code/_sp800_updates.me")
        print("  - source code/*summary*.md  or  *sp800*.md")
        print("  - docs/*summary*.md  or  *sp800*.md")
        sys.exit(1)

    print(f"Using summary source: {src}")

    # 2) Read and write canonical docs/latest-sp800-summary.md
    content = read(src)
    canonical = root / "docs" / "latest-sp800-summary.md"
    write(canonical, content)
    print(f"Wrote full summary to: {canonical}")

    # 3) Update README block (with preview + link)
    update_readme_block(readme, canonical, content)
    print("README.md updated with summary preview and link.")

if __name__ == "__main__":
    main()
