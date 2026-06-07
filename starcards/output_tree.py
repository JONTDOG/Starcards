from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .models import CardDraft


CARD_SUFFIXES = ("mcq", "cloze", "essay", "matching", "scaffold", "tf")


class OutputParseError(ValueError):
    """Raised when a generated output file cannot be parsed."""


class IncompleteOutputError(OutputParseError):
    """Raised when a model output is likely truncated mid-response."""


@dataclass(slots=True)
class ParsedOutputFile:
    path: Path
    card_type: str
    cards: list[CardDraft]
    warnings: list[str]


def card_type_from_filename(filename: str) -> str:
    for suffix in CARD_SUFFIXES:
        if filename.endswith(f"_{suffix}.txt"):
            return suffix
    return "mcq"


def _parse_line_fields(line: str) -> list[str]:
    return [field.strip() for field in line.split("|")]


def parse_text_cards(path: Path) -> ParsedOutputFile:
    text = path.read_text(encoding="utf-8")
    card_type = card_type_from_filename(path.name)
    cards: list[CardDraft] = []
    warnings: list[str] = []

    if card_type == "tf":
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            fields = _parse_line_fields(line)
            if len(fields) < 4:
                warnings.append(f"Skipped malformed true/false line in {path.name}")
                continue
            cards.append(
                CardDraft(
                    card_type="truefalse",
                    question=fields[0],
                    answer=fields[1],
                    source_label=fields[3],
                    extra={"correction": fields[2]},
                )
            )
        return ParsedOutputFile(path=path, card_type=card_type, cards=cards, warnings=warnings)

    if card_type == "scaffold":
        blocks = [block.strip() for block in text.split("===") if block.strip()]
        for block_index, block in enumerate(blocks):
            cleaned = re.sub(r"```(?:json)?", "", block).strip()
            try:
                payload = json.loads(cleaned)
            except json.JSONDecodeError as exc:
                warnings.append(
                    f"Truncated or invalid scaffold JSON in {path.name} block {block_index + 1}: {exc.msg}"
                )
                raise IncompleteOutputError(warnings[-1]) from exc

            if not isinstance(payload, list):
                warnings.append(f"Skipped non-list scaffold block in {path.name} block {block_index + 1}")
                continue

            for item in payload:
                if not isinstance(item, dict):
                    continue
                cards.append(
                    CardDraft(
                        card_type="scaffold",
                        question=str(item.get("question", "")).strip(),
                        answer=str(item.get("model_answer", "")).strip(),
                        source_label=str(item.get("source", "")).strip(),
                        key_terms=[str(term).strip() for term in item.get("key_terms", []) if str(term).strip()],
                        extra=item,
                    )
                )
        return ParsedOutputFile(path=path, card_type=card_type, cards=cards, warnings=warnings)

    for line in text.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        fields = _parse_line_fields(line)
        if card_type == "cloze":
            cards.append(
                CardDraft(
                    card_type="cloze",
                    question=fields[0],
                    answer=fields[0],
                    source_label=fields[1] if len(fields) > 1 else "",
                )
            )
        elif card_type == "essay":
            cards.append(
                CardDraft(
                    card_type="essay",
                    question=fields[0] if fields else "",
                    answer=fields[2] if len(fields) > 2 else "",
                    source_label=fields[4] if len(fields) > 4 else "",
                    key_terms=[term.strip() for term in (fields[3] if len(fields) > 3 else "").split(";") if term.strip()],
                )
            )
        elif card_type == "matching":
            pairs = [field for field in fields if field]
            cards.append(
                CardDraft(
                    card_type="matching",
                    question=fields[0] if fields else "",
                    answer=fields[1] if len(fields) > 1 else "",
                    source_label=fields[-1] if fields else "",
                    extra={"pairs": pairs},
                )
            )
        else:
            cards.append(
                CardDraft(
                    card_type="mcq",
                    question=fields[0] if fields else "",
                    answer=fields[1] if len(fields) > 1 else "",
                    source_label=fields[7] if len(fields) > 7 else "",
                    distractors=fields[2:5] if len(fields) > 4 else [],
                    extra={"raw_fields": fields},
                )
            )

    return ParsedOutputFile(path=path, card_type=card_type, cards=cards, warnings=warnings)


def iter_output_files(base_folder: Path):
    for path in sorted(base_folder.rglob("*.txt")):
        yield path

