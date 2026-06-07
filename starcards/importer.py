from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from .models import CardDraft, VerificationResult
from .output_tree import IncompleteOutputError, ParsedOutputFile, iter_output_files, parse_text_cards
from .verification import verify_card


class CardSink(Protocol):
    def add_card(self, card: CardDraft, verification: VerificationResult) -> None:
        ...


@dataclass(slots=True)
class ImportSummary:
    file: Path
    card_type: str
    accepted: int = 0
    rejected: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def import_parsed_output(parsed: ParsedOutputFile, source_text: str, sink: CardSink | None = None) -> ImportSummary:
    summary = ImportSummary(file=parsed.path, card_type=parsed.card_type, warnings=list(parsed.warnings))
    for card in parsed.cards:
        verification = verify_card(card, source_text)
        if verification.passed:
            summary.accepted += 1
            if sink is not None:
                sink.add_card(card, verification)
        else:
            summary.rejected += 1
            summary.errors.append(f"{card.question[:80]}: {verification.reason}")
    return summary


def import_output_file(path: Path, source_text: str, sink: CardSink | None = None) -> ImportSummary:
    parsed = parse_text_cards(path)
    return import_parsed_output(parsed, source_text, sink=sink)


def import_output_tree(
    base_folder: Path,
    source_lookup: Callable[[Path], str] | None = None,
    sink: CardSink | None = None,
) -> list[ImportSummary]:
    summaries: list[ImportSummary] = []
    for path in iter_output_files(base_folder):
        try:
            parsed = parse_text_cards(path)
        except IncompleteOutputError as exc:
            summaries.append(
                ImportSummary(
                    file=path,
                    card_type="scaffold" if "_scaffold" in path.name else "unknown",
                    rejected=1,
                    errors=[str(exc)],
                )
            )
            continue

        source_text = ""
        if source_lookup is not None:
            source_text = source_lookup(path) or ""

        summaries.append(import_parsed_output(parsed, source_text, sink=sink))
    return summaries
