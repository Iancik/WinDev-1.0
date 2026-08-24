# -*- coding: utf-8 -*-
"""CLI: extrage folder KOS din arhivă ZIP/RAR (pentru PHP / test)."""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from web.kos_utils import KosUploadError, prepare_kos_from_upload


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrage folder KOS din ZIP/RAR")
    parser.add_argument("archive_path", help="Cale arhivă .zip sau .rar")
    parser.add_argument("original_name", nargs="?", default="", help="Nume original upload")
    parser.add_argument("--json", action="store_true", help="Ieșire JSON")
    args = parser.parse_args()

    original = args.original_name or os.path.basename(args.archive_path)
    try:
        kos_path, work_dir = prepare_kos_from_upload(args.archive_path, original)
    except KosUploadError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"Eroare: {exc}", file=sys.stderr)
        return 1

    payload = {"ok": True, "kos_path": kos_path, "work_dir": work_dir}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(kos_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
