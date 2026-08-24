# -*- coding: utf-8 -*-
"""
Citire Winsmeta (.KOS) și utilitare comune pentru export Deviz360.

Citește baza Paradox din folderul proiectului Winsmeta.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from pypxlib import Table

DEVIZ_COLUMNS = [
    "Tip",
    "Pozitie",
    "PozitieGrup",
    "Simbol",
    "Denumire",
    "CantitateArticol",
    "CantitateinArticol",
    "CantitateTotala",
    "Um",
    "Pret",
    "PretMat",
    "PretMan",
    "PretUti",
    "PretTr",
    "PretTotal",
    "CodPretAuto",
    "PretAuto",
    "MonedaPretAuto",
    "TipPret",
    "SporMan",
    "SporMat",
    "SporUti",
    "Moneda",
    "NotaSubsol",
    "Provenienta",
    "Distanta",
    "CursEuroDeviz",
    "Greutate",
    "codArticol",
    "codRecapitulatie",
    "CantitateDeviz",
    "codProvenienta",
    "TipUtilaj",
    "CantitateBeneficiar",
]

WINSMETA_INDEKS_TO_DEVIZ_TIP = {
    2: 1,
    1: 2,
    4: 3,
}


@dataclass
class ProjectInfo:
    obiectiv: str = ""
    obiect: str = ""
    deviz: str = ""
    moneda: str = "lei"
    data_deviz: str = ""


@dataclass
class KosData:
    pozycje: Dict[int, Dict[str, Any]]
    naklady: Dict[int, List[Dict[str, Any]]]
    indeks: Dict[int, Dict[str, Any]]
    jedn: Dict[int, Dict[str, Any]]
    defnarz: Dict[int, Dict[str, Any]]
    narzuty: Dict[int, List[Dict[str, Any]]]
    info: ProjectInfo


# Mapare narzute Winsmeta -> PozitieGrup Devizonline
NARZUT_POZITIE_GRUP = {
    16: 101,  # Asigurari sociale
    17: 102,  # Cheltuieli de transport
    15: 103,  # Cheltuieli pentru depozitare
    20: 201,  # Cheltuieli de regie
    22: 301,  # Beneficiu de deviz
}

NARZUT_LABELS = {
    16: "Asigurari sociale",
    17: "Cheltuieli de transport",
    15: "Cheltuieli pentru depozitare",
    20: "Cheltuieli de regie",
    22: "Beneficiu de deviz",
}


def _cyrillic_count(text: str) -> int:
    return sum(1 for ch in text if "\u0400" <= ch <= "\u04FF")


def _romanian_diacritics_count(text: str) -> int:
    return sum(1 for ch in text if ch in "ăâîșțĂÂÎȘȚ")


def _mojibake_count(text: str) -> int:
    """Caractere tipice când chirilic CP866 e citit greșit ca CP1250/CP1251."""
    bad = "ÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßðñòóôõö÷øùúûüýþ‹›«»‚‘’""ŤŹťŻŻá"
    return sum(1 for ch in text if ch in bad)


def _encoding_score(text: str) -> int:
    # Preferă româna (cp1250); chirilicul nu trebuie să câștige pe texte de deviz.
    score = _romanian_diacritics_count(text) * 8
    score += _cyrillic_count(text)
    score -= _mojibake_count(text) * 4
    score -= text.count("\ufffd") * 20
    return score


_TEXT_ENCODINGS = ("cp1250", "cp1251", "cp866")


def _decode_high_byte_run(chunk: bytes) -> str:
    """Decodare segment cu bytes >= 0x80 (ex. marca «ЛСЭПЛ» în CP866)."""
    if not chunk:
        return ""

    best_text = chunk.decode("latin1")
    best_score = _encoding_score(best_text) - 1000
    for enc in _TEXT_ENCODINGS:
        try:
            text = chunk.decode(enc)
        except UnicodeDecodeError:
            text = chunk.decode(enc, errors="replace")
        score = _encoding_score(text)
        if enc == "cp1250" and _romanian_diacritics_count(text):
            score += 5
        if score > best_score:
            best_score = score
            best_text = text
    return best_text


def _decode_mixed_bytes(raw: bytes) -> str:
    """Păstrează ASCII; segmentele non-ASCII le decodează separat (CP866/CP1251/CP1250)."""
    if not raw:
        return ""

    parts: List[str] = []
    i = 0
    n = len(raw)
    while i < n:
        if raw[i] < 0x80:
            j = i
            while j < n and raw[j] < 0x80:
                j += 1
            parts.append(raw[i:j].decode("ascii"))
            i = j
        else:
            j = i
            while j < n and raw[j] >= 0x80:
                j += 1
            parts.append(_decode_high_byte_run(raw[i:j]))
            i = j
    return "".join(parts).rstrip("\x00").strip()


def _decode_bytes_smart(raw: bytes) -> str:
    mixed = _decode_mixed_bytes(raw)
    best_text = mixed
    best_score = _encoding_score(mixed)
    for enc in _TEXT_ENCODINGS + ("utf-8", "latin1"):
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        score = _encoding_score(text)
        if enc == "cp1250" and _romanian_diacritics_count(text):
            score += 2
        if score > best_score:
            best_score = score
            best_text = text
    return best_text.rstrip("\x00").strip()


def _fix_string_encoding(text: str) -> str:
    """Repară text deja decodat greșit, fără a transforma româna în chirilic."""
    if not text:
        return text

    cleaned = text.rstrip("\x00").strip()
    if _romanian_diacritics_count(cleaned) and _mojibake_count(cleaned) == 0:
        return cleaned

    best = cleaned
    best_score = _encoding_score(cleaned)

    for src, dst in (
        ("cp1250", "cp866"),
        ("cp1251", "cp866"),
        ("cp1250", "cp1251"),
        ("cp1251", "cp1250"),
        ("cp866", "cp1250"),
    ):
        try:
            alt = cleaned.encode(src).decode(dst)
            score = _encoding_score(alt)
            if score > best_score:
                best_score = score
                best = alt
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue

    for src in ("cp1251", "cp1250", "latin1"):
        try:
            alt = _decode_mixed_bytes(cleaned.encode(src))
            score = _encoding_score(alt)
            if score > best_score:
                best_score = score
                best = alt
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue

    return best.rstrip("\x00").strip()


def _dec(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bytes):
        return _decode_bytes_smart(value)
    if isinstance(value, str):
        return _fix_string_encoding(value)
    return value


def _safe_row(table: Table, row) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for name in table.fields:
        try:
            result[name] = _dec(row[name])
        except Exception:
            result[name] = None
    return result


def _kos_file(kos_path: str, name: str) -> Optional[str]:
    """Găsește un fișier KOS ignorând majuscule (Linux vs. Windows)."""
    want = name.upper()
    try:
        for entry in os.listdir(kos_path):
            if entry.upper() == want:
                return os.path.join(kos_path, entry)
    except OSError:
        return None
    return None


def _read_dane(kos_path: str) -> ProjectInfo:
    info = ProjectInfo()
    dane_path = _kos_file(kos_path, "DANE.DB")
    if not dane_path:
        return info

    table = Table(dane_path, encoding="cp1250")
    for row in table:
        data = _safe_row(table, row)
        obiectiv = data.get("UmowaBudowa") or data.get("UmowaObiekt") or ""
        obiect = data.get("UmowaRodzaj") or data.get("UmowaObiekt") or ""
        kos_nr = data.get("KosNr") or ""
        info.obiectiv = str(obiectiv or "")
        info.obiect = str(obiect or "")
        info.deviz = f"Deviz {kos_nr}".strip() if kos_nr else "Deviz Winsmeta"
        info.moneda = str(data.get("KosWaluta") or "lei")
        kos_data = data.get("KosData")
        if kos_data:
            info.data_deviz = str(kos_data)
        break

    return info


def load_kos(kos_path: str) -> KosData:
    if not os.path.isdir(kos_path):
        raise FileNotFoundError(f"Folderul KOS nu există: {kos_path}")

    poz_path = _kos_file(kos_path, "POZYCJE.DB")
    if not poz_path:
        raise FileNotFoundError(f"Nu am găsit POZYCJE.DB în {kos_path}")

    poz_t = Table(poz_path, encoding="cp1250")
    pozycje = {row["Nr"]: _safe_row(poz_t, row) for row in poz_t}

    naklady: Dict[int, List[Dict[str, Any]]] = {}
    nak_path = _kos_file(kos_path, "NAKLADY.DB")
    if nak_path:
        nak_t = Table(nak_path, encoding="cp1250")
        for row in nak_t:
            item = _safe_row(nak_t, row)
            naklady.setdefault(item["NrPoz"], []).append(item)

    indeks: Dict[int, Dict[str, Any]] = {}
    ind_path = _kos_file(kos_path, "INDEKS.DB")
    if ind_path:
        ind_t = Table(ind_path, encoding="cp1250")
        indeks = {row["NrInd"]: _safe_row(ind_t, row) for row in ind_t}

    jedn: Dict[int, Dict[str, Any]] = {}
    jed_path = _kos_file(kos_path, "JEDN.DB")
    if jed_path:
        jed_t = Table(jed_path, encoding="cp1250")
        jedn = {row["Nr"]: _safe_row(jed_t, row) for row in jed_t}

    defnarz: Dict[int, Dict[str, Any]] = {}
    def_path = _kos_file(kos_path, "DEFNARZ.DB")
    if def_path:
        def_t = Table(def_path, encoding="cp1250")
        defnarz = {row["NrNarzutu"]: _safe_row(def_t, row) for row in def_t}

    narzuty: Dict[int, List[Dict[str, Any]]] = {}
    nar_path = _kos_file(kos_path, "NARZUTY.DB")
    if nar_path:
        nar_t = Table(nar_path, encoding="cp1250")
        for row in nar_t:
            item = _safe_row(nar_t, row)
            narzuty.setdefault(item["NrPoz"], []).append(item)

    return KosData(
        pozycje=pozycje,
        naklady=naklady,
        indeks=indeks,
        jedn=jedn,
        defnarz=defnarz,
        narzuty=narzuty,
        info=_read_dane(kos_path),
    )


def _pick_name(nazwa: Any, nazwa2: Any = None) -> str:
    """Winsmeta stochează denumirea scurtă în Nazwa (~10 car.) și cea completă în Nazwa2."""
    full = str(_dec(nazwa2) or "").strip()
    short = str(_dec(nazwa) or "").strip()
    if full:
        return full
    return short


def _unit_symbol(jedn: Dict[int, Dict[str, Any]], nr_jedn: Optional[int]) -> str:
    if not nr_jedn:
        return ""
    return str(jedn.get(nr_jedn, {}).get("Symbol") or "")


def _component_totals(naklady: List[Dict[str, Any]], indeks: Dict[int, Dict[str, Any]]) -> Tuple[float, float, float, float]:
    mat = man = uti = total = 0.0
    for item in naklady:
        ir = indeks.get(item.get("NrInd"), {})
        typ = ir.get("Typ")
        val = float(item.get("Wartosc") or 0.0)
        total += val
        if typ == 2:
            mat += val
        elif typ == 1:
            man += val
        elif typ == 4:
            uti += val
    return mat, man, uti, total


def _empty_row() -> Dict[str, Any]:
    return {col: "" for col in DEVIZ_COLUMNS}


def _base_defaults(info: ProjectInfo, provenienta: str, tip_pret: float) -> Dict[str, Any]:
    row = _empty_row()
    row["MonedaPretAuto"] = info.moneda
    row["Moneda"] = info.moneda
    row["TipPret"] = tip_pret
    row["Provenienta"] = provenienta
    row["CantitateDeviz"] = 1.0
    row["TipUtilaj"] = "a"
    return row


def _item_defaults(info: ProjectInfo, provenienta: str, tip_pret: float) -> Dict[str, Any]:
    row = _base_defaults(info, provenienta, tip_pret)
    row["PozitieGrup"] = 0
    return row


def _header_row(text: str, info: ProjectInfo) -> Dict[str, Any]:
    row = _base_defaults(info, "C", 1.0)
    row["Simbol"] = "#R"
    row["Denumire"] = text
    return row


def _section_row(number: str, name: str, pozitie: int, info: ProjectInfo) -> Dict[str, Any]:
    row = _item_defaults(info, "C", 1.0)
    row["Tip"] = 100
    row["Pozitie"] = pozitie
    row["Denumire"] = f"{number}. {name}".strip()
    return row


def _chapter_total_row(title: str, pozitie: int, total: float, info: ProjectInfo) -> Dict[str, Any]:
    row = _item_defaults(info, "C", 1.0)
    row["Tip"] = 101
    row["Pozitie"] = pozitie
    row["Denumire"] = f"TOTAL {title}"
    row["PretTotal"] = round(total, 4)
    return row


def _label_row(denumire: str, info: ProjectInfo, **fields: Any) -> Dict[str, Any]:
    row = _empty_row()
    row["Denumire"] = denumire
    row["MonedaPretAuto"] = info.moneda
    row["Moneda"] = info.moneda
    for key, value in fields.items():
        if value != "" and value is not None:
            row[key] = value
    return row


def _wsp_for_resource(poz: Dict[str, Any], deviz_tip: int) -> float:
    """Coeficient pe normă (k / materiale marunte): WspR / WspM / WspS."""
    if deviz_tip == 1:
        wsp = float(poz.get("WspM") or 1.0)
    elif deviz_tip == 2:
        wsp = float(poz.get("WspR") or 1.0)
    elif deviz_tip == 3:
        wsp = float(poz.get("WspS") or 1.0)
    else:
        return 1.0
    if wsp <= 0:
        return 1.0
    return wsp


def _norm_row(
    poz: Dict[str, Any],
    pozitie: int,
    jedn: Dict[int, Dict[str, Any]],
    naklady: List[Dict[str, Any]],
    indeks: Dict[int, Dict[str, Any]],
    info: ProjectInfo,
    mat: Optional[float] = None,
    man: Optional[float] = None,
    uti: Optional[float] = None,
) -> Dict[str, Any]:
    qty = float(poz.get("Ilosc") or 0.0)
    if mat is None or man is None or uti is None:
        mat, man, uti, _total = _component_totals(naklady, indeks)
    total = mat + man + uti
    per_unit_total = total / qty if qty else total

    row = _item_defaults(info, "A", 1.0)
    row["Tip"] = 0
    row["Pozitie"] = pozitie
    row["Simbol"] = str(poz.get("Kod") or "")
    row["Denumire"] = _pick_name(poz.get("Nazwa"))
    row["CantitateArticol"] = qty
    row["CantitateinArticol"] = 1.0
    row["CantitateTotala"] = qty
    row["Um"] = _unit_symbol(jedn, poz.get("NrJedn"))
    row["PretMat"] = round(mat / qty, 4) if qty else round(mat, 4)
    row["PretMan"] = round(man / qty, 4) if qty else round(man, 4)
    row["PretUti"] = round(uti / qty, 4) if qty else round(uti, 4)
    row["PretTotal"] = round(per_unit_total, 4)
    row["codArticol"] = float(poz["Nr"]) * 1_000_000
    return row


def _component_row(
    parent: Dict[str, Any],
    nak: Dict[str, Any],
    indeks: Dict[int, Dict[str, Any]],
    jedn: Dict[int, Dict[str, Any]],
    info: ProjectInfo,
) -> Optional[Dict[str, Any]]:
    ir = indeks.get(nak.get("NrInd"), {})
    deviz_tip = WINSMETA_INDEKS_TO_DEVIZ_TIP.get(ir.get("Typ"))
    if deviz_tip is None:
        return None

    parent_qty = float(parent.get("Ilosc") or 0.0)
    base_norma = float(nak.get("Norma") or 0.0)
    cena = float(nak.get("Cena") or 0.0)
    wsp = _wsp_for_resource(parent, deviz_tip)
    norma = base_norma * wsp if wsp != 1.0 else base_norma
    total_qty = norma * parent_qty if parent_qty else norma
    base_total_qty = base_norma * parent_qty if parent_qty else base_norma
    if wsp != 1.0:
        val = cena * total_qty
    else:
        val = float(nak.get("Wartosc") or (cena * base_total_qty))

    row = _item_defaults(info, "AR", 2.0)
    row["Tip"] = deviz_tip
    row["Pozitie"] = parent.get("_pozitie", 1)
    row["Simbol"] = str(ir.get("Kod") or "")
    row["Denumire"] = _pick_name(ir.get("Nazwa"), ir.get("Nazwa2"))
    row["CantitateArticol"] = parent_qty
    row["CantitateinArticol"] = norma
    row["CantitateTotala"] = round(total_qty, 6)
    row["Um"] = _unit_symbol(jedn, ir.get("NrJedn"))
    row["Pret"] = cena

    if deviz_tip == 1:
        row["PretMat"] = round(val, 4)
    elif deviz_tip == 2:
        row["PretMan"] = round(val, 4)
    elif deviz_tip == 3:
        row["PretUti"] = round(val, 4)

    row["PretTotal"] = round(val, 4)
    row["codArticol"] = float(parent["Nr"]) * 1_000_000
    return row


def _collect_q_items(pozycje: Dict[int, Dict[str, Any]], nr: int) -> List[Dict[str, Any]]:
    """Colectează recursiv toate pozițiile Q dintr-un capitol (inclusiv subcapitole)."""
    items: List[Dict[str, Any]] = []
    poz = pozycje.get(nr)
    if not poz:
        return items
    if poz.get("Typ") == "Q":
        items.append(poz)
    child = poz.get("NrPod") or 0
    while child:
        items.extend(_collect_q_items(pozycje, child))
        child_poz = pozycje.get(child)
        child = child_poz.get("NrNast") if child_poz else 0
    return items


def _top_level_chapters(pozycje: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Returnează doar capitolele de nivel 1 (fără subcapitole Devizonline)."""
    root = pozycje.get(0)
    if not root:
        return []
    chapters: List[Dict[str, Any]] = []
    child = root.get("NrPod") or 0
    while child:
        poz = pozycje.get(child)
        if poz and poz.get("Typ") == "S":
            chapters.append(poz)
        child = poz.get("NrNast") if poz else 0
    return chapters


