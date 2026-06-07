from __future__ import annotations

import re
from pathlib import Path


_INVALID_CHARS = re.compile(r'[\\/*?:"<>|]')
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_name(value: str | None, fallback: str = "untitled", limit: int = 60) -> str:
    if value is None:
        return fallback
    text = str(value).replace("\x00", "")
    text = _CONTROL_CHARS.sub("", text)
    text = _INVALID_CHARS.sub("_", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        text = fallback
    return text[:limit]


def camel_case_name(value: str) -> str:
    parts = [p for p in re.split(r"\W+", value) if p]
    return "".join(part[:1].upper() + part[1:] for part in parts) or "UntitledSection"


def build_output_path(output_dir: Path, ancestors: list[str], section_title: str, suffix: str) -> Path:
    folder_parts = [sanitize_name(a) for a in ancestors]
    filename = f"{sanitize_name(camel_case_name(section_title))}_{suffix}.txt"
    return output_dir.joinpath(*folder_parts, filename)


def deck_name_from_path(base_deck: str, base_folder: Path, filepath: Path) -> str:
    rel_path = filepath.relative_to(base_folder)
    parts = list(rel_path.parts)
    filename = parts[-1]
    card_type_match = re.search(r"_(mcq|cloze|essay|matching|scaffold|tf)\.txt$", filename)
    card_type = card_type_match.group(1) if card_type_match else None
    filename = re.sub(r"_(mcq|cloze|essay|matching|scaffold|tf)\.txt$", "", filename)
    parts[-1] = filename
    deck = "::".join([base_deck, *parts])
    if card_type:
        deck = f"{deck}::{card_type}"
    return deck


def deck_name_for_section(base_deck: str, ancestors: list[str], section_title: str, card_type: str | None = None) -> str:
    parts = [sanitize_name(part) for part in ancestors]
    parts.append(sanitize_name(section_title))
    deck = "::".join([base_deck, *parts])
    if card_type:
        deck = f"{deck}::{sanitize_name(card_type)}"
    return deck

