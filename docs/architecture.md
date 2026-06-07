# StarCards Architecture

## Layers

### 1. Shared Core

The shared core owns:

- PDF bookmark extraction
- leaf-section selection
- card data models
- output path generation
- source-grounded verification
- output parsing and import dispatch

### 2. Pipelines

The pipeline layer turns the core into workflows:

- PDF -> section text -> card drafts
- card drafts -> verification -> accepted/rejected
- verified outputs -> Anki export or import

### 3. UIs

Two front ends can sit on top of the same backend:

- Desktop GUI for heavier local use
- Streamlit GUI for easy browser-based pilot use

## Guiding rules

- No card should ship without source evidence.
- Long scaffold outputs should be generated in chunks.
- Any file that looks truncated should fail closed and be rerun.
- The GUI should never contain generation logic directly.

## Output contract

Each card should carry:

- card type
- source label
- source quote
- verification status
- evidence or reason

