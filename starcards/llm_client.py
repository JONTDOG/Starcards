from __future__ import annotations

import html
import json
import re
import time
from dataclasses import dataclass
from typing import Any

from .models import CardDraft, SectionInfo
from .prompts import PROMPT_D, PROMPT_E, PROMPT_F, PROMPT_G, PROMPT_H, PROMPT_I, VERIFY_PROMPT


@dataclass(slots=True)
class LLMSettings:
    backend: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    sambanova_api_key: str = ""
    sambanova_model: str = "gpt-oss-120b"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    cerebras_api_key: str = ""
    cerebras_model: str = "qwen-3-235b-a22b-instruct-2507"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_delay: int = 10
    gemini_retries: int = 5
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5"
    github_token: str = ""
    github_model: str = "gpt-4o"
    use_linguistic_annotation: bool = False
    verify_answers: bool = True


_CLOZE_KEEP_RE = re.compile(r"\{\{c1::.*?\}\}")


def _clean_lines(raw: str) -> str:
    lines: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("```") or stripped.endswith("```"):
            continue
        lines.append(stripped)
    return "\n".join(lines).strip()


def _clean_mcq_output(raw: str) -> str:
    cleaned = []
    for line in _clean_lines(raw).splitlines():
        if line.startswith("AutoSubsection"):
            continue
        if line.startswith("Question |") or line.startswith("Question|"):
            continue
        if "|" not in line:
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _clean_cloze_output(raw: str) -> str:
    cleaned = []
    for line in _clean_lines(raw).splitlines():
        if "{{c1::" not in line:
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _clean_simple_output(raw: str) -> str:
    return _clean_lines(raw)


def _parse_pipe_line(line: str) -> list[str]:
    return [field.strip() for field in line.split("|")]