def _read_narzuty_percentages(data: KosData) -> Dict[int, float]:
    """Citește procentele narzute din KOS (DEFNARZ + NARZUTY) — toate pozițiile."""
    percentages: Dict[int, float] = {}
    for poz_items in data.narzuty.values():
        for item in poz_items:
            nr_narz = item.get("NrNarz")
            if nr_narz not in NARZUT_POZITIE_GRUP and nr_narz != 14:
                continue
            wielkosc = float(item.get("Wielkosc") or 0)
            if wielkosc > 0:
                percentages[nr_narz] = wielkosc
    return percentages


def _read_narzuty_for_chapter(data: KosData, chapter_nr: int) -> Dict[int, float]:
    """Narzute pentru un deviz/capitol: TVA de la rădăcină (0) + narzute pe capitol."""
    percentages: Dict[int, float] = {}
    for src in (0, chapter_nr):
        for item in data.narzuty.get(src, []):
            nr_narz = item.get("NrNarz")
            if nr_narz not in NARZUT_POZITIE_GRUP and nr_narz != 14:
                continue
            wielkosc = float(item.get("Wielkosc") or 0)
            if wielkosc > 0:
                percentages[nr_narz] = wielkosc
    return percentages


def _export_norm_block(
    data: KosData,
    poz: Dict[str, Any],
    pozitie: int,
) -> Tuple[List[Dict[str, Any]], float, float, float, float, float]:
    """Exportă o normă + resurse; returnează rânduri și totaluri pe categorii."""
    rows: List[Dict[str, Any]] = []
    nr = poz["Nr"]
    poz["_pozitie"] = pozitie
    naklady = data.naklady.get(nr, [])

    mat = man = uti = man_hours = 0.0
    comp_rows: List[Dict[str, Any]] = []

    for nak in sorted(naklady, key=lambda x: x.get("NrSkl", 0)):
        comp = _component_row(poz, nak, data.indeks, data.jedn, data.info)
        if not comp:
            continue
        comp_rows.append(comp)
        val = float(comp.get("PretTotal") or 0)
        tip = comp.get("Tip")
        if tip == 1:
            mat += val
        elif tip == 2:
            man += val
            man_hours += float(comp.get("CantitateTotala") or 0)
        elif tip == 3:
            uti += val

    rows.append(
        _norm_row(
            poz, pozitie, data.jedn, naklady, data.indeks, data.info, mat, man, uti
        )
    )
    rows.extend(comp_rows)

    line_total = mat + man + uti
    return rows, mat, man, uti, man_hours, line_total


