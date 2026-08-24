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

  function renderStats(headers) {
    const items = [
      ["Obiect", headers.get("X-WinDev-Object") || "—"],
      ["Norme", headers.get("X-WinDev-Norms") || "—"],
      ["Devize", headers.get("X-WinDev-Devizes") || "—"],
      ["Rânduri", headers.get("X-WinDev-Rows") || "—"],
      ["Cheltuieli directe", headers.get("X-WinDev-Total") ? headers.get("X-WinDev-Total") + " lei" : "—"],
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
      showError("Selectați o arhivă ZIP sau RAR.");
      return;
    }

    const fd = new FormData();
    fd.append("kos_zip", file);

    setLoading(true);
    try {
      const res = await fetch(apiUrl, { method: "POST", body: fd });
      if (!res.ok) {
        let msg = "Conversia a eșuat.";
        try {
          const data = await res.json();
          if (data.error) msg = data.error;
        } catch (_) {
          /* răspuns non-JSON */
        }
        throw new Error(msg);
      }

      const blob = await res.blob();
      const disp = res.headers.get("Content-Disposition") || "";
      let filename = "deviz360_export.xlsx";
      const match = /filename\*?=(?:UTF-8''|")?([^";]+)/i.exec(disp);
      if (match) filename = decodeURIComponent(match[1].replace(/"/g, ""));

      downloadBlob(blob, filename);
      renderStats(res.headers);

      successBox.textContent = "Fișierul a fost generat și descărcat cu succes.";
      successBox.classList.remove("hidden");
    } catch (err) {
      showError(err.message || "Eroare necunoscută.");
    } finally {
      setLoading(false);
    }
  });
})();
