# -*- coding: utf-8 -*-
"""CLI pentru convertorul Winsmeta -> Deviz360."""

import argparse
import os
import sys

from winsmeta_to_deviz360 import convert_kos_to_deviz360_xlsx, default_output_path_deviz360


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convertește un proiect Winsmeta (.KOS) în format Deviz360 (.xlsx)."
    )
    parser.add_argument("kos_path", help="Calea către folderul proiectului Winsmeta (ex: WINSMETA.KOS)")
    parser.add_argument(
        "-o",
        "--output",
        help="Calea fișierului de ieșire (.xlsx)",
    )
    args = parser.parse_args()

    kos_path = os.path.abspath(args.kos_path)
    output_path = os.path.abspath(args.output) if args.output else default_output_path_deviz360(kos_path)

    try:
        count, info, norm_count, sheets, mat, man, uti, total = convert_kos_to_deviz360_xlsx(
            kos_path, output_path
        )
        print(f"Conversie Deviz360 reușită: {count} rânduri, {norm_count} norme, {sheets} devize")
        print(
            f"Cheltuieli directe: {total:,.2f} lei "
            f"(material {mat:,.2f}, manoperă {man:,.2f}, utilaj {uti:,.2f})"
        )
    except Exception as exc:
        print(f"Eroare: {exc}", file=sys.stderr)
        return 1

    print(f"Obiect: {info.obiect}")
    print(f"Fișier: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
