# -*- coding: utf-8 -*-
"""WinDev — aplicație web Flask: Winsmeta KOS -> Deviz360."""

from __future__ import annotations

import io
import os
import sys
import tempfile
import threading
import time
import uuid

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from winsmeta_to_deviz360 import convert_kos_to_deviz360_xlsx
from web.kos_utils import (
    cleanup_work_dir,
    make_output_xlsx,
    prepare_kos_from_upload,
    safe_download_name,
)

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 80 * 1024 * 1024

JOB_TTL_SEC = 15 * 60
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _safe_error_message(exc: BaseException) -> str:
    text = str(exc).encode("utf-8", "replace").decode("utf-8").strip()
    return text or "Conversia a eșuat pe server."


def _purge_old_jobs() -> None:
    now = time.time()
    with _jobs_lock:
        stale = [jid for jid, job in _jobs.items() if now - job.get("created", now) > JOB_TTL_SEC]
        for jid in stale:
            job = _jobs.pop(jid, None)
            if job and job.get("work_dir"):
                cleanup_work_dir(job["work_dir"])


def _finish_job_cleanup(job: dict) -> None:
    work_dir = job.get("work_dir") or ""
    if work_dir:
        cleanup_work_dir(work_dir)
    job["work_dir"] = ""
    job["xlsx_path"] = ""


def _process_job(job_id: str, archive_path: str, filename: str) -> None:
    work_dir = ""
    try:
        kos_path, work_dir = prepare_kos_from_upload(archive_path, filename)
        out_path = make_output_xlsx(work_dir)
        count, info, norm_count, sheets, _mat, _man, _uti, total = convert_kos_to_deviz360_xlsx(
            kos_path, out_path
        )
        with _jobs_lock:
            job = _jobs.get(job_id)
            if not job:
                cleanup_work_dir(work_dir)
                return
            job["status"] = "done"
            job["work_dir"] = work_dir
            job["xlsx_path"] = out_path
            job["download_name"] = safe_download_name(filename)
            job["stats"] = {
                "obiect": info.obiect or "",
                "norms": str(norm_count),
                "devizes": str(sheets),
                "rows": str(count),
                "total": f"{total:.2f}",
            }
            work_dir = ""
    except Exception as exc:
        app.logger.exception("Conversie eșuată (job %s)", job_id)
        with _jobs_lock:
            job = _jobs.get(job_id)
            if job:
                job["status"] = "error"
                job["error"] = _safe_error_message(exc)
        if work_dir:
            cleanup_work_dir(work_dir)
    finally:
        try:
            os.unlink(archive_path)
        except OSError:
            pass


@app.errorhandler(RequestEntityTooLarge)
def too_large(_exc):
    return jsonify({"ok": False, "error": "Arhiva depășește limita de 80 MB. Folosiți ZIP."}), 413


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "app": "WinDev"})


@app.post("/api/convert")
def convert():
    _purge_old_jobs()
    if "kos_zip" not in request.files:
        return jsonify({"ok": False, "error": "Lipsește fișierul arhivă."}), 400

    upload = request.files["kos_zip"]
    if not upload.filename:
        return jsonify({"ok": False, "error": "Selectați o arhivă ZIP sau RAR."}), 400

    ext = os.path.splitext(upload.filename)[1].lower() or ".zip"
    if ext not in (".zip", ".rar"):
        return jsonify({"ok": False, "error": "Acceptăm doar arhive ZIP sau RAR."}), 400

    tmp_archive = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        upload.save(tmp_archive.name)
        tmp_archive.close()
    except Exception:
        try:
            os.unlink(tmp_archive.name)
        except OSError:
            pass
        raise

    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {
            "id": job_id,
            "status": "pending",
            "error": "",
            "created": time.time(),
            "work_dir": "",
            "xlsx_path": "",
            "download_name": safe_download_name(upload.filename),
            "stats": None,
        }

    thread = threading.Thread(
        target=_process_job,
        args=(job_id, tmp_archive.name, upload.filename),
        daemon=True,
        name=f"windev-{job_id[:8]}",
    )
    thread.start()
    return jsonify({"ok": True, "job_id": job_id, "status": "pending"}), 202


@app.get("/api/jobs/<job_id>")
def job_status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return jsonify({"ok": False, "error": "Conversia a expirat. Reîncărcați arhiva."}), 404
        payload = {
            "ok": True,
            "job_id": job_id,
            "status": job["status"],
            "error": job.get("error") or "",
            "filename": job.get("download_name") or "",
            "stats": job.get("stats"),
        }
    return jsonify(payload)


@app.get("/api/jobs/<job_id>/file")
def job_file(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return jsonify({"ok": False, "error": "Conversia a expirat. Reîncărcați arhiva."}), 404
        if job["status"] != "done" or not job.get("xlsx_path"):
            return jsonify({"ok": False, "error": "Fișierul nu este gata."}), 409
        path = job["xlsx_path"]
        download_name = job.get("download_name") or "deviz360_export.xlsx"
        stats = job.get("stats") or {}
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return jsonify({"ok": False, "error": "Fișierul convertit nu mai este disponibil."}), 404
        _finish_job_cleanup(job)
        job["status"] = "downloaded"

    buf = io.BytesIO(data)
    buf.seek(0)
    response = send_file(
        buf,
        as_attachment=True,
        download_name=download_name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response.headers["X-WinDev-Rows"] = str(stats.get("rows") or "")
    response.headers["X-WinDev-Norms"] = str(stats.get("norms") or "")
    response.headers["X-WinDev-Devizes"] = str(stats.get("devizes") or "")
    response.headers["X-WinDev-Object"] = str(stats.get("obiect") or "")
    response.headers["X-WinDev-Total"] = str(stats.get("total") or "")
    return response


def create_app():
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or os.environ.get("WINDEV_PORT", "8080"))
    debug = os.environ.get("WINDEV_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
