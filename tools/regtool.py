#!/usr/bin/env python3
"""
regtool.py - Elden Ring regulation.bin reader/writer and version-upgrade merger.

Purpose: rebase a mod's regulation.bin (params) onto a newer vanilla game
version by adding every row that exists in the new vanilla regulation but
not in the mod, and applying known paramdef field changes. This mirrors
what Smithbox's "Param Upgrader" does, at the raw-row level.

Formats handled (verified byte-for-byte against SoulsFormats behaviour):
  regulation.bin = AES-256-CBC( DCX(ZSTD)( BND4( *.param ... ) ) )

Usage:
  regtool.py info      <regulation.bin>
  regtool.py roundtrip <regulation.bin>              # self-test: parse+write must be identical
  regtool.py upgrade   <mod.bin> <vanilla_old.bin> <vanilla_new.bin> <out.bin> [--report report.json]
                       (3-way merge: vanilla_old must be the vanilla regulation the mod was built on)

Requires: python3 >= 3.8 and EITHER the `zstandard` + `cryptography` modules OR the `zstd` + `openssl` command-line tools.
"""
import json
import os
import struct
import sys

import shutil
import subprocess

# Optional native modules; if absent, fall back to the `zstd` and `openssl` command-line tools
# (both ship with SteamOS / most Linux distros), so the patcher works with no pip at all.
try:
    import zstandard  # type: ignore
except ImportError:  # pragma: no cover
    zstandard = None
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes  # type: ignore
except ImportError:  # pragma: no cover
    Cipher = None
FORCE_CLI = os.environ.get("REGTOOL_FORCE_CLI") == "1"


def _need(tool):
    path = shutil.which(tool)
    if not path:
        raise SystemExit(f"regtool: neither the Python module nor the `{tool}` command-line tool is available. "
                         f"Either `pip install zstandard cryptography` or install `{tool}`.")
    return path

ER_REG_KEY = bytes.fromhex(
    "99BFFC366A6BC8C6F5827D093602D676C42892A01C207FB024D3AF4E493FEF99"
)

# --------------------------------------------------------------------------- AES


def aes_decrypt(data: bytes) -> bytes:
    iv, body = data[:16], data[16:]
    if Cipher is not None and not FORCE_CLI:
        dec = Cipher(algorithms.AES(ER_REG_KEY), modes.CBC(iv)).decryptor()
        return dec.update(body) + dec.finalize()
    return subprocess.run([_need("openssl"), "enc", "-d", "-aes-256-cbc", "-K", ER_REG_KEY.hex(), "-iv", iv.hex(), "-nopad"],
                          input=body, capture_output=True, check=True).stdout


def aes_encrypt(plain: bytes) -> bytes:
    iv = os.urandom(16)
    pad = 16 - (len(plain) % 16)
    padded = plain + bytes([pad]) * pad  # PKCS7, as SoulsFormats does
    if Cipher is not None and not FORCE_CLI:
        enc = Cipher(algorithms.AES(ER_REG_KEY), modes.CBC(iv)).encryptor()
        return iv + enc.update(padded) + enc.finalize()
    out = subprocess.run([_need("openssl"), "enc", "-aes-256-cbc", "-K", ER_REG_KEY.hex(), "-iv", iv.hex(), "-nopad"],
                         input=padded, capture_output=True, check=True).stdout
    return iv + out


# --------------------------------------------------------------------------- DCX (ZSTD)


def dcx_unwrap(d: bytes):
    """Returns (decompressed_bytes, zstd_level)."""
    assert d[:4] == b"DCX\0", "not a DCX"
    assert d[0x28:0x2C] == b"ZSTD", "only DCX_ZSTD is supported here"
    unc = struct.unpack(">I", d[0x1C:0x20])[0]
    comp = struct.unpack(">I", d[0x20:0x24])[0]
    level = d[0x30]
    dca = d.find(b"DCA\0")
    dca_size = struct.unpack(">I", d[dca + 4 : dca + 8])[0]
    start = dca + dca_size
    frame = d[start : start + comp]
    if zstandard is not None and not FORCE_CLI:
        out = zstandard.ZstdDecompressor().decompressobj().decompress(frame)
    else:
        out = subprocess.run([_need("zstd"), "-d", "-q", "-c"], input=frame, capture_output=True, check=True).stdout
    assert len(out) == unc, f"DCX size mismatch {len(out)} != {unc}"
    return out, level


