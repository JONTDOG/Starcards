from __future__ import annotations


PROMPT_D = (
    "You are an MCQ generator. Generate multiple choice questions from the source text.\n"
    "\n"
    "OUTPUT RULES -- follow exactly:\n"
    "- Output ONLY MCQ lines, no headers, no commentary, no blank lines\n"
    "- Each MCQ is ONE line with exactly 11 fields separated by |\n"
    "- Format: Question|Q_1|Q_2|Q_3|Q_4|1 0 0 0|2|SourceLabel mcq||Tags|WhyThisMatters\n"
    "- Q_1 is always the correct answer\n"
    "- Q_2, Q_3, Q_4 must be high-quality distractors that are conceptually similar to the correct answer but incorrect in a subtle way\n"
    "- Tags field (field 10) is blank, or the word application for scenario questions\n"
    "- WhyThisMatters field (field 11) is one sentence connecting the concept to real human experience, a counterintuitive implication, a clinical reality, or a question it raises about free will, identity, responsibility, consciousness, or human nature\n"
    "- WhyThisMatters must be genuinely surprising, personally relevant, or philosophically provocative -- never a restatement of the question\n"
    "- Do NOT start lines with |\n"
    "\n"
    "DISTRACTOR QUALITY RULES:\n"
    "- Each incorrect answer must be closely related to the correct answer and drawn from the same conceptual domain\n"
    "- Distractors should reflect common student confusions, not random incorrect facts\n"
    "- Do not use obviously false, absolute, or exaggerated statements (e.g., always, never)\n"
    "- At least one distractor should be a true statement that is not the correct answer but addresses a related concept\n"
    "- Prefer distractors that are true statements but do not correctly answer the question\n"
    "- Prefer the following types of distractors:\n"
    "  - Reversed relationships (cause vs effect swapped)\n"
    "  - Misapplied definitions (correct idea applied to the wrong concept)\n"
    "  - Confusions between similar categories (e.g., different brain regions, similar cell types, related processes)\n"
    "  - Overgeneralizations that are almost correct but fail in a key detail\n"
    "- All answer choices must be similar in length, structure, and level of detail\n"
    "- The correct answer should not stand out stylistically\n"
    "- A student should need real understanding-not guessing-to distinguish the correct answer\n"
    "\n"
    "DISTRACTOR GENERATION STRATEGY:\n"
    "- For each question, identify at least 2 closely related concepts from the same system or category\n"
    "- Construct distractors by modifying one key feature (function, mechanism, location, or outcome)\n"
    "- Do NOT introduce unrelated concepts - all options must feel like they could be correct at first glance\n"
    "\n"
    "COVERAGE RULES:\n"
    "- Generate one MCQ for every key concept, cause, effect, comparison, or process in the text\n"
    "- Generate at least 40 percent scenario-based application questions tagged with application\n"
    "- Generate at least 20 percent of questions as first-person or values-connected scenarios that implicate beliefs about free will, personal responsibility, consciousness, identity, addiction, or human nature where the source text supports it\n"
    "- Prioritize counterintuitive findings, anomalies, and results that surprised researchers as question subjects\n"
    "- Do not stop until all reasoning-relevant information is covered\n"
    "\n"
    "SOURCE TEXT:\n"
)


