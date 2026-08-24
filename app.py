# -*- coding: utf-8 -*-
"""Interfață grafică pentru convertorul Winsmeta -> Deviz360."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from winsmeta_to_deviz360 import convert_kos_to_deviz360_xlsx, default_output_path_deviz360


class ConverterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Winsmeta KOS -> Deviz360")
        self.geometry("780x440")
        self.resizable(False, False)

        self.kos_var = tk.StringVar()
        self.out_var = tk.StringVar()
        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 8}
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Convertor Winsmeta (.KOS) -> Deviz360 (.xlsx)",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text="Selectați folderul WINSMETA.KOS și salvați fișierul Excel pentru import în Deviz360.",
            wraplength=720,
        ).pack(anchor="w", pady=(8, 16))

        kos_row = ttk.Frame(frame)
        kos_row.pack(fill="x", **pad)
        ttk.Label(kos_row, text="Folder KOS:", width=14).pack(side="left")
        ttk.Entry(kos_row, textvariable=self.kos_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(kos_row, text="Browse...", command=self._pick_kos).pack(side="left")

        out_row = ttk.Frame(frame)
        out_row.pack(fill="x", **pad)
        ttk.Label(out_row, text="Fișier output:", width=14).pack(side="left")
        ttk.Entry(out_row, textvariable=self.out_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(out_row, text="Browse...", command=self._pick_out).pack(side="left")

        btns = ttk.Frame(frame)
        btns.pack(fill="x", pady=(16, 8))
        ttk.Button(btns, text="Convertește", command=self._convert).pack(side="left")
        ttk.Button(btns, text="Închide", command=self.destroy).pack(side="left", padx=8)

        self.log = tk.Text(frame, height=13, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, pady=(8, 0))

        default_kos = os.path.join(os.path.dirname(os.path.abspath(__file__)), "WINSMETA.KOS")
        if os.path.isdir(default_kos):
            self.kos_var.set(default_kos)
            self.out_var.set(default_output_path_deviz360(default_kos))

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _pick_kos(self) -> None:
        path = filedialog.askdirectory(title="Selectați folderul WINSMETA.KOS")
        if path:
            self.kos_var.set(path)
            self.out_var.set(default_output_path_deviz360(path))

    def _pick_out(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Salvați fișierul Deviz360",
            defaultextension=".xlsx",
            filetypes=[
                ("Deviz360 Excel", "*.xlsx"),
                ("Toate fișierele", "*.*"),
            ],
        )
        if path:
            self.out_var.set(path)

    def _convert(self) -> None:
        kos_path = self.kos_var.get().strip()
        out_path = self.out_var.get().strip()

        if not kos_path or not os.path.isdir(kos_path):
            messagebox.showerror("Eroare", "Selectați un folder KOS valid.")
            return
        if not out_path:
            out_path = default_output_path_deviz360(kos_path)
            self.out_var.set(out_path)

        try:
            count, info, norm_count, sheet_count, mat, man, uti, total = convert_kos_to_deviz360_xlsx(
                kos_path, out_path
            )
            self._append_log(
                f"Deviz360: {count} rânduri, {norm_count} norme, {sheet_count} devize + Centralizator."
            )
            self._append_log(
                f"Cheltuieli directe: {total:,.2f} lei "
                f"(mat {mat:,.2f}, man {man:,.2f}, uti {uti:,.2f})."
            )
            self._append_log(f"Obiect: {info.obiect}")
            self._append_log(f"Fișier: {out_path}")
            messagebox.showinfo(
                "Succes",
                f"Fișier generat cu succes:\n{out_path}\n\n"
                f"Devize: {sheet_count}\nRânduri: {count}\nNorme: {norm_count}",
            )
        except Exception as exc:
            self._append_log(f"Eroare: {exc}")
            messagebox.showerror("Eroare la conversie", str(exc))


def main() -> None:
    ConverterApp().mainloop()


if __name__ == "__main__":
    main()
