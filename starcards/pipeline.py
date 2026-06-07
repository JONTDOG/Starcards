from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .bookmarks import build_sections, is_excluded, section_filter_match
from .models import CardDraft, JobConfig, JobResult, SectionInfo
from .verification import verify_card


class LLMClient(Protocol):
    def generate_cards(self, section: SectionInfo, card_types: list[str]) -> list[CardDraft]:
        ...


@dataclass(slots=True)
class PipelineReport:
    job: JobResult
    sections: list[SectionInfo] = field(default_factory=list)
    verified_cards: list[CardDraft] = field(default_factory=list)
    rejected_cards: list[CardDraft] = field(default_factory=list)


class StarCardsPipeline:
    """Shared backend workflow for generation and verification."""

    def __init__(self, config: JobConfig, llm_client: LLMClient):
        self.config = config
        self.llm_client = llm_client

    def load_sections(self) -> list[SectionInfo]:
        sections = build_sections(self.config.pdf_path, skip_pages=self.config.skip_pages)
        filtered: list[SectionInfo] = []
        for section in sections:
            if is_excluded(section.title, self.config.exclude_sections):
                continue
            if not section_filter_match(section, self.config.chapter_filter):
                continue
            filtered.append(section)
        return filtered

    def run(self, card_types: list[str]) -> PipelineReport:
        sections = self.load_sections()
        job = JobResult(job_id=self.config.pdf_path.stem, output_dir=self.config.output_dir)
        verified_cards: list[CardDraft] = []
        rejected_cards: list[CardDraft] = []

        for section in sections:
            job.processed_sections += 1
            drafts = self.llm_client.generate_cards(section, card_types)
            job.generated_cards += len(drafts)
            for draft in drafts:
                if not self.config.verify_answers:
                    verified_cards.append(draft)
                    job.verified_cards += 1
                    continue

                result = verify_card(draft, section.source_text)
                draft.extra["verification"] = {
                    "passed": result.passed,
                    "score": result.score,
                    "reason": result.reason,
                    "evidence": result.evidence,
                }
                if result.passed:
                    verified_cards.append(draft)
                    job.verified_cards += 1
                else:
                    rejected_cards.append(draft)
                    job.rejected_cards += 1
                    job.notes.append(f"{section.breadcrumb}: {result.reason}")

        return PipelineReport(job=job, sections=sections, verified_cards=verified_cards, rejected_cards=rejected_cards)

