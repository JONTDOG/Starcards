from __future__ import annotations

import argparse
from pathlib import Path

from starcards.bookmarks import build_sections


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect leaf-level PDF sections")
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--skip-pages", type=int, default=0)
    args = parser.parse_args()

    sections = build_sections(args.pdf_path, skip_pages=args.skip_pages)
    for section in sections:
        print(f"{section.breadcrumb} | pages {section.start_page + 1}-{section.end_page + 1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