def dcx_wrap(raw: bytes, level: int) -> bytes:
    # Match the zstd frame layout of files the game is known to accept (vanilla and Smithbox-written
    # regulations): frame header descriptor 0x00 = NO Frame_Content_Size field, no checksum, no dict id,
    # explicit window descriptor. A frame with a content-size field (FHD 0x80) is valid zstd but is not
    # what FromSoftware's reader expects; that mismatch crashed the game at boot on 1.17.
    if zstandard is not None and not FORCE_CLI:
        params = zstandard.ZstdCompressionParameters.from_level(level, window_log=16, write_content_size=False,
                                                               write_checksum=False, write_dict_id=False)
        comp = zstandard.ZstdCompressor(compression_params=params).compress(raw)
    else:
        comp = subprocess.run([_need("zstd"), "-q", "-c", f"-{level}", "--no-check", "--no-content-size", "--zstd=wlog=16"],
                              input=raw, capture_output=True, check=True).stdout
    assert comp[:4] == b"\x28\xb5\x2f\xfd" and comp[4] == 0x00, f"unexpected zstd frame header {comp[4]:#x}"
    h = bytearray()
    h += b"DCX\0" + struct.pack(">IIIII", 0x11000, 0x18, 0x24, 0x44, 0x4C)
    h += b"DCS\0" + struct.pack(">II", len(raw), len(comp))
    h += b"DCP\0" + b"ZSTD" + struct.pack(">I", 0x20) + bytes([level]) + b"\0" * 3
    h += struct.pack(">IIII", 0, 0, 0, 0x00010100)
    h += b"DCA\0" + struct.pack(">I", 8)
    assert len(h) == 0x4C
    return bytes(h) + comp


# --------------------------------------------------------------------------- BND4


def reverse_bits(v: int) -> int:
    return int(f"{v:08b}"[::-1], 2)


class BndFile:
    __slots__ = ("flags", "id", "name", "data")

    def __init__(self, flags, fid, name, data):
        self.flags, self.id, self.name, self.data = flags, fid, name, data


