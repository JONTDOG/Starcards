from __future__ import annotations

import argparse
from pathlib import Path

from starcards.anki import AnkiConnectClient, AnkiSettings


def main() -> int:
    parser = argparse.ArgumentParser(description="Export an Anki deck as APKG via AnkiConnect")
    parser.add_argument("deck_name")
    parser.add_argument("output_path", type=Path)
    parser.add_argument("--connect-url", default="http://localhost:8765")
    parser.add_argument("--include-sched", action="store_true")
    args = parser.parse_args()

    client = AnkiConnectClient(
        AnkiSettings(
            connect_url=args.connect_url,
            include_sched=args.include_sched,
        )
    )
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    ok = client.export_package(args.deck_name, args.output_path)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

