# -*- coding: utf-8 -*-
"""WinDev — aplicație web Flask: Winsmeta KOS -> Deviz360."""

from __future__ import annotations

import io
import os
import subprocess
import sys
import threading
import time
import uuid

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from web.jobs import job_dir, purge_old_jobs, read_status, resolve_job, write_status
from web.kos_utils import safe_download_name

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 80 * 1024 * 1024
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

BUILD_ID = "13"


def _watch_worker(proc: subprocess.Popen, job_id: str) -> None:
    try:
        out, _ = proc.communicate(timeout=150)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        write_status(
            job_id,
            status="error",
            error="Conversia a durat prea mult pe server. Încercați un ZIP mai mic.",
        )
        return
    text = (out or b"").decode("utf-8", "replace")
    if text:
        print(text[-4000:], flush=True)
    job = read_status(job_id) or {}
    if job.get("status") in ("done", "error"):
        return
    rc = proc.returncode
    if rc and rc < 0:
        msg = (
            "Citirea fișierelor Winsmeta a crăpat pe server (biblioteca Paradox). "
            "Încercați un proiect mai mic."
        )
    else:
        last = text.strip().splitlines()[-1] if text.strip() else ""
        msg = last[:400] or f"Convertorul s-a oprit (cod {rc})."
    write_status(job_id, status="error", error=msg)


@app.errorhandler(RequestEntityTooLarge)
def too_large(_exc):
    return jsonify({"ok": False, "error": "Arhiva depășește limita de 80 MB. Folosiți ZIP."}), 413


@app.route("/")
def index():
    resp = app.make_response(render_template("index.html", build=BUILD_ID))
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "app": "WinDev", "build": BUILD_ID})


@app.post("/api/convert")
def convert():
    purge_old_jobs()
    if "kos_zip" not in request.files:
        return jsonify({"ok": False, "error": "Lipsește fișierul arhivă."}), 400

    upload = request.files["kos_zip"]
    if not upload.filename:
        return jsonify({"ok": False, "error": "Selectați o arhivă ZIP."}), 400

    ext = os.path.splitext(upload.filename)[1].lower() or ".zip"
    if ext not in (".zip", ".rar"):
        return jsonify({"ok": False, "error": "Acceptăm doar arhive ZIP."}), 400

    job_id = uuid.uuid4().hex
    folder = job_dir(job_id)
    os.makedirs(folder, exist_ok=True)
    archive_path = os.path.join(folder, "upload" + ext)
    upload.save(archive_path)

    write_status(
        job_id,
        status="pending",
        created=time.time(),
        download_name=safe_download_name(upload.filename),
        pid=0,
        step="queued",
    )

    worker = os.path.join(ROOT, "web", "convert_job.py")
    env = os.environ.copy()
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-u", worker, job_id, upload.filename],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    write_status(job_id, pid=proc.pid)
    threading.Thread(
        target=_watch_worker,
        args=(proc, job_id),
        daemon=True,
        name=f"watch-{job_id[:8]}",
    ).start()
    return jsonify({"ok": True, "job_id": job_id, "status": "pending", "build": BUILD_ID}), 202


@app.get("/api/jobs/<job_id>")
def job_status(job_id: str):
    job = resolve_job(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Conversia a expirat. Reîncărcați arhiva ZIP."}), 404
    return jsonify(
        {
            "ok": True,
            "job_id": job_id,
            "status": job.get("status") or "pending",
            "error": job.get("error") or "",
            "step": job.get("step") or "",
            "filename": job.get("download_name") or "",
            "stats": job.get("stats"),
            "build": BUILD_ID,
        }
    )


@app.get("/api/jobs/<job_id>/file")
def job_file(job_id: str):
    job = resolve_job(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Conversia a expirat. Reîncărcați arhiva ZIP."}), 404
    if job.get("status") != "done":
        return jsonify({"ok": False, "error": job.get("error") or "Fișierul nu este gata."}), 409

    path = job.get("xlsx_path") or os.path.join(job_dir(job_id), "export.xlsx")
    if not os.path.isfile(path):
        return jsonify({"ok": False, "error": "Fișierul convertit nu mai este disponibil."}), 404

    download_name = job.get("download_name") or "deviz360_export.xlsx"
    stats = job.get("stats") or {}
    with open(path, "rb") as fh:
        data = fh.read()

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
