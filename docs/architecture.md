# Architecture

StarCards is organized as a modular PDF-to-Anki platform with clearly separated layers:

- `ingestion/` handles document intake
- `preprocessing/` prepares document structure
- `card_generation/` represents card creation responsibilities
- `export/` represents package export responsibilities
- `ui/` contains browser and desktop presentation layers
- `providers/` contains provider adapter boundaries
- `orchestration/` contains workflow coordination boundaries
- `utils/` contains shared helpers

This repository intentionally publishes only the architectural shape of the system.
