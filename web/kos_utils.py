# -*- coding: utf-8 -*-
"""Utilitare upload/extragere arhive KOS (ZIP / RAR) pentru WinDev web."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from typing import List, Optional, Tuple

MAX_ARCHIVE_BYTES = 80 * 1024 * 1024  # 80 MB
ALLOWED_ARCHIVE_EXT = {".zip", ".rar"}


class KosUploadError(Exception):
    pass


def _find_kos_root(base_dir: str) -> Optional[str]:
    """Găsește folderul care conține POZYCJE.DB (indiferent de subfolder)."""
    for root, _dirs, files in os.walk(base_dir):
        for name in files:
            if name.upper() == "POZYCJE.DB":
                return root
    return None


def _safe_extract_zip(zip_path: str, dest_dir: str) -> None:
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            name = member.filename.replace("\\", "/")
            if name.startswith("/") or ".." in name.split("/"):
                raise KosUploadError("Arhiva conține căi nevalide.")
            target = os.path.realpath(os.path.join(dest_dir, name))
            if not target.startswith(os.path.realpath(dest_dir)):
                raise KosUploadError("Arhiva conține căi nevalide.")
        zf.extractall(dest_dir)


def _is_rar_file(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            sig = fh.read(7)
        return sig.startswith(b"Rar!\x1a\x07")
    except OSError:
        return False


def _seven_zip_paths() -> List[str]:
    paths: List[str] = []
    found = shutil.which("7z")
    if found:
        paths.append(found)
    for candidate in (
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ):
        if os.path.isfile(candidate):
            paths.append(candidate)
    return paths


def _unrar_paths() -> List[str]:
    paths: List[str] = []
    for name in ("unrar", "UnRAR", "unrar.exe", "UnRAR.exe"):
        found = shutil.which(name)
        if found:
            paths.append(found)
    for candidate in (
        r"C:\Program Files\WinRAR\UnRAR.exe",
        r"C:\Program Files\WinRAR\unrar.exe",
    ):
        if os.path.isfile(candidate):
            paths.append(candidate)
    return paths


def _run_extract(cmd: List[str]) -> None:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except FileNotFoundError as exc:
        raise KosUploadError("Extractorul de arhive nu este disponibil pe server.") from exc
    except subprocess.TimeoutExpired as exc:
        raise KosUploadError("Extragerea arhivei a durat prea mult.") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise KosUploadError(detail or "Extragerea arhivei RAR a eșuat.")


def _extract_rar(rar_path: str, dest_dir: str) -> None:
    try:
        import rarfile  # type: ignore

        with rarfile.RarFile(rar_path) as rf:
            rf.extractall(dest_dir)
        return
    except ImportError:
        pass
    except Exception as exc:
        if "Cannot find working tool" not in str(exc):
            raise KosUploadError(f"Arhiva RAR este invalidă: {exc}") from exc

    for seven_zip in _seven_zip_paths():
        _run_extract([seven_zip, "x", f"-o{dest_dir}", "-y", rar_path])
        return

    for unrar in _unrar_paths():
        _run_extract([unrar, "x", "-y", rar_path, dest_dir + os.sep])
        return

    raise KosUploadError(
        "Arhiva RAR necesită 7-Zip sau UnRAR pe server. Folosiți ZIP sau instalați 7-Zip."
    )


def _archive_kind(path: str, original_name: str = "") -> str:
    ext = os.path.splitext(original_name or path)[1].lower()
    if ext == ".rar" or _is_rar_file(path):
        return "rar"
    if ext == ".zip" or zipfile.is_zipfile(path):
        return "zip"
    return ""


def prepare_kos_from_upload(
    upload_path: str,
    original_name: str = "",
) -> Tuple[str, str]:
    """
    Extrage arhiva ZIP/RAR și returnează (kos_path, work_dir).

    Acceptă:
    - CS1.zip / CS1.rar cu folderul CS1.KOS în interior
    - arhivă făcută direct peste folderul KOS (click dreapta → comprimă)
    """
    size = os.path.getsize(upload_path)
    if size > MAX_ARCHIVE_BYTES:
        raise KosUploadError("Arhiva depășește limita de 80 MB.")

    kind = _archive_kind(upload_path, original_name)
    if not kind:
        ext = os.path.splitext(original_name or upload_path)[1].lower()
        if ext and ext not in ALLOWED_ARCHIVE_EXT:
            raise KosUploadError("Acceptăm doar arhive ZIP sau RAR.")
        raise KosUploadError("Fișierul trebuie să fie arhivă ZIP sau RAR cu folderul KOS.")

    work_dir = tempfile.mkdtemp(prefix="windev_")
    extract_dir = os.path.join(work_dir, "extract")
    os.makedirs(extract_dir, exist_ok=True)

    try:
        if kind == "zip":
            _safe_extract_zip(upload_path, extract_dir)
        else:
            _extract_rar(upload_path, extract_dir)
    except zipfile.BadZipFile as exc:
        cleanup_work_dir(work_dir)
        raise KosUploadError("Arhiva ZIP este coruptă.") from exc
    except KosUploadError:
        cleanup_work_dir(work_dir)
        raise
    except Exception as exc:
        cleanup_work_dir(work_dir)
        raise KosUploadError(f"Extragerea arhivei a eșuat: {exc}") from exc

    kos_root = _find_kos_root(extract_dir)
    if not kos_root:
        cleanup_work_dir(work_dir)
        raise KosUploadError(
            "Nu am găsit POZYCJE.DB în arhivă. Comprimați folderul proiectului "
            "(ex: CS1.KOS) — click dreapta pe folder → Trimite la → Folder comprimat (ZIP/RAR)."
        )

    return kos_root, work_dir


def make_output_xlsx(work_dir: str) -> str:
    name = f"deviz360_{uuid.uuid4().hex[:8]}.xlsx"
    return os.path.join(work_dir, name)


def cleanup_work_dir(work_dir: str) -> None:
    if work_dir and os.path.isdir(work_dir):
        shutil.rmtree(work_dir, ignore_errors=True)


def safe_download_name(original: str) -> str:
    base = os.path.splitext(os.path.basename(original or "deviz360"))[0]
    base = re.sub(r"[^\w\-]+", "_", base, flags=re.UNICODE).strip("_")
    return (base or "deviz360") + "_export.xlsx"
