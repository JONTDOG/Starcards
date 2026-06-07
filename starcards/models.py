from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SectionInfo:
    """A leaf section extracted from the PDF outline."""

    level: int
    title: str
    start_page: int
    end_page: int
    ancestors: list[str] = field(default_factory=list)
    source_text: str = ""
    auto_detected: bool = False
    detection_score: float = 0.0

    @property
    def breadcrumb(self) -> str:
        return " > ".join([*self.ancestors, self.title])


@dataclass(slots=True)
class CardDraft:
    """A generated card before it is exported or imported into Anki."""

    card_type: str
    question: str
    answer: str
    source_label: str = ""
    source_quote: str = ""
    key_terms: list[str] = field(default_factory=list)
    distractors: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VerificationResult:
    """Result of a source-grounding check for a generated card."""

    passed: bool
    score: float
    reason: str
    evidence: str = ""
    reviewer_note: str = ""


@dataclass(slots=True)
class JobConfig:
    """Configuration shared by all jobs."""

    pdf_path: Path
    output_dir: Path
    backend: str = "ollama"
    chapter_filter: str | None = None
    exclude_sections: list[str] = field(default_factory=list)
    skip_pages: int = 0
    generate_mcqs: bool = True
    generate_clozes: bool = True
    generate_truefalse: bool = True
    generate_essays: bool = True
    generate_matching: bool = True
    generate_scaffold: bool = True
    verify_answers: bool = True


@dataclass(slots=True)
class JobResult:
    """Summary of a completed generation or import job."""

    job_id: str
    output_dir: Path
    processed_sections: int = 0
    generated_cards: int = 0
    verified_cards: int = 0
    rejected_cards: int = 0
    notes: list[str] = field(default_factory=list)
