# -*- coding: utf-8 -*-
"""Citire tabele Paradox (.DB) fără pxlib/pypxlib (stabil pe Linux)."""

from __future__ import annotations

import struct
from typing import Any, Dict, List, Optional, Tuple

# Tipuri Paradox (pxlib)
PX_ALPHA = 1
PX_DATE = 2
PX_SHORT = 3
PX_LONG = 4
PX_CURRENCY = 5
PX_NUMBER = 6
PX_LOGICAL = 9
PX_MEMO = 12
PX_BLOB = 13
PX_FMTMEMO = 14
PX_OLE = 15
PX_GRAPHIC = 16
PX_TIME = 20
PX_TIMESTAMP = 21
PX_AUTOINC = 22
PX_BCD = 23
PX_BYTES = 24


def _u16(buf: bytes, off: int) -> int:
    return struct.unpack_from("<H", buf, off)[0]


def _i16(buf: bytes, off: int) -> int:
    return struct.unpack_from("<h", buf, off)[0]


def _u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def _decode_short(data: bytes) -> Optional[int]:
    if len(data) < 2 or data == b"\x00\x00":
        return None
    v = struct.unpack(">h", data[:2])[0]
    if v == 0:
        return None
    if v < 0:
        return v + 0x8000
    return v - 0x8000


def _decode_long(data: bytes) -> Optional[int]:
    if len(data) < 4 or data == b"\x00\x00\x00\x00":
        return None
    v = struct.unpack(">i", data[:4])[0]
    if v == 0:
        return None
    if v < 0:
        return v + 0x80000000
    return v - 0x80000000


def _decode_number(data: bytes) -> Optional[float]:
    if len(data) < 8 or data == b"\x00" * 8:
        return None
    raw = bytearray(data[:8])
    if raw[0] & 0x80:
        raw[0] &= 0x7F
    else:
        raw = bytearray((~b) & 0xFF for b in raw)
    try:
        return struct.unpack(">d", bytes(raw))[0]
    except struct.error:
        return None


def _decode_alpha(data: bytes) -> str:
    text = data.split(b"\x00", 1)[0]
    for enc in ("cp1250", "cp866", "cp1251", "latin1"):
        try:
            return text.decode(enc).strip()
        except UnicodeDecodeError:
            continue
    return text.decode("latin1", "replace").strip()


def _decode_field(ftype: int, data: bytes) -> Any:
    if ftype == PX_ALPHA:
        return _decode_alpha(data)
    if ftype == PX_SHORT:
        return _decode_short(data)
    if ftype in (PX_LONG, PX_AUTOINC, PX_DATE, PX_TIME):
        return _decode_long(data)
    if ftype in (PX_NUMBER, PX_CURRENCY, PX_TIMESTAMP):
        return _decode_number(data)
    if ftype == PX_LOGICAL:
        if not data or data[0] == 0:
            return None
        return bool(data[0] & 0x7F)
    if ftype in (PX_MEMO, PX_FMTMEMO, PX_BLOB, PX_OLE, PX_GRAPHIC):
        inline = data[:-10] if len(data) > 10 else data
        return _decode_alpha(inline)
    if ftype == PX_BCD:
        return _decode_alpha(data)
    if ftype == PX_BYTES:
        return data
    return _decode_alpha(data)


def _parse_header(blob: bytes) -> Dict[str, Any]:
    if len(blob) < 88:
        raise ValueError("Fișier Paradox prea scurt.")
    record_size = _u16(blob, 0)
    header_size = _u16(blob, 2)
    file_type = blob[4]
    max_table_size = blob[5]
    num_records = _u32(blob, 6)
    file_blocks = _u16(blob, 12)
    first_block = _u16(blob, 14)
    last_block = _u16(blob, 16)
    num_fields = _u16(blob, 0x21)
    file_version_id = blob[0x39]
    encryption = _u32(blob, 0x25)
    if record_size == 0 or header_size == 0 or max_table_size < 1 or max_table_size > 32:
        raise ValueError("Antet Paradox invalid.")
    if encryption not in (0, 0xFF00FF00):
        raise ValueError("Tabela Paradox este criptată și nu poate fi citită.")
    return {
        "record_size": record_size,
        "header_size": header_size,
        "file_type": file_type,
        "max_table_size": max_table_size,
        "num_records": num_records,
        "file_blocks": file_blocks,
        "first_block": first_block,
        "last_block": last_block,
        "num_fields": num_fields,
        "file_version_id": file_version_id,
    }


def _field_info_offset(header: Dict[str, Any]) -> int:
    off = 88
    if header["file_version_id"] >= 5:
        off += 32
    return off


def read_paradox_table(path: str) -> List[Dict[str, Any]]:
    with open(path, "rb") as fh:
        blob = fh.read()
    header = _parse_header(blob)
    nfields = header["num_fields"]
    if nfields < 1 or nfields > 255:
        raise ValueError(f"Număr invalid de câmpuri Paradox: {nfields}")

    info_off = _field_info_offset(header)
    fields: List[Tuple[str, int, int]] = []
    pos = info_off
    types_sizes: List[Tuple[int, int]] = []
    for _ in range(nfields):
        if pos + 2 > len(blob):
            raise ValueError("Antet Paradox trunchiat (câmpuri).")
        types_sizes.append((blob[pos], blob[pos + 1]))
        pos += 2

    pos += 4
    if header["file_type"] in (0, 2, 3, 5, 6, 8):
        pos += 4 * nfields

    tablenamelen = 261 if header["file_version_id"] >= 12 else 79
    pos += tablenamelen

    names: List[str] = []
    for _ in range(nfields):
        end = blob.find(b"\x00", pos)
        if end < 0:
            raise ValueError("Nume de câmp Paradox trunchiat.")
        names.append(_decode_alpha(blob[pos:end]))
        pos = end + 1

    for name, (ftype, flen) in zip(names, types_sizes):
        if ftype == PX_BCD:
            flen = 17
        fields.append((name, ftype, flen))

    rec_size = header["record_size"]
    block_size = header["max_table_size"] * 0x400
    header_size = header["header_size"]
    rows: List[Dict[str, Any]] = []
    seen_blocks = set()
    blocknr = header["first_block"]
    max_loops = max(header["file_blocks"] + 2, 8)

    for _ in range(max_loops):
        if blocknr <= 0 or blocknr in seen_blocks:
            break
        seen_blocks.add(blocknr)
        offset = header_size + (blocknr - 1) * block_size
        if offset + 6 > len(blob):
            break
        next_block = _u16(blob, offset)
        add_data = _i16(blob, offset + 4)
        nrec = add_data // rec_size + 1 if rec_size else 0
        max_fit = max((block_size - 6) // rec_size, 0)
        nrec = max(0, min(nrec, max_fit))
        rec_pos = offset + 6
        for _i in range(nrec):
            rec = blob[rec_pos : rec_pos + rec_size]
            if len(rec) < rec_size:
                break
            rec_pos += rec_size
            if rec == b"\x00" * rec_size:
                continue
            row: Dict[str, Any] = {}
            cur = 0
            for name, ftype, flen in fields:
                row[name] = _decode_field(ftype, rec[cur : cur + flen])
                cur += flen
            rows.append(row)
            if header["num_records"] and len(rows) >= header["num_records"]:
                return rows
        blocknr = next_block

    return rows
