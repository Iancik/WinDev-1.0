# -*- coding: utf-8 -*-
"""WinDev — aplicație web Flask: Winsmeta KOS -> Deviz360."""

from __future__ import annotations

import io
import os
import sys
import tempfile

from flask import Flask, jsonify, render_template, request, send_file

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from winsmeta_to_deviz360 import convert_kos_to_deviz360_xlsx
from web.kos_utils import (
    KosUploadError,
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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "app": "WinDev"})


@app.post("/api/convert")
def convert():
    if "kos_zip" not in request.files:
        return jsonify({"ok": False, "error": "Lipsește fișierul arhivă."}), 400

    upload = request.files["kos_zip"]
    if not upload.filename:
        return jsonify({"ok": False, "error": "Selectați o arhivă ZIP sau RAR."}), 400

    ext = os.path.splitext(upload.filename)[1].lower() or ".zip"
    if ext not in (".zip", ".rar"):
        return jsonify({"ok": False, "error": "Acceptăm doar arhive ZIP sau RAR."}), 400

    tmp_archive = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    work_dir = ""
    try:
        upload.save(tmp_archive.name)
        tmp_archive.close()

        kos_path, work_dir = prepare_kos_from_upload(tmp_archive.name, upload.filename)
        out_path = make_output_xlsx(work_dir)

        count, info, norm_count, sheets, _mat, _man, _uti, total = convert_kos_to_deviz360_xlsx(
            kos_path, out_path
        )

        with open(out_path, "rb") as f:
            data = f.read()

        download_name = safe_download_name(upload.filename)
        buf = io.BytesIO(data)
        buf.seek(0)

        response = send_file(
            buf,
            as_attachment=True,
            download_name=download_name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response.headers["X-WinDev-Rows"] = str(count)
        response.headers["X-WinDev-Norms"] = str(norm_count)
        response.headers["X-WinDev-Devizes"] = str(sheets)
        response.headers["X-WinDev-Object"] = info.obiect or ""
        response.headers["X-WinDev-Total"] = f"{total:.2f}"
        return response

    except KosUploadError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        try:
            os.unlink(tmp_archive.name)
        except OSError:
            pass
        if work_dir:
            cleanup_work_dir(work_dir)


def create_app():
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or os.environ.get("WINDEV_PORT", "8080"))
    debug = os.environ.get("WINDEV_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
