from __future__ import annotations

import tempfile
import re
from pathlib import Path

import streamlit as st

from starcards.apkg_exporter import export_apkg
from starcards.bookmarks import build_sections
from starcards.llm_client import LLMSettings, StarCardsLLMClient
from starcards.verification import verify_card
from starcards.writer import write_section_cards


st.set_page_config(page_title="StarCards", layout="wide")


def _inject_css() -> None:
    st.markdown(
        """
        <style>
          .stApp {
            background: radial-gradient(circle at top, #121826 0%, #090c14 55%, #05070c 100%);
            color: #f4f7fb;
          }
          .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2.5rem;
            max-width: 1500px;
          }
          .starcards-hero {
            padding: 1.4rem 1.5rem;
            border-radius: 24px;
            background: linear-gradient(135deg, rgba(25, 35, 58, 0.92), rgba(11, 16, 27, 0.98));
            border: 1px solid rgba(142, 197, 255, 0.18);
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
            margin-bottom: 1rem;
          }
          .starcards-kicker {
            display: inline-flex;
            gap: 0.5rem;
            align-items: center;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: rgba(74, 144, 217, 0.16);
            color: #8ec5ff;
            font-weight: 700;
            letter-spacing: 0.02em;
            font-size: 0.8rem;
            margin-bottom: 0.8rem;
          }
          .starcards-title {
            font-size: clamp(2.1rem, 4vw, 3.6rem);
            font-weight: 800;
            line-height: 1.02;
            margin: 0 0 0.45rem 0;
            color: #ffffff;
          }
          .starcards-subtitle {
            max-width: 64rem;
            font-size: 1rem;
            line-height: 1.55;
            color: rgba(232, 240, 254, 0.78);
            margin-bottom: 0.2rem;
          }
          .starcards-step {
            display: inline-flex;
            align-items: center;
            gap: 0.55rem;
            padding: 0.45rem 0.8rem;
            border-radius: 999px;
            background: rgba(17, 24, 39, 0.88);
            border: 1px solid rgba(74, 144, 217, 0.22);
            color: #dbeafe;
            font-weight: 700;
            font-size: 0.9rem;
            margin-right: 0.5rem;
            margin-bottom: 0.45rem;
          }
          [data-testid="stFileUploaderDropzone"] {
            border: 1px solid rgba(142, 197, 255, 0.16);
            background: rgba(16, 22, 35, 0.88);
            border-radius: 18px;
          }
          [data-testid="stMultiSelect"] > div,
          [data-testid="stTextInput"] input,
          [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
          [data-testid="stTextArea"] textarea,
          .stNumberInput input {
            border-radius: 14px !important;
            background: rgba(16, 22, 35, 0.92) !important;
            color: #f8fbff !important;
            border-color: rgba(142, 197, 255, 0.18) !important;
          }
          .stButton > button {
            border-radius: 999px;
            font-weight: 800;
            background: linear-gradient(135deg, #5ca8ff, #3273ff);
            border: 0;
            box-shadow: 0 12px 32px rgba(50, 115, 255, 0.25);
          }
          .stButton > button:hover {
            box-shadow: 0 16px 36px rgba(50, 115, 255, 0.32);
          }
          .starcards-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: rgba(20, 184, 166, 0.12);
            color: #99f6e4;
            font-size: 0.82rem;
            font-weight: 700;
            margin: 0.15rem 0.25rem 0.15rem 0;
          }
          .starcards-auto-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.2rem 0.55rem;
            border-radius: 999px;
            background: rgba(245, 158, 11, 0.14);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.22);
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.03em;
            margin-right: 0.35rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _save_upload(uploaded_file) -> Path:
    suffix = Path(uploaded_file.name).suffix or ".pdf"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getbuffer())
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def _default_deck_name(pdf_path: Path | None) -> str:
    if pdf_path is None:
        return "StarCards"
    stem = re.sub(r"[^\w\s-]", " ", pdf_path.stem)
    stem = stem.replace("_", " ").replace("-", " ")
    stem = re.sub(r"\s+", " ", stem).strip()
    if not stem:
        return "StarCards"
    return stem.title()


def _section_map(sections):
    return {section.breadcrumb: section for section in sections}


def _run_generation(pdf_path: Path, selected_sections, card_types, llm_settings: LLMSettings, verify_answers: bool):
    client = StarCardsLLMClient(llm_settings)
    selected = list(selected_sections)
    output_dir = Path(tempfile.mkdtemp(prefix="starcards_output_"))

    report = []
    total_generated = 0
    total_verified = 0
    total_rejected = 0

    for section in selected:
        cards = client.generate_cards(section, card_types)
        total_generated += len(cards)
        accepted = []
        rejected = []
        for card in cards:
            if verify_answers:
                result = verify_card(card, section.source_text)
                card.extra["verification"] = {
                    "passed": result.passed,
                    "score": result.score,
                    "reason": result.reason,
                    "evidence": result.evidence,
                }
                if result.passed:
                    accepted.append(card)
                    total_verified += 1
                else:
                    rejected.append((card, result))
                    total_rejected += 1
            else:
                accepted.append(card)
                total_verified += 1

        written = write_section_cards(output_dir, section, accepted)
        report.append(
            {
                "section": section,
                "accepted": accepted,
                "rejected": rejected,
                "written": written,
            }
        )

    return report, total_generated, total_verified, total_rejected


_inject_css()
st.markdown(
    """
    <div class="starcards-hero">
      <div class="starcards-kicker">StarCards | PDF to APKG study decks</div>
      <div class="starcards-title">Generate verified Anki decks from textbook PDFs.</div>
      <div class="starcards-subtitle">
        Upload a PDF, choose the bookmarks you want, pick your card types, and generate a downloadable APKG.
        Students and teachers can import the deck into Anki manually with no Python required.
      </div>
      <div style="margin-top: 0.9rem;">
        <span class="starcards-step">1. Upload PDF</span>
        <span class="starcards-step">2. Choose sections</span>
        <span class="starcards-step">3. Generate cards</span>
        <span class="starcards-step">4. Download APKG</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1.1, 0.9])

