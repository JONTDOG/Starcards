from __future__ import annotations

import argparse
from pathlib import Path

from starcards.llm_client import LLMSettings, StarCardsLLMClient
from starcards.models import JobConfig
from starcards.pipeline import StarCardsPipeline
from starcards.writer import write_section_cards


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate StarCards outputs from a PDF")
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--backend", default="ollama")
    parser.add_argument("--chapter-filter", default=None)
    parser.add_argument("--skip-pages", type=int, default=0)
    parser.add_argument("--card-types", nargs="+", default=["mcq", "cloze", "essay", "matching", "scaffold", "truefalse"])
    parser.add_argument("--verify", dest="verify", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    settings = LLMSettings(backend=args.backend, verify_answers=args.verify)
    client = StarCardsLLMClient(settings)
    config = JobConfig(
        pdf_path=args.pdf_path,
        output_dir=args.output_dir,
        backend=args.backend,
        chapter_filter=args.chapter_filter,
        skip_pages=args.skip_pages,
        verify_answers=args.verify,
    )
    pipeline = StarCardsPipeline(config, client)

    sections = pipeline.load_sections()
    print(f"Sections found: {len(sections)}")
    total_written = 0
    total_verified = 0
    total_rejected = 0

    for section in sections:
        print(section.breadcrumb)
        cards = client.generate_cards(section, args.card_types)
        if config.verify_answers:
            verified_cards = []
            from starcards.verification import verify_card

            for card in cards:
                result = verify_card(card, section.source_text)
                card.extra["verification"] = {
                    "passed": result.passed,
                    "score": result.score,
                    "reason": result.reason,
                    "evidence": result.evidence,
                }
                if result.passed:
                    verified_cards.append(card)
                    total_verified += 1
                else:
                    total_rejected += 1
            cards = verified_cards
        written = write_section_cards(args.output_dir, section, cards)
        total_written += len(written)
        for path in written:
            print(f"  wrote {path}")

    print(f"Done. files_written={total_written} verified_cards={total_verified} rejected_cards={total_rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
