from __future__ import annotations

import argparse
from pathlib import Path

from starcards.anki import AnkiConnectClient, AnkiSettings


def main() -> int:
    parser = argparse.ArgumentParser(description="Import an APKG into Anki via AnkiConnect")
    parser.add_argument("apkg_path", type=Path)
    parser.add_argument("--connect-url", default="http://localhost:8765")
    args = parser.parse_args()

    client = AnkiConnectClient(AnkiSettings(connect_url=args.connect_url))
    ok = client.import_package(args.apkg_path)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