def _build_recap_block(
    info: ProjectInfo,
    data: KosData,
    mat: float,
    man: float,
    uti: float,
    man_hours: float,
    narzuty_pct: Dict[int, float],
) -> List[Dict[str, Any]]:
    """Construiește blocul de recapitulație + narzute de la sfârșitul Excel-ului."""
    rows: List[Dict[str, Any]] = []
    cd = mat + man + uti

    rows.append(_label_row("Material", info, Pret=round(mat, 4)))
    rows.append(_label_row("Manopera", info, Pret=round(man, 4)))
    rows.append(_label_row("Utilaj", info, Pret=round(uti, 4)))
    rows.append(_label_row("Transport", info))
    rows.append(_label_row("Cheltuieli directe", info, Pret=round(cd, 4)))
    rows.append(_label_row("Greutate materiale", info))
    rows.append(_label_row("Total manopera", info, Pret=round(man_hours, 4)))
    rows.append(_label_row("Sporuri pe Deviz", info))
    rows.append(_label_row("Material", info))
    rows.append(_label_row("Manopera", info))
    rows.append(_label_row("Utilaj", info))
    rows.append(_empty_row())
    rows.append(_label_row("Recapitulatie", info))

    asig_pct = narzuty_pct.get(16, 0.0)
    trans_pct = narzuty_pct.get(17, 0.0)
    dep_pct = narzuty_pct.get(15, 0.0)
    regie_pct = narzuty_pct.get(20, 0.0)
    benef_pct = narzuty_pct.get(22, 0.0)
    tva_pct = narzuty_pct.get(14, 20.0)

    asig_val = man * asig_pct / 100.0
    trans_val = mat * trans_pct / 100.0
    dep_val = mat * dep_pct / 100.0
    sub1 = cd + asig_val + trans_val + dep_val
    regie_val = sub1 * regie_pct / 100.0
    sub2 = sub1 + regie_val
    benef_val = sub2 * benef_pct / 100.0

    recap_sum = asig_val + trans_val + dep_val + regie_val + benef_val
    total_before_tva = cd + recap_sum
    tva_val = total_before_tva * tva_pct / 100.0
    valoare = total_before_tva + tva_val

    narzut_order = [16, 17, 15, 20, 22]
    for nr_narz in narzut_order:
        pct = narzuty_pct.get(nr_narz, 0.0)
        if pct <= 0:
            continue
        if nr_narz == 16:
            val = asig_val
        elif nr_narz == 17:
            val = trans_val
        elif nr_narz == 15:
            val = dep_val
        elif nr_narz == 20:
            val = regie_val
        elif nr_narz == 22:
            val = benef_val
        else:
            val = 0.0

        label = NARZUT_LABELS.get(nr_narz)
        if not label:
            defn = data.defnarz.get(nr_narz, {})
            label = str(defn.get("Nazwa") or nr_narz)
        row = _empty_row()
        row["PozitieGrup"] = NARZUT_POZITIE_GRUP[nr_narz]
        row["Denumire"] = label
        row["CantitateArticol"] = pct
        row["Um"] = "%"
        row["CantitateTotala"] = round(val, 6)
        row["Pret"] = round(val, 6)
        rows.append(row)

    rows.append(_empty_row())
    rows.append(_label_row("Recapitulatie", info, CantitateArticol=round(recap_sum, 4)))
    rows.append(_label_row("Total", info, CantitateArticol=round(total_before_tva, 4)))
    tva_label = f"TVA({int(tva_pct)}%)" if tva_pct == int(tva_pct) else f"TVA({tva_pct}%)"
    rows.append(_label_row(tva_label, info, CantitateArticol=round(tva_val, 4)))
    rows.append(_label_row("Valoare", info, CantitateArticol=round(valoare, 4)))
    return rows