with left:
    uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"])
    include_auto_headings = st.checkbox(
        "Include auto-detected subheadings",
        value=True,
        help="StarCards can detect likely section headers from the PDF text when the bookmark tree is shallow or incomplete.",
    )
    if uploaded_pdf:
        pdf_path = _save_upload(uploaded_pdf)
        st.session_state["pdf_path"] = pdf_path
        st.success(f"Loaded {uploaded_pdf.name}")
        sections = build_sections(pdf_path, include_auto_headings=include_auto_headings)
        st.session_state["sections"] = sections
        if st.session_state.get("_deck_name_source") != uploaded_pdf.name:
            st.session_state["deck_name"] = _default_deck_name(pdf_path)
            st.session_state["_deck_name_source"] = uploaded_pdf.name
        st.write(f"Found {len(sections)} selectable sections.")
    else:
        st.info("Upload a PDF to begin.")

    if "sections" in st.session_state:
        sections = st.session_state["sections"]
        breadcrumb_list = [
            f"{'[AUTO] ' if section.auto_detected else ''}{section.breadcrumb} (p. {section.start_page + 1})"
            for section in sections
        ]
        label_to_section = {label: section for label, section in zip(breadcrumb_list, sections)}
        selected_sections = st.multiselect(
            "Select chapters, subchapters, and auto-detected headings",
            breadcrumb_list,
            default=breadcrumb_list[: min(3, len(breadcrumb_list))],
            help="Choose the bookmarks and sub-bookmarks you want included in the deck. Auto-detected entries are marked with [AUTO].",
        )
    else:
        label_to_section = {}
        selected_sections = []

    card_type_options = ["mcq", "cloze", "essay", "matching", "scaffold", "truefalse"]
    selected_card_types = st.multiselect("Card types", card_type_options, default=card_type_options)
    verify_answers = st.checkbox(
        "Verify cards against source text",
        value=False,
        help="When enabled, StarCards filters out cards that do not pass the source-text check.",
    )