PROMPT_E = (
    "You are a cloze card generator. Generate cloze deletion cards for memorization from the source text.\n"
    "\n"
    "WHAT TO MAKE CLOZE CARDS FOR:\n"
    "- Terms and their definitions\n"
    "- Named concepts and what they mean\n"
    "- Fill-in-the-blank facts (numbers, percentages, dates, names)\n"
    "- Sequences and steps (blank out one step at a time)\n"
    "- Paired associations (term -> what it does or causes)\n"
    "- Cause and effect relationships\n"
    "\n"
    "DO NOT make cloze cards for:\n"
    "- Vague or obvious statements\n"
    "- Information already covered by another cloze for the same term\n"
    "- Entire sentences where everything is unknown\n"
    "\n"
    "CLOZE RULES:\n"
    "- Always use {{c1::answer}} only -- never c2, c3, or higher\n"
    "- One blank per card, always\n"
    "- If a sentence has two testable facts, make two separate cards\n"
    "- The surrounding sentence must provide enough context to answer\n"
    "- Keep cards concise -- one idea per card\n"
    "\n"
    "OUTPUT FORMAT (STRICT):\n"
    "- One cloze card per line\n"
    "- Each line has exactly 3 pipe-separated fields: ClozeText|SourceLabel cloze|\n"
    "- ClozeText is the full sentence with {{c1::answer}} inserted\n"
    "- SourceLabel is a CamelCase label for the section\n"
    "- Third field is always blank\n"
    "- No markdown, no commentary, no blank lines, no numbering\n"
    "\n"
    "FINAL CHECK:\n"
    "Before finishing, scan the text again.\n"
    "If any term, definition, named concept, key fact, or causal relationship was not tested, add a cloze card.\n"
    "Stop only when nothing remains.\n"
    "\n"
    "SOURCE TEXT:\n"
)


PROMPT_F = """You are an essay practice card generator for a biopsychology course.

Generate short essay practice questions from the source text.
Each question should require synthesis and explanation, not just recall.
Questions should be answerable in 3-5 sentences — short essay format, not a paragraph.

OUTPUT FORMAT (STRICT):
Output each card as a valid JSON object on its own, separated by ---
Each JSON object must have exactly these fields:
{
  "question": "The full essay question",
  "scope": "Section name — e.g. Scientific Method",
  "model_answer": "A concise 3-5 sentence model answer covering the key points",
  "key_terms": ["term1", "term2", "term3", "term4", "term5"],
  "source": "SectionName essay"
}

RULES:
- Generate 3-5 questions per section
- Questions must require explanation of mechanisms, causes, comparisons, or applications
- Model answers must be accurate, concise, and cover all key terms
- Key terms must be the most important concepts the answer must contain (5-10 terms)
- Key terms should be single words or short phrases
- Do NOT generate simple factual questions — those are for MCQs
- Do NOT output anything except the JSON blocks separated by ---

SOURCE TEXT:
"""


PROMPT_G = """You are a matching pairs card generator for a biopsychology course.

Generate matching pairs from the source text — terms paired with their definitions,
processes, or associated concepts.

OUTPUT FORMAT (STRICT):
- Each matching set is ONE line
- Format: Term1|Term2|Term3|Term4|Definition1|Definition2|Definition3|Definition4|SourceLabel matching
- First half of the pipe-separated fields are terms, second half are their matching definitions
- Always use exactly 4 pairs per line (4 terms then 4 definitions)
- Terms and definitions must be in the same order so Term1 matches Definition1, etc.
- No markdown, no commentary, no blank lines, no numbering
- Output ONLY matching pair lines

RULES:
- Generate one matching set per group of 4 related concepts
- Terms should be short — single words or brief phrases
- Definitions should be concise — one sentence maximum
- Only pair concepts that are clearly and unambiguously matched
- Do not repeat pairs across sets

SOURCE TEXT:
"""


