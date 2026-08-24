# -*- coding: utf-8 -*-
"""Punct de intrare CLI pentru conversie web (Flask / PHP exec)."""

from __future__ import annotations

import argparse
import json
import sys

from winsmeta_to_deviz360 import convert_kos_to_deviz360_xlsx


def main() -> int:
    parser = argparse.ArgumentParser(description="Conversie KOS -> Deviz360 pentru server web")
    parser.add_argument("kos_path", help="Cale folder WINSMETA.KOS")
    parser.add_argument("output_path", help="Cale fișier .xlsx de ieșire")
    parser.add_argument("--json", action="store_true", help="Afișează statistici JSON pe stdout")
    args = parser.parse_args()

    try:
        count, info, norm_count, sheets, mat, man, uti, total = convert_kos_to_deviz360_xlsx(
            args.kos_path, args.output_path
        )
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"Eroare: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "rows": count,
                    "norms": norm_count,
                    "devizes": sheets,
                    "obiect": info.obiect,
                    "material": round(mat, 2),
                    "manopera": round(man, 2),
                    "utilaj": round(uti, 2),
                    "total": round(total, 2),
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
