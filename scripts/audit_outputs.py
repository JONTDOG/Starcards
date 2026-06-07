from __future__ import annotations

import argparse
import json
from pathlib import Path

from starcards.output_tree import IncompleteOutputError, iter_output_files, parse_text_cards
from starcards.verification import verify_card


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit generated StarCards output files")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("source_dir", type=Path, nargs="?")
    args = parser.parse_args()

    report = []
    for path in iter_output_files(args.output_dir):
        try:
            parsed = parse_text_cards(path)
        except IncompleteOutputError as exc:
            report.append(
                {
                    "file": str(path),
                    "status": "incomplete",
                    "reason": str(exc),
                }
            )
            continue

        source_text = ""
        if args.source_dir:
            source_candidate = args.source_dir / path.relative_to(args.output_dir)
            if source_candidate.exists():
                source_text = source_candidate.read_text(encoding="utf-8")

        file_result = {
            "file": str(path),
            "card_type": parsed.card_type,
            "warnings": parsed.warnings,
            "cards": [],
        }
        for card in parsed.cards:
            if source_text:
                result = verify_card(card, source_text)
                file_result["cards"].append(
                    {
                        "question": card.question,
                        "passed": result.passed,
                        "score": result.score,
                        "reason": result.reason,
                    }
                )
            else:
                file_result["cards"].append(
                    {
                        "question": card.question,
                        "passed": None,
                        "score": None,
                        "reason": "No source text supplied for verification.",
                    }
                )
        report.append(file_result)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