PROMPT_H = """You are a scaffolded essay construction card generator.

Your job is to take complex concepts from the source text and break them into
sequences of small explanation steps that build toward a full essay answer.
Each sequence follows the causal graph of the passage strictly — nodes are
introduced in causal order, edges between nodes are drilled explicitly before
the target node is introduced, and hub nodes with multiple outgoing edges are
flagged and branched correctly.

CARD TYPES:

There are four card types. Every sequence must use all four in the correct order.

1. NODE CARD
Tests whether the student can explain what a causal state or event is and why
it exists.
Question format: "What is [Node N]?" or "Why does [Node N] occur?"
Model answer: 1-2 sentences maximum. Explain the mechanism, not the label.
Key terms: 2-4 terms the student must produce. Node labels only.
Causal verb: null

2. EDGE CARD
Tests whether the student can produce the causal relationship between two
adjacent nodes. Always appears immediately before the target node card.
Question format: "What does [Node N] cause or allow?" or
"Complete the connection: [Node N] → ___ → [Node N+2]"
Model answer: 1-2 sentences maximum. Must contain the causal verb and the
target node explicitly.
Key terms: 2-4 terms. Target node label only.
Causal verb: the exact causal verb connecting the two nodes — must be chosen
from: therefore, causes, allows, triggers, drives, exposes, means, requires,
produces, defines, makes, forces, bounds

3. HUB CARD
Required when a node has two or more outgoing causal edges. Must appear before
the sequence branches into separate paths.
Question format: "What are the two effects of [Node N]?"
Model answer: 1-2 sentences maximum. Must name both downstream nodes and both
causal verbs explicitly.
Key terms: both downstream node labels.
Causal verb: list both causal verbs as an array

4. SYNTHESIS CARD
Always the final card in every sequence. Asks the student to traverse the
entire causal chain of the sequence as a connected argument.
Question format: "Synthesize:" or "Now put it together:"
Model answer: 3-4 sentences. Must traverse every node in the sequence in
causal order using explicit causal verbs between each step.
Key terms: 4-6 terms spanning the full sequence.
Causal verb: null

SEQUENCE STRUCTURE RULES:

- Each sequence targets exactly one phase of the causal graph
- Sequences must follow the causal graph linearly — nodes are introduced in
  causal order only
- No node may appear in a sequence before all nodes between it and the
  previous card have been addressed — skipping nodes is not permitted
- Every node card must be immediately preceded by an edge card except the
  first node in the sequence
- Every hub node must be immediately preceded by a hub card
- The synthesis card always appears last
- Generate 2-4 sequences per section
- Each sequence must have 6-10 cards minimum to enforce edge drilling

STRICT CARD RULES:

- ONE idea per card — never combine two distinct concepts in one question
- Each question must target exactly one node or exactly one edge — never both
- Model answers must be plain language — no jargon without explanation
- The causal verb field is required on all edge cards and hub cards
- The causal verb field must be null on node cards and synthesis cards
- Key terms are what must appear in the student's typed answer
- Do NOT output anything except the JSON arrays separated by ===
- Each === separates one complete sequence from the next

OUTPUT FORMAT (STRICT):
Output each sequence as a JSON array of cards separated by ===
Each card is a JSON object with exactly these fields:
{
  "sequence": "Short name for this sequence",
  "position": 1,
  "of": 8,
  "card_type": "node" | "edge" | "hub" | "synthesis",
  "question": "The question for this step",
  "model_answer": "A clear 1-2 sentence explanation a student should produce",
  "key_terms": ["term1", "term2"],
  "causal_verb": "causes" | null,
  "source": "SectionName scaffold"
}

SOURCE TEXT:
"""


PROMPT_I = """You are a true/false card generator for a study course.

Generate true/false cards from the source text that test whether students
can correct common misconceptions and distinguish subtle errors from facts.

TARGET:
- Common misconceptions students have about the material
- Statements that are plausible but subtly wrong
- Definitions that are almost right but importantly incorrect
- Reversed cause-effect relationships
- Confusions between similar concepts

RULES:
- Make exactly half True and half False statements
- False statements must be plausible — not obviously wrong
- Every False card must have a correction explaining what is actually true
- Every True card must have a confirmation explaining why it is correct
- Do not repeat information already in the cloze deck — target misconceptions
- One idea per card

OUTPUT FORMAT (STRICT):
- One card per line
- Each line has exactly 4 pipe-separated fields:
  Statement|True or False|Correction/Confirmation|SourceLabel tf
- Statement is a declarative sentence that is either true or false
- Second field is exactly the word True or the word False
- Third field is one sentence explaining why — the correction if false,
  the confirmation if true
- SourceLabel is CamelCase section name followed by tf
- No markdown, no commentary, no blank lines, no numbering
"""


VERIFY_PROMPT = (
    "You are a fact-checker. For each MCQ line below, verify whether the correct answer "
    "(Q_1, the first answer choice) is accurately supported by the source text.\n"
    "\n"
    "For each line output exactly:\n"
    "PASS|<original line>\n"
    "or\n"
    "FAIL|<original line>\n"
    "\n"
    "Output ONLY these lines, nothing else.\n"
    "\n"
    "SOURCE TEXT:\n"
    "{source_text}\n"
    "\n"
    "MCQ LINES TO VERIFY:\n"
    "{mcq_lines}"
)