with right:
    st.subheader("Model Settings")
    provider = st.selectbox("Provider", ["ollama", "openai", "anthropic", "gemini", "groq", "cerebras", "sambanova", "github"])
    api_key = st.text_input("API key", type="password", help="Bring your own key. Leave blank for local Ollama.")
    model_name = st.text_input("Model name", value={
        "ollama": "qwen2.5:14b",
        "openai": "gpt-4o",
        "anthropic": "claude-haiku-4-5",
        "gemini": "gemini-2.0-flash",
        "groq": "llama-3.3-70b-versatile",
        "cerebras": "qwen-3-235b-a22b-instruct-2507",
        "sambanova": "gpt-oss-120b",
        "github": "gpt-4o",
    }[provider])
    ollama_url = st.text_input("Ollama URL", value="http://localhost:11434")

    root_deck = st.text_input(
        "Deck name",
        key="deck_name",
    )
    st.caption("This becomes the Anki deck name inside the APKG.")

if uploaded_pdf and "sections" in st.session_state:
    sections = st.session_state["sections"]
    selected_section_objects = [label_to_section[label] for label in selected_sections if label in label_to_section]
    st.markdown(f"<div class='starcards-chip'>Selected sections: {len(selected_section_objects)}</div>", unsafe_allow_html=True)
    if selected_section_objects:
        with st.expander("Selected section list", expanded=False):
            for section in selected_section_objects[:50]:
                if section.auto_detected:
                    st.markdown(
                        f"<span class='starcards-auto-chip'>AUTO</span> {section.breadcrumb} <span style='opacity:0.7'>(page {section.start_page + 1})</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.write(section.breadcrumb)

    generate_clicked = st.button("Generate cards", type="primary")

    llm_settings = LLMSettings(
        backend=provider,
        ollama_url=ollama_url,
        ollama_model=model_name,
        groq_api_key=api_key if provider == "groq" else "",
        groq_model=model_name,
        sambanova_api_key=api_key if provider == "sambanova" else "",
        sambanova_model=model_name,
        openai_api_key=api_key if provider == "openai" else "",
        openai_model=model_name,
        cerebras_api_key=api_key if provider == "cerebras" else "",
        cerebras_model=model_name,
        gemini_api_key=api_key if provider == "gemini" else "",
        gemini_model=model_name,
        anthropic_api_key=api_key if provider == "anthropic" else "",
        anthropic_model=model_name,
        github_token=api_key if provider == "github" else "",
        github_model=model_name,
        verify_answers=verify_answers,
    )

    if generate_clicked:
        if not selected_section_objects:
            st.warning("Select at least one section first.")
        else:
            with st.spinner("Generating cards..."):
                report, total_generated, total_verified, total_rejected = _run_generation(
                    st.session_state["pdf_path"],
                    selected_section_objects,
                    selected_card_types,
                    llm_settings,
                    verify_answers,
                )
                st.session_state["generation_report"] = report
                st.session_state["generated_totals"] = {
                    "generated": total_generated,
                    "verified": total_verified,
                    "rejected": total_rejected,
                }
                st.session_state["generation_ready"] = True
                st.session_state["root_deck"] = root_deck
                export_dir = Path(tempfile.mkdtemp(prefix="starcards_apkg_"))
                export_path = export_dir / f"{root_deck}.apkg"
                artifact = export_apkg(report, root_deck, export_path)
                st.session_state["apkg_path"] = str(artifact.path)
                st.session_state["apkg_bytes"] = artifact.path.read_bytes()
                st.success(f"Generation complete. APKG ready: {artifact.path.name}")

    if "generated_totals" in st.session_state:
        totals = st.session_state["generated_totals"]
        st.metric("Generated", totals["generated"])
        st.metric("Verified", totals["verified"])
        st.metric("Rejected", totals["rejected"])
        if not verify_answers:
            st.caption("Verification is currently disabled, so all generated cards are included in the APKG.")

    if st.session_state.get("apkg_bytes"):
        st.caption("Download the APKG and import it manually into Anki.")
        st.download_button(
            "Download APKG",
            data=st.session_state["apkg_bytes"],
            file_name=Path(st.session_state["apkg_path"]).name,
            mime="application/octet-stream",
        )
