from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from .models import CardDraft, VerificationResult


_WHITESPACE = re.compile(r"\s+")
_CLOZE_RE = re.compile(r"\{\{c1::(.*?)\}\}")


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return _WHITESPACE.sub(" ", text).strip()


def token_overlap(a: str, b: str) -> float:
    a_tokens = set(normalize(a).split())
    b_tokens = set(normalize(b).split())
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)


def best_quote_match(answer: str, source_text: str) -> tuple[str, float]:
    source_lines = [line.strip() for line in source_text.splitlines() if line.strip()]
    if not source_lines:
        return "", 0.0

    best_line = ""
    best_score = 0.0
    for line in source_lines:
        ratio = SequenceMatcher(None, normalize(answer), normalize(line)).ratio()
        overlap = token_overlap(answer, line)
        score = max(ratio, overlap)
        if score > best_score:
            best_score = score
            best_line = line
    return best_line, best_score


def extract_cloze_answer(text: str) -> str:
    match = _CLOZE_RE.search(text)
    return match.group(1).strip() if match else ""


def verify_mcq(card: CardDraft, source_text: str) -> VerificationResult:
    quote, score = best_quote_match(card.answer, source_text)
    if score >= 0.55:
        return VerificationResult(True, score, "Correct answer is grounded in the source text.", quote)
    return VerificationResult(False, score, "Correct answer is not well supported by the source text.", quote)


def verify_cloze(card: CardDraft, source_text: str) -> VerificationResult:
    answer = extract_cloze_answer(card.question) or card.answer
    if not answer:
        return VerificationResult(False, 0.0, "Cloze answer could not be extracted.")

    normalized_source = normalize(source_text)
    normalized_answer = normalize(answer)
    if normalized_answer and normalized_answer in normalized_source:
        quote, score = best_quote_match(answer, source_text)
        return VerificationResult(True, max(score, 0.75), "Cloze answer appears in the source text.", quote)

    quote, score = best_quote_match(answer, source_text)
    if score >= 0.65:
        return VerificationResult(True, score, "Cloze answer is strongly paraphrase-supported by the source text.", quote)
    return VerificationResult(False, score, "Cloze answer is not directly supported by the source text.", quote)


def verify_truefalse(card: CardDraft, source_text: str) -> VerificationResult:
    quote, score = best_quote_match(card.question, source_text)
    if score >= 0.5:
        return VerificationResult(True, score, "Statement is supported by the source text.", quote)

    correction_quote, correction_score = best_quote_match(card.answer, source_text)
    if correction_score >= 0.5:
        return VerificationResult(True, correction_score, "Correction is supported by the source text.", correction_quote)

    return VerificationResult(False, max(score, correction_score), "Neither the statement nor the correction is well grounded.", quote or correction_quote)


def verify_matching(card: CardDraft, source_text: str) -> VerificationResult:
    terms = [term.strip() for term in card.extra.get("pairs", []) if term and term.strip()]
    if not terms:
        return VerificationResult(False, 0.0, "Matching card does not contain pair data.")

    scores = []
    quotes = []
    for term in terms:
        quote, score = best_quote_match(term, source_text)
        scores.append(score)
        if quote:
            quotes.append(quote)
    score = sum(scores) / len(scores)
    if score >= 0.5:
        return VerificationResult(True, score, "Matching pairs are supported by the source text.", " | ".join(quotes[:3]))
    return VerificationResult(False, score, "Matching pairs are not sufficiently grounded.", " | ".join(quotes[:3]))


def verify_essay(card: CardDraft, source_text: str) -> VerificationResult:
    if not card.key_terms:
        return VerificationResult(False, 0.0, "Essay card does not include key terms.")

    hits = 0
    quotes = []
    for term in card.key_terms:
        quote, score = best_quote_match(term, source_text)
        if score >= 0.45:
            hits += 1
            if quote:
                quotes.append(quote)

    score = hits / len(card.key_terms)
    if score >= 0.6:
        return VerificationResult(True, score, "Essay key terms are grounded in the source text.", " | ".join(quotes[:3]))
    return VerificationResult(False, score, "Too many essay key terms are unsupported by the source text.", " | ".join(quotes[:3]))


def verify_card(card: CardDraft, source_text: str) -> VerificationResult:
    card_type = card.card_type.lower()
    if card_type == "mcq":
        return verify_mcq(card, source_text)
    if card_type == "cloze":
        return verify_cloze(card, source_text)
    if card_type == "truefalse":
        return verify_truefalse(card, source_text)
    if card_type == "matching":
        return verify_matching(card, source_text)
    if card_type == "essay":
        return verify_essay(card, source_text)
    if card_type == "scaffold":
        return verify_essay(card, source_text)
    return VerificationResult(False, 0.0, f"Unknown card type: {card.card_type}")

