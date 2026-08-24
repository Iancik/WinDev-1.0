# -*- coding: utf-8 -*-
"""Stocare job-uri de conversie pe disc (supraviețuiește restartului Render)."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from typing import Any, Dict, Optional

JOB_ROOT = os.path.join(tempfile.gettempdir(), "windev_jobs")
JOB_TTL_SEC = 20 * 60


def job_dir(job_id: str) -> str:
    return os.path.join(JOB_ROOT, job_id)


def status_path(job_id: str) -> str:
    return os.path.join(job_dir(job_id), "status.json")


def read_status(job_id: str) -> Optional[Dict[str, Any]]:
    path = status_path(job_id)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def write_status(job_id: str, **fields: Any) -> Dict[str, Any]:
    os.makedirs(job_dir(job_id), exist_ok=True)
    data = read_status(job_id) or {}
    data.update(fields)
    path = status_path(job_id)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    os.replace(tmp, path)
    return data


def pid_alive(pid: Any) -> bool:
    try:
        pid_i = int(pid or 0)
    except (TypeError, ValueError):
        return False
    if pid_i <= 0:
        return False
    try:
        with open(f"/proc/{pid_i}/stat", "r", encoding="ascii") as fh:
            stat = fh.read()
        rparen = stat.rfind(")")
        if rparen != -1 and rparen + 2 < len(stat) and stat[rparen + 2] == "Z":
            return False
    except OSError:
        pass
    try:
        os.kill(pid_i, 0)
        return True
    except OSError:
        return False


def purge_old_jobs() -> None:
    if not os.path.isdir(JOB_ROOT):
        return
    now = time.time()
    for name in os.listdir(JOB_ROOT):
        path = os.path.join(JOB_ROOT, name)
        if not os.path.isdir(path):
            continue
        try:
            age = now - os.path.getmtime(path)
        except OSError:
            continue
        if age > JOB_TTL_SEC:
            shutil.rmtree(path, ignore_errors=True)


def resolve_job(job_id: str) -> Optional[Dict[str, Any]]:
    data = read_status(job_id)
    if not data:
        return None
    if data.get("status") == "pending":
        age = time.time() - float(data.get("created") or time.time())
        if age > 180:
            data = write_status(
                job_id,
                status="error",
                error="Conversia a durat prea mult pe server. Încercați un proiect/ZIP mai mic.",
            )
            return data
        if not pid_alive(data.get("pid")):
            xlsx = data.get("xlsx_path") or os.path.join(job_dir(job_id), "export.xlsx")
            if os.path.isfile(xlsx):
                data = write_status(job_id, status="done", xlsx_path=xlsx)
            else:
                data = write_status(
                    job_id,
                    status="error",
                    error="Conversia s-a oprit pe server. Reîncărcați arhiva ZIP.",
                )
    return data
