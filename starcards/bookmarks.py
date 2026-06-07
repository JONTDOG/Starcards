from __future__ import annotations

from dataclasses import dataclass
from statistics import median
import re
from pathlib import Path
from typing import Iterable

import fitz

from .models import SectionInfo
from .pathing import sanitize_name

@dataclass(slots=True)
class BookmarkEntry:
    level: int
    title: str
    start_page: int
    end_page: int


@dataclass(slots=True)
class TextChunk:
    page_index: int
    y0: float
    text: str
    size: float
    bold: bool


@dataclass(slots=True)
class HeadingCandidate:
    title: str
    page_index: int
    chunk_index: int
    score: float
    size: float
    y0: float


def _normalize_match_text(value: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def _clean_title(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = value.rstrip(":-–—")
    return sanitize_name(value, fallback="untitled", limit=120)


def _is_bold_span(span: dict) -> bool:
    font_name = str(span.get("font", "")).lower()
    flags = int(span.get("flags", 0) or 0)
    return any(token in font_name for token in ("bold", "black", "heavy", "semibold", "demi")) or bool(flags & 16)


def _line_text_and_metrics(line: dict) -> tuple[str, float, bool]:
    pieces: list[str] = []
    sizes: list[float] = []
    bold = False
    for span in line.get("spans", []):
        text = str(span.get("text", "")).strip()
        if not text:
            continue
        pieces.append(text)
        try:
            sizes.append(float(span.get("size", 0.0) or 0.0))
        except Exception:
            sizes.append(0.0)
        bold = bold or _is_bold_span(span)
    return " ".join(pieces).strip(), (max(sizes) if sizes else 0.0), bold


def _collect_text_chunks(doc: fitz.Document, start: int, end: int) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for page_index in range(start, min(end + 1, doc.page_count)):
        page = doc[page_index]
        page_dict = page.get_text("dict")
        blocks = list(page_dict.get("blocks", []))
        blocks.sort(key=lambda block: (block.get("bbox", [0, 0, 0, 0])[1], block.get("bbox", [0, 0, 0, 0])[0]))
        for block in blocks:
            if block.get("type", 0) != 0:
                continue
            lines = list(block.get("lines", []))
            lines.sort(key=lambda line: (line.get("bbox", [0, 0, 0, 0])[1], line.get("bbox", [0, 0, 0, 0])[0]))
            for line in lines:
                text, size, bold = _line_text_and_metrics(line)
                if not text:
                    continue
                chunks.append(
                    TextChunk(
                        page_index=page_index,
                        y0=float(line.get("bbox", [0, 0, 0, 0])[1]),
                        text=text,
                        size=size,
                        bold=bold,
                    )
                )
    return chunks


def _title_like_score(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    uppercase_ratio = sum(1 for ch in letters if ch.isupper()) / len(letters)
    title_case = text == text.title()
    all_caps = uppercase_ratio > 0.8
    score = 0.0
    if title_case:
        score += 1.0
    if all_caps:
        score += 1.0
    if uppercase_ratio > 0.55:
        score += 0.5
    return score


def _heading_candidate_score(text: str, size: float, body_size: float, bold: bool) -> float:
    words = text.split()
    if len(words) == 0 or len(text) > 140:
        return -999.0
    if len(words) > 16:
        return -999.0
    if text.endswith((".", "!", "?")) and len(words) > 4:
        return -999.0
    if text.lower().startswith(("figure ", "table ", "source ", "adapted from", "image ", "link to")):
        return -999.0

    size_delta = max(0.0, size - body_size)
    score = size_delta * 1.8
    if bold:
        score += 1.0
    score += _title_like_score(text)
    if len(words) <= 8:
        score += 0.75
    elif len(words) <= 12:
        score += 0.25
    if ":" in text:
        score += 0.2
    return score


def _split_chunk_range(chunks: list[TextChunk], start_index: int, end_index: int) -> str:
    selected = [chunk.text for chunk in chunks[start_index:end_index] if chunk.text.strip()]
    return "\n".join(selected).strip()


def _detect_auto_headings(
    doc: fitz.Document,
    entry: BookmarkEntry,
    existing_titles: set[str],
) -> list[tuple[HeadingCandidate, int, int]]:
    chunks = _collect_text_chunks(doc, entry.start_page, entry.end_page)
    if not chunks:
        return []

    sizes = [chunk.size for chunk in chunks if chunk.size > 0]
    body_size = float(median(sizes)) if sizes else 0.0
    candidates: list[HeadingCandidate] = []
    seen_by_page: dict[tuple[int, str], float] = {}

    for index, chunk in enumerate(chunks):
        text = _clean_title(chunk.text)
        normalized = _normalize_match_text(text)
        if not text or normalized in existing_titles:
            continue
        if len(text.split()) < 1:
            continue

        score = _heading_candidate_score(text, chunk.size, body_size, chunk.bold)
        if score < 3.0:
            continue

        key = (chunk.page_index, normalized)
        previous_y = seen_by_page.get(key)
        if previous_y is not None and abs(previous_y - chunk.y0) < 24:
            continue
        seen_by_page[key] = chunk.y0

        candidates.append(
            HeadingCandidate(
                title=text,
                page_index=chunk.page_index,
                chunk_index=index,
                score=score,
                size=chunk.size,
                y0=chunk.y0,
            )
        )

    candidates.sort(key=lambda item: (item.page_index, item.y0, -item.score))

    deduped: list[HeadingCandidate] = []
    last_key: tuple[int, str] | None = None
    for candidate in candidates:
        key = (candidate.page_index, _normalize_match_text(candidate.title))
        if key == last_key:
            continue
        last_key = key
        deduped.append(candidate)

    results: list[tuple[HeadingCandidate, int, int]] = []
    for index, candidate in enumerate(deduped):
        next_index = deduped[index + 1].chunk_index if index + 1 < len(deduped) else len(chunks)
        if next_index <= candidate.chunk_index:
            continue
        segment_text = _split_chunk_range(chunks, candidate.chunk_index, next_index)
        if not segment_text:
            continue
        next_page = deduped[index + 1].page_index if index + 1 < len(deduped) else entry.end_page
        results.append((candidate, candidate.page_index, max(candidate.page_index, next_page)))
    return results


def extract_toc_with_end_pages(doc: fitz.Document, skip_pages: int = 0) -> list[BookmarkEntry]:
    raw = doc.get_toc()
    total = doc.page_count
    entries: list[BookmarkEntry] = []

    for i, (level, title, page) in enumerate(raw):
        end_page = total - 1
        for j in range(i + 1, len(raw)):
            if raw[j][0] <= level:
                end_page = raw[j][2] - 2
                break

        entries.append(
            BookmarkEntry(
                level=level,
                title=sanitize_name(title),
                start_page=max(page - 1, skip_pages),
                end_page=end_page,
            )
        )

    return entries


def is_leaf(index: int, entries: list[BookmarkEntry]) -> bool:
    return index + 1 >= len(entries) or entries[index + 1].level <= entries[index].level


def ancestor_titles(index: int, entries: list[BookmarkEntry]) -> list[str]:
    chain: list[str] = []
    target_level = entries[index].level
    for j in range(index - 1, -1, -1):
        if entries[j].level < target_level:
            chain.insert(0, entries[j].title)
            target_level = entries[j].level
    return chain


def extract_section_text(doc: fitz.Document, start: int, end: int, heading: str | None = None) -> str:
    heading_norm = _normalize_match_text(heading or "")
    parts: list[str] = []

    if heading_norm:
        for page_index in range(start, min(end + 1, doc.page_count)):
            page = doc[page_index]
            blocks = page.get_text("blocks", sort=True)
            page_parts: list[str] = []
            heading_found = False

            for block in blocks:
                text = str(block[4]).strip() if len(block) > 4 else ""
                if not text:
                    continue

                block_norm = _normalize_match_text(text)
                if not heading_found and heading_norm in block_norm:
                    heading_found = True
                    raw_index = text.lower().find((heading or "").lower())
                    if raw_index >= 0:
                        text = text[raw_index:]
                    page_parts.append(text)
                    continue

                if heading_found:
                    page_parts.append(text)

            if heading_found:
                parts.append("\n".join(page_parts))
                for following_index in range(page_index + 1, min(end + 1, doc.page_count)):
                    parts.append(doc[following_index].get_text("text"))
                return "\n".join(parts).strip()

    for page_index in range(start, min(end + 1, doc.page_count)):
        parts.append(doc[page_index].get_text("text"))
    return "\n".join(parts).strip()


def _extract_auto_section_text(doc: fitz.Document, entry: BookmarkEntry, candidate: HeadingCandidate, following_candidate: HeadingCandidate | None) -> str:
    chunks = _collect_text_chunks(doc, entry.start_page, entry.end_page)
    if not chunks:
        return ""
    end_index = following_candidate.chunk_index if following_candidate is not None else len(chunks)
    return _split_chunk_range(chunks, candidate.chunk_index, end_index)


def is_excluded(title: str, exclude_sections: Iterable[str]) -> bool:
    title_lower = title.lower()
    return any(excluded.lower() in title_lower for excluded in exclude_sections)


def section_filter_match(section: SectionInfo, chapter_filter: str | None) -> bool:
    if not chapter_filter:
        return True
    needle = chapter_filter.lower()
    return any(needle in ancestor.lower() for ancestor in section.ancestors) or needle in section.title.lower()


def build_sections(pdf_path: Path, skip_pages: int = 0, include_auto_headings: bool = True) -> list[SectionInfo]:
    doc = fitz.open(str(pdf_path))
    try:
        entries = extract_toc_with_end_pages(doc, skip_pages=skip_pages)
        sections: list[SectionInfo] = []
        bookmark_titles = {_normalize_match_text(entry.title) for entry in entries}
        for index, entry in enumerate(entries):
            if not is_leaf(index, entries):
                continue
            ancestors = ancestor_titles(index, entries)
            leaf_section = SectionInfo(
                level=entry.level,
                title=entry.title,
                start_page=entry.start_page,
                end_page=entry.end_page,
                ancestors=ancestors,
                source_text=extract_section_text(doc, entry.start_page, entry.end_page, heading=entry.title),
                auto_detected=False,
            )
            sections.append(leaf_section)

            if not include_auto_headings:
                continue

            auto_candidates = _detect_auto_headings(doc, entry, bookmark_titles)
            for auto_index, (candidate, start_page, end_page) in enumerate(auto_candidates):
                next_candidate = auto_candidates[auto_index + 1][0] if auto_index + 1 < len(auto_candidates) else None
                auto_text = _extract_auto_section_text(doc, entry, candidate, next_candidate)
                if not auto_text.strip():
                    continue
                sections.append(
                    SectionInfo(
                        level=entry.level + 1,
                        title=candidate.title,
                        start_page=start_page,
                        end_page=end_page,
                        ancestors=[*ancestors, entry.title],
                        source_text=auto_text,
                        auto_detected=True,
                        detection_score=candidate.score,
                    )
                )
        return sections
    finally:
        doc.close()