class Bnd4:
    def __init__(self):
        self.unk04 = self.unk05 = False
        self.big_endian = False
        self.bit_big_endian = False
        self.version = ""
        self.unicode = True
        self.format = 0
        self.extended = 0
        self.files = []

    # format flag helpers (SoulsFormats Binder.Format)
    @property
    def has_ids(self):
        return bool(self.format & 0x02)

    @property
    def has_names(self):
        return bool(self.format & 0x0C)

    @property
    def long_offsets(self):
        return bool(self.format & 0x10)

    @property
    def has_compression(self):
        return bool(self.format & 0x20)

    def file_header_size(self):
        return 0x10 + (8 if self.long_offsets else 4) + (8 if self.has_compression else 0) \
            + (4 if self.has_ids else 0) + (4 if self.has_names else 0) + (8 if self.format == 0x04 else 0)

    @classmethod
    def parse(cls, b: bytes):
        self = cls()
        assert b[:4] == b"BND4"
        self.unk04, self.unk05 = bool(b[4]), bool(b[5])
        self.big_endian = bool(b[9])
        self.bit_big_endian = not bool(b[10])
        assert not self.big_endian, "big-endian BND4 not expected for ER"
        count = struct.unpack("<i", b[0x0C:0x10])[0]
        assert struct.unpack("<q", b[0x10:0x18])[0] == 0x40
        self.version = b[0x18:0x20].rstrip(b"\0").decode("ascii")
        fhs = struct.unpack("<q", b[0x20:0x28])[0]
        self.unicode = bool(b[0x30])
        raw_fmt = b[0x31]
        self.format = raw_fmt if (self.bit_big_endian or raw_fmt & 0x80) else reverse_bits(raw_fmt)
        # SoulsFormats: reverse = bitBigEndian || ForceBigEndian(format)
        fmt_try = raw_fmt if self.bit_big_endian else reverse_bits(raw_fmt)
        if fmt_try & 0x01:  # ForceBigEndian means the raw value was the real one
            fmt_try = raw_fmt
        self.format = fmt_try
        self.extended = b[0x32]
        assert fhs == self.file_header_size(), f"file header size {fhs:#x} != expected {self.file_header_size():#x}"
        pos = 0x40
        for _ in range(count):
            raw_flags = b[pos]
            flags = raw_flags if self.bit_big_endian else reverse_bits(raw_flags)
            assert b[pos + 1 : pos + 4] == b"\0\0\0" and struct.unpack("<i", b[pos + 4 : pos + 8])[0] == -1
            p = pos + 8
            csize = struct.unpack("<q", b[p : p + 8])[0]; p += 8
            usize = -1
            if self.has_compression:
                usize = struct.unpack("<q", b[p : p + 8])[0]; p += 8
            if self.long_offsets:
                doff = struct.unpack("<q", b[p : p + 8])[0]; p += 8
            else:
                doff = struct.unpack("<I", b[p : p + 4])[0]; p += 4
            fid = -1
            if self.has_ids:
                fid = struct.unpack("<i", b[p : p + 4])[0]; p += 4
            name = None
            if self.has_names:
                noff = struct.unpack("<I", b[p : p + 4])[0]; p += 4
                if self.unicode:
                    end = b.find(b"\0\0", noff)
                    while (end - noff) % 2:  # align to UTF-16 code unit boundary
                        end = b.find(b"\0\0", end + 1)
                    name = b[noff:end].decode("utf-16-le")
                else:
                    name = b[noff : b.find(b"\0", noff)].decode("shift_jis")
            if self.format == 0x04:
                p += 8
            assert not (flags & 0x01), "compressed binder entries not expected in regulation"
            assert usize in (-1, csize)
            self.files.append(BndFile(flags, fid, name, b[doff : doff + csize]))
            pos += self.file_header_size()
        return self

    def write(self) -> bytes:
        out = bytearray()
        out += b"BND4"
        out += bytes([int(self.unk04), int(self.unk05), 0, 0, 0, int(self.big_endian), int(not self.bit_big_endian), 0])
        out += struct.pack("<i", len(self.files))
        out += struct.pack("<q", 0x40)
        out += self.version.encode("ascii").ljust(8, b"\0")
        out += struct.pack("<q", self.file_header_size())
        headers_end_pos = len(out); out += b"\0" * 8
        raw_fmt = self.format if (self.bit_big_endian or self.format & 0x01) else reverse_bits(self.format)
        out += bytes([int(self.unicode), raw_fmt, self.extended, 0])
        out += struct.pack("<i", 0)
        hash_off_pos = len(out); out += b"\0" * 8
        assert len(out) == 0x40
        entry_pos = []
        for f in self.files:
            entry_pos.append(len(out))
            raw_flags = f.flags if self.bit_big_endian else reverse_bits(f.flags)
            out += bytes([raw_flags, 0, 0, 0]) + struct.pack("<i", -1)
            out += b"\0" * 8  # compressed size (filled later)
            if self.has_compression:
                out += b"\0" * 8
            out += b"\0" * (8 if self.long_offsets else 4)
            if self.has_ids:
                out += struct.pack("<i", f.id)
            if self.has_names:
                out += b"\0" * 4
            if self.format == 0x04:
                out += struct.pack("<ii", f.id, 0)
        # names
        for i, f in enumerate(self.files):
            if self.has_names:
                noff = len(out)
                p = entry_pos[i] + 8 + 8 + (8 if self.has_compression else 0) + (8 if self.long_offsets else 4) + (4 if self.has_ids else 0)
                struct.pack_into("<I", out, p, noff)
                out += (f.name.encode("utf-16-le") + b"\0\0") if self.unicode else (f.name.encode("shift_jis") + b"\0")
        if self.extended == 4:
            while len(out) % 8:
                out += b"\0"
            struct.pack_into("<q", out, hash_off_pos, len(out))
            out += self._hash_table(len(out))
        struct.pack_into("<q", out, headers_end_pos, len(out))
        # data
        for i, f in enumerate(self.files):
            while len(out) % 0x10:
                out += b"\0"
            doff = len(out)
            out += f.data
            p = entry_pos[i] + 8
            struct.pack_into("<q", out, p, len(f.data)); p += 8
            if self.has_compression:
                struct.pack_into("<q", out, p, len(f.data)); p += 8
            if self.long_offsets:
                struct.pack_into("<q", out, p, doff)
            else:
                struct.pack_into("<I", out, p, doff)
        return bytes(out)

    def _hash_table(self, base: int) -> bytes:
        def is_prime(n):
            if n < 2: return False
            if n == 2: return True
            if n % 2 == 0: return False
            i = 3
            while i * i <= n:
                if n % i == 0: return False
                i += 2
            return True

        def path_hash(text):
            h = text.lower().replace("\\", "/")
            if not h.startswith("/"):
                h = "/" + h
            v = 0
            for c in h:
                v = (v * 37 + ord(c)) & 0xFFFFFFFF
            return v

        n = len(self.files)
        group_count = next(p for p in range(n // 7, 100001) if is_prime(p))
        lists = [[] for _ in range(group_count)]
        for i, f in enumerate(self.files):
            h = path_hash(f.name)
            lists[h % group_count].append((h, i))
        for l in lists:
            l.sort(key=lambda t: t[0])
        groups, hashes = [], []
        for l in lists:
            groups.append((len(hashes), len(l)))
            hashes.extend(l)
        out = bytearray()
        out += b"\0" * 8  # hashes offset
        out += struct.pack("<I", group_count) + bytes([0x10, 8, 8, 0])
        for idx, length in groups:
            out += struct.pack("<ii", length, idx)
        struct.pack_into("<q", out, 0, base + len(out))  # absolute offset, as SoulsFormats writes it
        for h, i in hashes:
            out += struct.pack("<Ii", h, i)
        return bytes(out)


# --------------------------------------------------------------------------- PARAM (row level)


class Param:
    """Row-level PARAM: keeps header bytes verbatim and rows as (id, data, name)."""

    def __init__(self):
        self.big_endian = False
        self.fmt2d = 0
        self.fmt2e = 0
        self.def_fmt_ver = 0
        self.unk06 = 0
        self.def_data_ver = 0
        self.param_type = ""
        self.rows = []  # list of [id, bytes, name|None]
        self.row_size = -1

    @property
    def long_offsets(self):
        return bool(self.fmt2d & 0x04)

    @property
    def offset_param_type(self):
        return bool(self.fmt2d & 0x80)

    @property
    def flag01_intdata(self):
        return (self.fmt2d & 0x01) and (self.fmt2d & 0x02)

    @classmethod
    def parse(cls, b: bytes):
        self = cls()
        self.big_endian = b[0x2C] == 0xFF
        assert not self.big_endian
        self.fmt2d, self.fmt2e, self.def_fmt_ver = b[0x2D], b[0x2E], b[0x2F]
        strings_off = struct.unpack("<I", b[0:4])[0]
        p = 4
        if (self.flag01_intdata) or self.long_offsets:
            assert b[p : p + 2] == b"\0\0"
        p += 2
        self.unk06, self.def_data_ver, row_count = struct.unpack("<hhH", b[p : p + 6]); p += 6
        actual_strings_off = 0
        if self.offset_param_type:
            assert struct.unpack("<i", b[p : p + 4])[0] == 0; p += 4
            pto = struct.unpack("<q", b[p : p + 8])[0]; p += 8
            assert b[p : p + 0x14] == b"\0" * 0x14; p += 0x14
            if pto < len(b):
                self.param_type = b[pto : b.find(b"\0", pto)].decode("ascii")
                actual_strings_off = pto
        else:
            self.param_type = b[p : p + 0x20].split(b"\0")[0].decode("ascii"); p += 0x20
        p += 4  # format bytes
        if self.flag01_intdata:
            p += 16
        elif self.long_offsets:
            p += 16
        entries = []
        for _ in range(row_count):
            if self.long_offsets:
                rid, _z, doff, noff = struct.unpack("<iiqq", b[p : p + 24]); p += 24
            else:
                rid, doff, noff = struct.unpack("<iII", b[p : p + 12]); p += 12
            name = None
            if noff:
                if actual_strings_off == 0 or noff < actual_strings_off:
                    actual_strings_off = noff
                if self.fmt2e & 0x01:
                    end = noff
                    while b[end : end + 2] != b"\0\0" or (end - noff) % 2:
                        end += 1
                    name = b[noff:end].decode("utf-16-le")
                else:
                    name = b[noff : b.find(b"\0", noff)].decode("shift_jis")
            entries.append((rid, doff, name))
        if row_count > 1:
            self.row_size = entries[1][1] - entries[0][1]
        elif row_count == 1:
            self.row_size = (actual_strings_off or strings_off) - entries[0][1]
        else:
            self.row_size = -1
        for rid, doff, name in entries:
            self.rows.append([rid, b[doff : doff + self.row_size], name])
        return self

    def write(self) -> bytes:
        out = bytearray()
        out += b"\0" * 4  # strings offset
        if self.flag01_intdata or self.long_offsets:
            out += b"\0\0"
        else:
            out += b"\0\0"  # data start (u16), filled later
        out += struct.pack("<hhH", self.unk06, self.def_data_ver, len(self.rows))
        pto_pos = None
        if self.offset_param_type:
            out += struct.pack("<i", 0)
            pto_pos = len(out); out += b"\0" * 8
            out += b"\0" * 0x14
        else:
            out += self.param_type.encode("ascii").ljust(0x20, b"\x20" if (self.fmt2d & 0x01) else b"\0")
        out += bytes([0xFF if self.big_endian else 0, self.fmt2d, self.fmt2e, self.def_fmt_ver])
        ds_pos = None
        if self.flag01_intdata:
            ds_pos = len(out); out += b"\0" * 16
        elif self.long_offsets:
            ds_pos = len(out); out += b"\0" * 16
        row_hdr_pos = []
        for rid, _d, _n in self.rows:
            row_hdr_pos.append(len(out))
            if self.long_offsets:
                out += struct.pack("<iiqq", rid, 0, 0, 0)
            else:
                out += struct.pack("<iII", rid, 0, 0)
        if self.fmt2d == 0x01:
            out += b"\0" * 0x20
        data_start = len(out)
        if self.flag01_intdata:
            struct.pack_into("<I", out, ds_pos, data_start)
        elif self.long_offsets:
            struct.pack_into("<q", out, ds_pos, data_start)
        else:
            struct.pack_into("<H", out, 4, data_start)
        for i, (rid, data, _n) in enumerate(self.rows):
            doff = len(out)
            out += data
            if self.long_offsets:
                struct.pack_into("<q", out, row_hdr_pos[i] + 8, doff)
            else:
                struct.pack_into("<I", out, row_hdr_pos[i] + 4, doff)
        struct.pack_into("<I", out, 0, len(out))
        if self.offset_param_type:
            struct.pack_into("<q", out, pto_pos, len(out))
            out += self.param_type.encode("ascii") + b"\0"
        # Row names: identical strings share one entry (Smithbox/SoulsFormatsNEXT behaviour),
        # written in order of first appearance, followed by a 2-byte terminator.
        seen = {}
        for i, (_rid, _d, name) in enumerate(self.rows):
            noff = 0
            if name is not None:
                if name in seen:
                    noff = seen[name]
                else:
                    noff = seen[name] = len(out)
                    out += (name.encode("utf-16-le") + b"\0\0") if (self.fmt2e & 0x01) else (name.encode("shift_jis") + b"\0")
            if self.long_offsets:
                struct.pack_into("<q", out, row_hdr_pos[i] + 16, noff)
            else:
                struct.pack_into("<I", out, row_hdr_pos[i] + 8, noff)
        out += b"\0\0"
        return bytes(out)


# --------------------------------------------------------------------------- regulation I/O


def read_regulation(path):
    enc = open(path, "rb").read()
    dcx = aes_decrypt(enc)
    raw, level = dcx_unwrap(dcx)
    return Bnd4.parse(raw), level, raw


def write_regulation(path, bnd: Bnd4, level: int):
    raw = bnd.write()
    open(path, "wb").write(aes_encrypt(dcx_wrap(raw, level)))
    return raw


def short_name(n: str) -> str:
    return n.replace("\\", "/").split("/")[-1]


# --------------------------------------------------------------------------- commands


def cmd_info(path):
    bnd, level, raw = read_regulation(path)
    print(f"{path}\n  BND4 version={bnd.version} files={len(bnd.files)} format=0x{bnd.format:02x} extended=0x{bnd.extended:02x} unicode={bnd.unicode} zstd_level={level} raw={len(raw)} bytes")
    total = 0
    for f in bnd.files:
        p = Param.parse(f.data)
        total += len(p.rows)
        print(f"  {short_name(f.name):40} id={f.id:4} type={p.param_type:34} rows={len(p.rows):6} rowsize={p.row_size:5} fmt2d=0x{p.fmt2d:02x} fmt2e=0x{p.fmt2e:02x} defver={p.def_data_ver} unk06={p.unk06}")
    print(f"  total rows: {total}")


def cmd_roundtrip(path):
    bnd, level, raw = read_regulation(path)
    bad = 0
    for f in bnd.files:
        p = Param.parse(f.data)
        w = p.write()
        if w != f.data:
            bad += 1
            # find first diff
            i = next((k for k in range(min(len(w), len(f.data))) if w[k] != f.data[k]), min(len(w), len(f.data)))
            print(f"  PARAM MISMATCH {short_name(f.name)}: len {len(f.data)} -> {len(w)}, first diff @0x{i:x}")
    print(f"params: {len(bnd.files) - bad}/{len(bnd.files)} round-trip byte-identical")
    w = bnd.write()
    if w == raw:
        print("BND4: round-trip byte-identical")
    else:
        i = next((k for k in range(min(len(w), len(raw))) if w[k] != raw[k]), min(len(w), len(raw)))
        print(f"BND4 MISMATCH: len {len(raw)} -> {len(w)}, first diff @0x{i:x}")
        bad += 1
    # AES/DCX layer: decrypt(encrypt(x)) must equal x
    back, _ = dcx_unwrap(aes_decrypt(aes_encrypt(dcx_wrap(raw, level)))[: len(dcx_wrap(raw, level))])
    print("DCX/AES: round-trip OK" if back == raw else "DCX/AES MISMATCH")
    return bad == 0 and back == raw


# EquipParamProtector 1.17 paramdef change: `dummy8 pad404[14]` became 32 x u8:1 bitflags
# (unk404_a_1..unk404_d_8) followed by `dummy8 pad408[10]`. Row size unchanged (416 bytes).
# Byte range [0x192, 0x1A0) computed from Smithbox's Defs/EquipParamProtector.xml
# (bitfields packed by unit size; both the 1.16.1 and 1.17.0 layouts total 416 bytes).
FIELD_COPIES = {
    "EQUIP_PARAM_PROTECTOR_ST": [(0x192, 0x1A0)],
}


def cmd_upgrade(mod_path, old_vanilla_path, new_vanilla_path, out_path, report_path=None):
    """Three-way, row-level merge (the same policy as Smithbox/DSMapStudio's param upgrader):

      row only in NEW vanilla                      -> added to the mod (new game content)
      row in OLD vanilla but not in NEW vanilla:
          mod row identical to OLD vanilla         -> removed (game removed it, mod never touched it)
          mod row differs                          -> kept (mod owns it), noted in report
      row in both vanillas:
          mod row identical to OLD vanilla         -> replaced with NEW vanilla row (take the 1.17 balance change)
          mod row differs and vanilla unchanged    -> kept (mod change)
          mod row differs and vanilla changed too  -> kept (mod wins), listed as a CONFLICT for manual review
      row only in the mod                          -> kept
      plus per-param FIELD_COPIES for paramdef layout changes, applied to rows present in NEW vanilla.
    """
    mod, level, _ = read_regulation(mod_path)
    old, _, _ = read_regulation(old_vanilla_path)
    new, _, _ = read_regulation(new_vanilla_path)
    print(f"mod:         version={mod.version} files={len(mod.files)}")
    print(f"old vanilla: version={old.version} files={len(old.files)}")
    print(f"new vanilla: version={new.version} files={len(new.files)}")
    if mod.version != old.version:
        print(f"  WARNING: mod regulation version {mod.version} != old vanilla {old.version}; the 3-way base may not match")
    old_by = {short_name(f.name).lower(): f for f in old.files}
    new_by = {short_name(f.name).lower(): f for f in new.files}
    report = {"mod_version": mod.version, "old_vanilla": old.version, "new_vanilla": new.version, "params": {}, "warnings": [], "conflicts": {}}
    tot = {"added": 0, "removed": 0, "updated": 0, "kept_mod": 0, "conflicts": 0, "field_copies": 0}
    for f in mod.files:
        key = short_name(f.name).lower()
        nf, of = new_by.get(key), old_by.get(key)
        e = {"added": 0, "removed": 0, "updated": 0, "kept_removed": 0, "conflicts": 0, "field_copies": 0, "header_updates": []}
        report["params"][key] = e
        if nf is None:
            report["warnings"].append(f"{key}: not present in new vanilla; left untouched")
            continue
        mp, np_ = Param.parse(f.data), Param.parse(nf.data)
        op = Param.parse(of.data) if of is not None else None
        if mp.rows and np_.rows and mp.row_size != np_.row_size:
            report["warnings"].append(f"{key}: ROW SIZE DIFFERS mod={mp.row_size} new={np_.row_size}; left untouched - needs a real paramdef migration")
            continue
        for attr in ("unk06", "def_data_ver", "def_fmt_ver", "fmt2d", "fmt2e"):
            if getattr(mp, attr) != getattr(np_, attr):
                e["header_updates"].append(f"{attr}: {getattr(mp, attr)} -> {getattr(np_, attr)}")
                setattr(mp, attr, getattr(np_, attr))
        old_rows = {r[0]: r[1] for r in op.rows} if op else {}
        new_rows = {r[0]: (r[1], r[2]) for r in np_.rows}
        merged = []
        conflicts = []
        for rid, data, name in mp.rows:
            o = old_rows.get(rid)
            n = new_rows.get(rid)
            if o is not None and n is None:
                if data == o:
                    e["removed"] += 1          # vanilla removed it, mod never changed it
                    continue
                e["kept_removed"] += 1
                merged.append([rid, data, name])
            elif o is not None and n is not None:
                if data == o:
                    if n[0] != o:
                        e["updated"] += 1      # take new vanilla version of an untouched row
                    merged.append([rid, n[0], name])
                else:
                    if n[0] != o:
                        e["conflicts"] += 1; conflicts.append(rid)
                    merged.append([rid, data, name])
            else:
                merged.append([rid, data, name])  # mod-only row (or row absent from old vanilla)
        # New vanilla rows: keep the mod's existing row order untouched (several Convergence params, and
        # even one vanilla param, are not id-sorted, and the game accepts that) and insert each new row
        # before the first existing row with a larger id, so id-sorted params stay sorted.
        have = {r[0] for r in merged}
        new_rows_to_add = [[rid, data, name] for rid, data, name in np_.rows if rid not in have and rid not in old_rows]
        # (rows that existed in old vanilla but are absent from the mod were deleted on purpose -> stay absent)
        for row in sorted(new_rows_to_add, key=lambda r: r[0]):
            idx = next((i for i, r in enumerate(merged) if r[0] > row[0]), len(merged))
            merged.insert(idx, row); e["added"] += 1
        for lo, hi in FIELD_COPIES.get(np_.param_type, []):
            for r in merged:
                n = new_rows.get(r[0])
                if n is not None:
                    upd = r[1][:lo] + n[0][lo:hi] + r[1][hi:]
                    if upd != r[1]:
                        r[1] = upd; e["field_copies"] += 1
        mp.rows = merged
        f.data = mp.write()
        if conflicts:
            report["conflicts"][key] = conflicts
        for k in ("added", "removed", "updated", "conflicts", "field_copies"):
            tot[k] += e[k]
        tot["kept_mod"] += e["kept_removed"]
        if any(e[k] for k in ("added", "removed", "updated", "conflicts", "field_copies")) or e["header_updates"]:
            print(f"  {key:38} +{e['added']:4} -{e['removed']:3} upd={e['updated']:4} conflicts={e['conflicts']:3} fieldcp={e['field_copies']:4} {'; '.join(e['header_updates'])}")
    mod_names = {short_name(f.name).lower() for f in mod.files}
    for key, nf in new_by.items():
        if key not in mod_names:
            report["warnings"].append(f"{key}: new param file in vanilla {new.version}, not in mod - added verbatim")
            mod.files.append(BndFile(nf.flags, nf.id, nf.name, nf.data))
    mod.version = new.version
    raw = write_regulation(out_path, mod, level)
    report["totals"] = tot
    report["output"] = {"path": out_path, "bnd_bytes": len(raw), "file_bytes": os.path.getsize(out_path), "version": mod.version}
    print(f"\ntotals: {tot}\nBND4 version set to {mod.version}; wrote {out_path} ({os.path.getsize(out_path)} bytes)")
    for w in report["warnings"]:
        print("  WARNING:", w)
    if report_path:
        json.dump(report, open(report_path, "w"), indent=2)
        print(f"report: {report_path}")
    chk, _, _ = read_regulation(out_path)
    assert chk.version == new.version and len(chk.files) == len(mod.files)
    for f in chk.files:
        Param.parse(f.data)
    print("verify: output re-read OK, all params parse")
    return report


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("info", "roundtrip", "upgrade"):
        print(__doc__); sys.exit(2)
    if a[0] == "info":
        cmd_info(a[1])
    elif a[0] == "roundtrip":
        sys.exit(0 if cmd_roundtrip(a[1]) else 1)
    else:
        rep = None
        if "--report" in a:
            rep = a[a.index("--report") + 1]
        cmd_upgrade(a[1], a[2], a[3], a[4], rep)
