from __future__ import annotations

import argparse
import json
from pathlib import Path

from starcards.models import CardDraft
from starcards.verification import verify_card


def parse_card_file(path: Path) -> list[CardDraft]:
    cards: list[CardDraft] = []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        fields = line.split("|")
        card_type = "mcq"
        if "_cloze" in path.name:
            card_type = "cloze"
        elif "_essay" in path.name:
            card_type = "essay"
        elif "_matching" in path.name:
            card_type = "matching"
        elif "_scaffold" in path.name:
            card_type = "scaffold"
        elif "_tf" in path.name:
            card_type = "truefalse"

        question = fields[0].strip() if fields else ""
        answer = fields[1].strip() if len(fields) > 1 else ""
        cards.append(CardDraft(card_type=card_type, question=question, answer=answer))
    return cards


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify card outputs against source text")
    parser.add_argument("card_file", type=Path)
    parser.add_argument("source_file", type=Path)
    args = parser.parse_args()

    source_text = args.source_file.read_text(encoding="utf-8")
    cards = parse_card_file(args.card_file)
    results = []
    for card in cards:
        result = verify_card(card, source_text)
        results.append(
            {
                "card_type": card.card_type,
                "question": card.question,
                "passed": result.passed,
                "score": result.score,
                "reason": result.reason,
                "evidence": result.evidence,
            }
        )
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

