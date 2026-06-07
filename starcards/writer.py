from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .models import CardDraft, SectionInfo
from .pathing import build_output_path


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_lines(path: Path, lines: list[str]) -> None:
    _ensure_parent(path)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _mcq_line(card: CardDraft) -> str:
    fields = card.extra.get("raw_fields")
    if isinstance(fields, list) and len(fields) >= 11:
        return "|".join(str(field) for field in fields)
    tags = card.extra.get("tags", "")
    why = card.extra.get("why_this_matters", "")
    answer_pattern = card.extra.get("answer_pattern", "1 0 0 0")
    qtype = card.extra.get("qtype", "2")
    return "|".join(
        [
            card.question,
            card.answer,
            *(card.distractors + ["", "", ""])[:3],
            answer_pattern,
            qtype,
            card.source_label,
            "",
            tags,
            why,
        ]
    )


def _cloze_line(card: CardDraft) -> str:
    return f"{card.question}|{card.source_label} cloze|"


def _essay_block(card: CardDraft) -> str:
    payload = card.extra if isinstance(card.extra, dict) else {}
    if not payload:
        payload = {
            "question": card.question,
            "scope": card.extra.get("scope", "") if isinstance(card.extra, dict) else "",
            "model_answer": card.answer,
            "key_terms": card.key_terms,
            "source": card.source_label,
        }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _matching_line(card: CardDraft) -> str:
    fields = card.extra.get("pairs")
    if isinstance(fields, list) and len(fields) >= 9:
        return "|".join(str(field) for field in fields[:9])
    return "|".join([card.question, card.answer, "", "", "", "", "", "", card.source_label])


def _tf_line(card: CardDraft) -> str:
    correction = card.extra.get("correction", "")
    return f"{card.question}|{card.answer}|{correction}|{card.source_label}"


def _scaffold_sequences(cards: list[CardDraft]) -> list[str]:
    grouped: dict[tuple[str, int], list[CardDraft]] = defaultdict(list)
    for card in cards:
        payload = card.extra if isinstance(card.extra, dict) else {}
        sequence = str(payload.get("sequence", card.source_label or "Sequence")).strip() or "Sequence"
        chunk_index = int(payload.get("chunk_index", 0) or 0)
        grouped[(sequence, chunk_index)].append(card)

    rendered: list[str] = []
    for (sequence, _chunk_index), items in grouped.items():
        ordered = sorted(
            items,
            key=lambda item: int((item.extra or {}).get("position", 0)) if isinstance(item.extra, dict) else 0,
        )
        payload: list[dict] = []
        for card in ordered:
            if isinstance(card.extra, dict):
                payload.append(card.extra)
            else:
                payload.append(
                    {
                        "sequence": sequence,
                        "position": len(payload) + 1,
                        "of": len(ordered),
                        "card_type": "node",
                        "question": card.question,
                        "model_answer": card.answer,
                        "key_terms": card.key_terms,
                        "causal_verb": None,
                        "source": card.source_label,
                    }
                )

        for index, item in enumerate(payload):
            prev_item = payload[index - 1] if index > 0 else {}
            next_item = payload[index + 1] if index + 1 < len(payload) else {}
            item["prev_question"] = str(prev_item.get("question", ""))
            item["prev_answer"] = str(prev_item.get("model_answer", ""))
            item["prev_position"] = str(prev_item.get("position", ""))
            item["next_question"] = str(next_item.get("question", ""))
            item["next_answer"] = str(next_item.get("model_answer", ""))
            item["next_position"] = str(next_item.get("position", ""))
        rendered.append(json.dumps(payload, ensure_ascii=False, indent=2))
    return rendered


def write_section_cards(output_dir: Path, section: SectionInfo, cards: list[CardDraft]) -> list[Path]:
    written: list[Path] = []
    by_type: dict[str, list[CardDraft]] = defaultdict(list)
    for card in cards:
        by_type[card.card_type.lower()].append(card)

    for card_type, items in by_type.items():
        suffix = "tf" if card_type == "truefalse" else card_type
        out_path = build_output_path(output_dir, section.ancestors, section.title, suffix)
        if card_type == "mcq":
            _write_lines(out_path, [_mcq_line(card) for card in items])
        elif card_type == "cloze":
            _write_lines(out_path, [_cloze_line(card) for card in items])
        elif card_type == "essay":
            _write_lines(out_path, [_essay_block(card) for card in items])
        elif card_type == "matching":
            _write_lines(out_path, [_matching_line(card) for card in items])
        elif card_type == "truefalse":
            _write_lines(out_path, [_tf_line(card) for card in items])
        elif card_type == "scaffold":
            _write_lines(out_path, ["\n\n===\n\n".join(_scaffold_sequences(items))])
        else:
            _write_lines(out_path, [card.question for card in items])
        written.append(out_path)
    return written
