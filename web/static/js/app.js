(function () {
  const form = document.getElementById("convert-form");
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("kos_zip");
  const browseBtn = document.getElementById("browse-btn");
  const fileNameEl = document.getElementById("file-name");
  const submitBtn = document.getElementById("submit-btn");
  const spinner = document.getElementById("spinner");
  const btnLabel = submitBtn.querySelector(".btn-label");
  const errorBox = document.getElementById("error-box");
  const successBox = document.getElementById("success-box");
  const statsCard = document.getElementById("stats-card");
  const statsGrid = document.getElementById("stats-grid");

  const apiUrl = document.body.dataset.apiUrl || "/api/convert";

  function hideAlerts() {
    errorBox.classList.add("hidden");
    successBox.classList.add("hidden");
  }

  function showError(msg) {
    hideAlerts();
    errorBox.textContent = msg;
    errorBox.classList.remove("hidden");
  }

  function setLoading(on) {
    submitBtn.disabled = on || !fileInput.files.length;
    spinner.classList.toggle("hidden", !on);
    btnLabel.textContent = on ? "Se convertește…" : "Convertește în Deviz360";
  }

  function updateFileUI() {
    const file = fileInput.files[0];
    fileNameEl.textContent = file ? file.name : "";
    submitBtn.disabled = !file;
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function parseError(res, raw) {
    let msg = "Conversia a eșuat.";
    try {
      const data = JSON.parse(raw);
      if (data.error) msg = data.error;
    } catch (_) {
      if (res.status === 413) msg = "Fișierul este prea mare (maximum 80 MB).";
      else if (res.status === 502 || res.status === 503 || res.status === 504) {
        msg = "Serverul este ocupat. Așteptați 30 de secunde și reîncercați.";
      } else {
        msg = "Conversia a eșuat (cod " + res.status + ").";
      }
    }
    return msg;
  }

  function renderStats(stats) {
    const items = [
      ["Obiect", (stats && stats.obiect) || "—"],
      ["Norme", (stats && stats.norms) || "—"],
      ["Devize", (stats && stats.devizes) || "—"],
      ["Rânduri", (stats && stats.rows) || "—"],
      ["Cheltuieli directe", stats && stats.total ? stats.total + " lei" : "—"],
    ];
    statsGrid.innerHTML = items
      .map(
        ([label, val]) =>
          `<div><dt>${label}</dt><dd>${escapeHtml(String(val))}</dd></div>`
      )
      .join("");
    statsCard.classList.remove("hidden");
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  browseBtn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    fileInput.click();
  });

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", updateFileUI);

  ["dragenter", "dragover"].forEach((ev) => {
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((ev) => {
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length) {
      fileInput.files = files;
      updateFileUI();
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlerts();
    statsCard.classList.add("hidden");

    const file = fileInput.files[0];
    if (!file) {
      showError("Selectați o arhivă ZIP.");
      return;
    }

    const fd = new FormData();
    fd.append("kos_zip", file);

    setLoading(true);
    try {
      const startRes = await fetch(apiUrl, { method: "POST", body: fd });
      const startRaw = await startRes.text();
      if (!startRes.ok) {
        throw new Error(parseError(startRes, startRaw));
      }
      let startData;
      try {
        startData = JSON.parse(startRaw);
      } catch (_) {
        throw new Error("Răspuns invalid de la server. Faceți Manual Deploy pe Render, apoi reîncercați.");
      }
      const jobId = startData.job_id;
      if (!jobId) {
        throw new Error("Serverul nu a pornit conversia. Faceți Manual Deploy pe Render.");
      }

      const deadline = Date.now() + 4 * 60 * 1000;
      let job;
      while (Date.now() < deadline) {
        await sleep(1500);
        const stRes = await fetch("/api/jobs/" + jobId);
        const stRaw = await stRes.text();
        if (!stRes.ok) {
          throw new Error(parseError(stRes, stRaw));
        }
        job = JSON.parse(stRaw);
        if (job.status === "error") {
          throw new Error(job.error || "Conversia a eșuat pe server.");
        }
        if (job.status === "done") {
          break;
        }
      }
      if (!job || job.status !== "done") {
        throw new Error("Conversia durează prea mult. Reîncercați cu un ZIP mai mic.");
      }

      const fileRes = await fetch("/api/jobs/" + jobId + "/file");
      if (!fileRes.ok) {
        throw new Error(parseError(fileRes, await fileRes.text()));
      }
      const blob = await fileRes.blob();
      downloadBlob(blob, job.filename || "deviz360_export.xlsx");
      renderStats(job.stats || {});

      successBox.textContent = "Fișierul a fost generat și descărcat cu succes.";
      successBox.classList.remove("hidden");
    } catch (err) {
      showError(err.message || "Eroare necunoscută.");
    } finally {
      setLoading(false);
    }
  });
})();
