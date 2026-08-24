# -*- coding: utf-8 -*-
"""Worker: extrage ZIP-ul și generează Excel-ul Deviz360."""

from __future__ import annotations

import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from winsmeta_to_deviz360 import convert_kos_to_deviz360_xlsx
from web.jobs import job_dir, write_status
from web.kos_utils import (
    cleanup_work_dir,
    prepare_kos_from_upload,
    safe_download_name,
)


def _archive_path(job_folder: str) -> str:
    for name in os.listdir(job_folder):
        lower = name.lower()
        if lower.startswith("upload") and lower.endswith((".zip", ".rar")):
            return os.path.join(job_folder, name)
    raise FileNotFoundError("Arhiva încărcată nu a fost găsită.")


def main() -> int:
    if len(sys.argv) < 3:
        return 2
    job_id = sys.argv[1]
    filename = sys.argv[2]
    job_folder = job_dir(job_id)
    work_dir = ""
    try:
        write_status(job_id, status="pending", pid=os.getpid(), step="extract")
        print(f"[{job_id}] extract {filename}", flush=True)
        archive = _archive_path(job_folder)
        kos_path, work_dir = prepare_kos_from_upload(archive, filename)
        write_status(job_id, step="convert")
        print(f"[{job_id}] convert {kos_path}", flush=True)
        out_path = os.path.join(job_folder, "export.xlsx")
        count, info, norm_count, sheets, _mat, _man, _uti, total = convert_kos_to_deviz360_xlsx(
            kos_path, out_path
        )
        write_status(
            job_id,
            status="done",
            xlsx_path=out_path,
            download_name=safe_download_name(filename),
            stats={
                "obiect": info.obiect or "",
                "norms": str(norm_count),
                "devizes": str(sheets),
                "rows": str(count),
                "total": f"{total:.2f}",
            },
        )
        return 0
    except Exception as exc:
        write_status(
            job_id,
            status="error",
            error=str(exc).encode("utf-8", "replace").decode("utf-8").strip()
            or "Conversia a eșuat pe server.",
            trace=traceback.format_exc()[-2000:],
        )
        return 1
    finally:
        if work_dir:
            cleanup_work_dir(work_dir)


if __name__ == "__main__":
    raise SystemExit(main())