def _parse_json_blocks(raw: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for block in [block.strip() for block in raw.split("---") if block.strip()]:
        obj = json.loads(block)
        if isinstance(obj, dict):
            payloads.append(obj)
    return payloads


def _parse_scaffold_blocks(raw: str) -> list[list[dict[str, Any]]]:
    sequences: list[list[dict[str, Any]]] = []
    for block in [block.strip() for block in raw.split("===") if block.strip()]:
        cleaned = re.sub(r"```(?:json)?", "", block).strip()
        payload = json.loads(cleaned)
        if isinstance(payload, list):
            sequences.append(payload)
    return sequences


def _chunk_text(text: str, max_chars: int = 3500) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for paragraph in paragraphs:
        addition = len(paragraph) + 2
        if current and current_len + addition > max_chars:
            chunks.append("\n\n".join(current))
            current = [paragraph]
            current_len = len(paragraph)
        else:
            current.append(paragraph)
            current_len += addition
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _add_scaffold_reveal_buttons(sequence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    updated: list[dict[str, Any]] = []
    for card in sequence:
        if not isinstance(card, dict):
            continue
        model_answer = str(card.get("model_answer", "") or "").strip()
        escaped_answer = html.escape(model_answer)
        card = dict(card)
        card["reveal_button_label"] = "Reveal model answer"
        card["reveal_html"] = (
            '<details class="model-answer-reveal">'
            '<summary>Reveal model answer</summary>'
            f'<div class="model-answer-body">{escaped_answer}</div>'
            "</details>"
        )
        updated.append(card)
    return updated


class StarCardsLLMClient:
    def __init__(self, settings: LLMSettings):
        self.settings = settings

    def _check_ollama(self) -> bool:
        import requests

        r = requests.get(f"{self.settings.ollama_url}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        base = self.settings.ollama_model.split(":")[0]
        return any(base in model for model in models)

    def call_raw(self, prompt: str) -> str:
        backend = self.settings.backend
        if backend == "ollama":
            import requests

            r = requests.post(
                f"{self.settings.ollama_url}/api/generate",
                json={
                    "model": self.settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 8192},
                },
                timeout=600,
            )
            r.raise_for_status()
            return r.json()["response"].strip()

        if backend == "groq":
            from groq import Groq

            client = Groq(api_key=self.settings.groq_api_key)
            response = client.chat.completions.create(
                model=self.settings.groq_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=8192,
            )
            return response.choices[0].message.content.strip()

        if backend == "sambanova":
            from openai import OpenAI

            client = OpenAI(base_url="https://api.sambanova.ai/v1", api_key=self.settings.sambanova_api_key)
            response = client.chat.completions.create(
                model=self.settings.sambanova_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=16384,
            )
            return response.choices[0].message.content.strip()

        if backend == "openai":
            from openai import OpenAI

            client = OpenAI(api_key=self.settings.openai_api_key)
            response = client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=8192,
            )
            return response.choices[0].message.content.strip()

        if backend == "cerebras":
            from cerebras.cloud.sdk import Cerebras

            client = Cerebras(api_key=self.settings.cerebras_api_key)
            response = client.chat.completions.create(
                model=self.settings.cerebras_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=8192,
            )
            return response.choices[0].message.content.strip()

        if backend == "gemini":
            from google import genai

            for attempt in range(1, self.settings.gemini_retries + 1):
                try:
                    client = genai.Client(api_key=self.settings.gemini_api_key)
                    response = client.models.generate_content(model=self.settings.gemini_model, contents=prompt)
                    return response.text.strip()
                except Exception as exc:
                    error_str = str(exc)
                    retry_match = re.search(r"retry_delay\s*\{[^}]*seconds:\s*(\d+)", error_str)
                    suggested = int(retry_match.group(1)) if retry_match else None
                    if "429" in error_str or "quota" in error_str.lower():
                        if "GenerateRequestsPerDayPerProjectPerModel" in error_str:
                            raise RuntimeError("DAILY QUOTA EXHAUSTED. Rerun tomorrow after midnight Pacific time.") from exc
                        wait = (suggested + 5) if suggested else 65
                        time.sleep(wait)
                        continue
                    raise
            raise RuntimeError(f"Gemini failed after {self.settings.gemini_retries} retries.")

        if backend == "anthropic":
            import anthropic

            client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
            message = client.messages.create(
                model=self.settings.anthropic_model,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text.strip()

        if backend == "github":
            from openai import OpenAI

            client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=self.settings.github_token)
            response = client.chat.completions.create(
                model=self.settings.github_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=8192,
            )
            return response.choices[0].message.content.strip()

        raise ValueError(
            f"Unknown BACKEND '{backend}'. Use ollama/groq/cerebras/gemini/anthropic/github/openai."
        )

    def _section_label(self, section: SectionInfo) -> str:
        return "".join(part[:1].upper() + part[1:] for part in re.split(r"\W+", section.title) if part) or "UntitledSection"

    def generate_mcq(self, section: SectionInfo) -> list[CardDraft]:
        raw = self.call_raw(PROMPT_D + section.source_text)
        cleaned = _clean_mcq_output(raw)
        cards: list[CardDraft] = []
        for line in cleaned.splitlines():
            fields = _parse_pipe_line(line)
            if len(fields) < 11:
                continue
            cards.append(
                CardDraft(
                    card_type="mcq",
                    question=fields[0],
                    answer=fields[1],
                    source_label=fields[7],
                    distractors=fields[2:5],
                    extra={
                        "answer_pattern": fields[5],
                        "qtype": fields[6],
                        "tags": fields[9],
                        "why_this_matters": fields[10],
                    },
                )
            )
        return cards

    def generate_cloze(self, section: SectionInfo) -> list[CardDraft]:
        raw = self.call_raw(PROMPT_E + section.source_text)
        cleaned = _clean_cloze_output(raw)
        cards: list[CardDraft] = []
        for line in cleaned.splitlines():
            fields = _parse_pipe_line(line)
            if len(fields) < 2:
                continue
            cards.append(
                CardDraft(
                    card_type="cloze",
                    question=fields[0],
                    answer=fields[0],
                    source_label=fields[1],
                    extra={"raw_fields": fields},
                )
            )
        return cards

    def generate_essay(self, section: SectionInfo) -> list[CardDraft]:
        raw = self.call_raw(PROMPT_F + section.source_text)
        cards: list[CardDraft] = []
        for obj in _parse_json_blocks(raw):
            cards.append(
                CardDraft(
                    card_type="essay",
                    question=str(obj.get("question", "")).strip(),
                    answer=str(obj.get("model_answer", "")).strip(),
                    source_label=str(obj.get("source", "")).strip(),
                    key_terms=[str(term).strip() for term in obj.get("key_terms", []) if str(term).strip()],
                    extra=obj,
                )
            )
        return cards

    def generate_matching(self, section: SectionInfo) -> list[CardDraft]:
        raw = self.call_raw(PROMPT_G + section.source_text)
        cards: list[CardDraft] = []
        for line in _clean_simple_output(raw).splitlines():
            fields = _parse_pipe_line(line)
            if len(fields) < 9:
                continue
            cards.append(
                CardDraft(
                    card_type="matching",
                    question=fields[0],
                    answer=fields[4],
                    source_label=fields[8],
                    extra={"pairs": fields},
                )
            )
        return cards

    def generate_scaffold(self, section: SectionInfo) -> list[CardDraft]:
        cards: list[CardDraft] = []
        for chunk_index, chunk in enumerate(_chunk_text(section.source_text, max_chars=3500), start=1):
            chunk_prompt = (
                "Generate a compact scaffold sequence from this excerpt only. "
                "Prefer 1-2 sequences and keep the output small enough to avoid truncation.\n\n"
                + PROMPT_H
                + chunk
            )
            raw = self.call_raw(chunk_prompt)
            for sequence in _parse_scaffold_blocks(raw):
                sequence = _add_scaffold_reveal_buttons(sequence)
                for obj in sequence:
                    payload = dict(obj)
                    payload["chunk_index"] = chunk_index
                    cards.append(
                        CardDraft(
                            card_type="scaffold",
                            question=str(payload.get("question", "")).strip(),
                            answer=str(payload.get("model_answer", "")).strip(),
                            source_label=str(payload.get("source", "")).strip(),
                            key_terms=[str(term).strip() for term in payload.get("key_terms", []) if str(term).strip()],
                            extra=payload,
                        )
                    )
        return cards

    def generate_truefalse(self, section: SectionInfo) -> list[CardDraft]:
        raw = self.call_raw(PROMPT_I + section.source_text)
        cards: list[CardDraft] = []
        for line in _clean_simple_output(raw).splitlines():
            fields = _parse_pipe_line(line)
            if len(fields) < 4:
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
        return cards

    def generate_cards(self, section: SectionInfo, card_types: list[str]) -> list[CardDraft]:
        cards: list[CardDraft] = []
        requested = [card_type.lower() for card_type in card_types]
        if "mcq" in requested:
            cards.extend(self.generate_mcq(section))
        if "cloze" in requested:
            cards.extend(self.generate_cloze(section))
        if "essay" in requested:
            cards.extend(self.generate_essay(section))
        if "matching" in requested:
            cards.extend(self.generate_matching(section))
        if "scaffold" in requested:
            cards.extend(self.generate_scaffold(section))
        if "truefalse" in requested or "tf" in requested:
            cards.extend(self.generate_truefalse(section))
        return cards
