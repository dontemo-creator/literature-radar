# -*- coding: utf-8 -*-
"""A small QR encoder (byte mode, error-correction level M, versions 1-10).

Written from the spec with no dependencies so the app stays standard-library
only.  Its output is verified by decoding real images with Apple's Vision
framework -- see ``tools/qr_verify.swift`` and ``tests/test_qrcode.py``; an
encoder that produces something a phone cannot scan is worse than no encoder.

Versions 1-10 hold up to 213 bytes, far more than any ``http://host:port/``.
"""
from __future__ import annotations

import struct
import zlib

# --------------------------------------------------------------- GF(256) ----
_EXP = [0] * 512
_LOG = [0] * 256


def _init_tables() -> None:
    x = 1
    for i in range(255):
        _EXP[i] = x
        _LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D              # primitive polynomial for QR
    for i in range(255, 512):
        _EXP[i] = _EXP[i - 255]


_init_tables()


def _mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _rs_generator(n: int) -> list[int]:
    g = [1]
    for i in range(n):
        g = _poly_mul(g, [1, _EXP[i]])
    return g


def _poly_mul(a: list[int], b: list[int]) -> list[int]:
    out = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        if ai == 0:
            continue
        for j, bj in enumerate(b):
            out[i + j] ^= _mul(ai, bj)
    return out


def _rs_ecc(data: list[int], n: int) -> list[int]:
    gen = _rs_generator(n)
    rem = list(data) + [0] * n
    for i in range(len(data)):
        coef = rem[i]
        if coef == 0:
            continue
        for j, gj in enumerate(gen):
            rem[i + j] ^= _mul(gj, coef)
    return rem[len(data):]


# ------------------------------------------------------- version tables -----
# level M: (ecc codewords per block, [(block count, data codewords), ...])
_EC_M: dict[int, tuple[int, list[tuple[int, int]]]] = {
    1: (10, [(1, 16)]),
    2: (16, [(1, 28)]),
    3: (26, [(1, 44)]),
    4: (18, [(2, 32)]),
    5: (24, [(2, 43)]),
    6: (16, [(4, 27)]),
    7: (18, [(4, 31)]),
    8: (22, [(2, 38), (2, 39)]),
    9: (22, [(3, 36), (2, 37)]),
    10: (26, [(4, 43), (1, 44)]),
}
_ALIGN: dict[int, list[int]] = {
    1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34],
    7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50],
}


def _capacity(version: int) -> int:
    """Byte-mode payload capacity, in bytes."""
    _, groups = _EC_M[version]
    data_cw = sum(cnt * dc for cnt, dc in groups)
    count_bits = 16 if version >= 10 else 8
    return (data_cw * 8 - 4 - count_bits) // 8


class QRError(ValueError):
    pass


# ------------------------------------------------------------- encoding ----
def _bitstream(payload: bytes, version: int) -> list[int]:
    bits: list[int] = []

    def put(value: int, length: int) -> None:
        for i in range(length - 1, -1, -1):
            bits.append((value >> i) & 1)

    put(0b0100, 4)                                  # byte mode
    put(len(payload), 16 if version >= 10 else 8)
    for byte in payload:
        put(byte, 8)

    _, groups = _EC_M[version]
    total_data_bits = sum(cnt * dc for cnt, dc in groups) * 8
    put(0, min(4, total_data_bits - len(bits)))     # terminator
    while len(bits) % 8:
        bits.append(0)
    pad = (0xEC, 0x11)
    i = 0
    while len(bits) < total_data_bits:
        put(pad[i % 2], 8)
        i += 1
    return bits


def _codewords(payload: bytes, version: int) -> list[int]:
    bits = _bitstream(payload, version)
    data = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]

    ecc_len, groups = _EC_M[version]
    blocks: list[list[int]] = []
    eccs: list[list[int]] = []
    pos = 0
    for count, dc in groups:
        for _ in range(count):
            chunk = data[pos:pos + dc]
            pos += dc
            blocks.append(chunk)
            eccs.append(_rs_ecc(chunk, ecc_len))

    out: list[int] = []
    for i in range(max(len(b) for b in blocks)):
        for b in blocks:
            if i < len(b):
                out.append(b[i])
    for i in range(ecc_len):
        for e in eccs:
            out.append(e[i])
    return out


# -------------------------------------------------------------- matrix -----
def _new_matrix(size: int):
    return [[None] * size for _ in range(size)]


def _place_function_patterns(m, version: int) -> None:
    size = len(m)

    def finder(r0: int, c0: int) -> None:
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = r0 + dr, c0 + dc
                if not (0 <= r < size and 0 <= c < size):
                    continue
                inner = 2 <= dr <= 4 and 2 <= dc <= 4
                ring = dr in (0, 6) or dc in (0, 6)
                m[r][c] = 1 if (inner or ring) and 0 <= dr <= 6 and 0 <= dc <= 6 else 0

    finder(0, 0)
    finder(0, size - 7)
    finder(size - 7, 0)

    for i in range(size):
        if m[6][i] is None:
            m[6][i] = 1 if i % 2 == 0 else 0
        if m[i][6] is None:
            m[i][6] = 1 if i % 2 == 0 else 0

    # Alignment patterns sit at every coordinate pair except the three that
    # would collide with the finders.  Testing "is this cell already taken?"
    # instead looks right for versions 2-6 but silently drops the patterns at
    # (first, middle) and (middle, first) from version 7 on, because the timing
    # pattern got there first -- and those versions then fail to decode.
    coords = _ALIGN[version]
    if coords:
        first, last = coords[0], coords[-1]
        skip = {(first, first), (first, last), (last, first)}
        for r in coords:
            for c in coords:
                if (r, c) in skip:
                    continue
                for dr in range(-2, 3):
                    for dc in range(-2, 3):
                        ring = max(abs(dr), abs(dc))
                        m[r + dr][c + dc] = 1 if ring != 1 else 0

    m[size - 8][8] = 1                     # dark module

    for i in range(9):                     # reserve format areas
        if m[8][i] is None:
            m[8][i] = 0
        if m[i][8] is None:
            m[i][8] = 0
    for i in range(8):
        if m[8][size - 1 - i] is None:
            m[8][size - 1 - i] = 0
        if m[size - 1 - i][8] is None:
            m[size - 1 - i][8] = 0

    if version >= 7:                       # reserve version areas
        for i in range(6):
            for j in range(3):
                m[size - 11 + j][i] = 0
                m[i][size - 11 + j] = 0


def _place_data(m, codewords: list[int]) -> list[tuple[int, int]]:
    size = len(m)
    bits = []
    for cw in codewords:
        for i in range(7, -1, -1):
            bits.append((cw >> i) & 1)
    idx = 0
    written: list[tuple[int, int]] = []
    col = size - 1
    upward = True
    while col > 0:
        if col == 6:
            col -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for row in rows:
            for c in (col, col - 1):
                if m[row][c] is not None:
                    continue
                m[row][c] = bits[idx] if idx < len(bits) else 0
                written.append((row, c))
                idx += 1
        upward = not upward
        col -= 2
    return written


_MASKS = [
    lambda i, j: (i + j) % 2 == 0,
    lambda i, j: i % 2 == 0,
    lambda i, j: j % 3 == 0,
    lambda i, j: (i + j) % 3 == 0,
    lambda i, j: (i // 2 + j // 3) % 2 == 0,
    lambda i, j: (i * j) % 2 + (i * j) % 3 == 0,
    lambda i, j: ((i * j) % 2 + (i * j) % 3) % 2 == 0,
    lambda i, j: ((i + j) % 2 + (i * j) % 3) % 2 == 0,
]


def _penalty(m) -> int:
    size = len(m)
    score = 0

    lines = [[m[r][c] for c in range(size)] for r in range(size)]
    lines += [[m[r][c] for r in range(size)] for c in range(size)]
    for line in lines:
        run, prev = 0, None
        for v in line:
            if v == prev:
                run += 1
            else:
                if run >= 5:
                    score += 3 + (run - 5)
                run, prev = 1, v
        if run >= 5:
            score += 3 + (run - 5)

    for r in range(size - 1):
        for c in range(size - 1):
            if m[r][c] == m[r][c + 1] == m[r + 1][c] == m[r + 1][c + 1]:
                score += 3

    pattern = [1, 0, 1, 1, 1, 0, 1]
    for line in lines:
        for i in range(size - 6):
            if line[i:i + 7] != pattern:
                continue
            before = line[max(0, i - 4):i]
            after = line[i + 7:i + 11]
            if len(before) >= 4 and all(v == 0 for v in before[-4:]):
                score += 40
            if len(after) >= 4 and all(v == 0 for v in after[:4]):
                score += 40

    dark = sum(sum(row) for row in m)
    percent = dark * 100 / (size * size)
    score += 10 * (int(abs(percent - 50) / 5))
    return score


def _format_bits(mask: int) -> int:
    data = (0b00 << 3) | mask                 # level M == 0b00
    value = data << 10
    gen = 0b10100110111
    for i in range(4, -1, -1):
        if value & (1 << (i + 10)):
            value ^= gen << i
    return ((data << 10) | value) ^ 0b101010000010010


def _version_bits(version: int) -> int:
    value = version << 12
    gen = 0b1111100100101
    for i in range(5, -1, -1):
        if value & (1 << (i + 12)):
            value ^= gen << i
    return (version << 12) | value


def _apply_format(m, mask: int, version: int) -> None:
    size = len(m)
    fmt = _format_bits(mask)
    # Copy one runs *down column 8* for bits 0-5 and then *left along row 8*
    # for bits 9-14.  Getting these two axes the wrong way round produces a
    # mirror image that no decoder will read, so the order matters exactly.
    for i in range(15):
        bit = (fmt >> i) & 1
        if i < 6:
            m[i][8] = bit
        elif i == 6:
            m[7][8] = bit
        elif i == 7:
            m[8][8] = bit
        elif i == 8:
            m[8][7] = bit
        else:
            m[8][14 - i] = bit
    # Copy two: bits 0-7 along row 8 from the right edge, bits 8-14 down
    # column 8 from the bottom edge.
    for i in range(15):
        bit = (fmt >> i) & 1
        if i < 8:
            m[8][size - 1 - i] = bit
        else:
            m[size - 15 + i][8] = bit
    m[size - 8][8] = 1

    if version >= 7:
        vb = _version_bits(version)
        for i in range(18):
            bit = (vb >> i) & 1
            m[size - 11 + i % 3][i // 3] = bit
            m[i // 3][size - 11 + i % 3] = bit


def encode(text: str) -> list[list[int]]:
    """Return the QR matrix (1 = dark) for ``text``, without a quiet zone."""
    payload = text.encode("utf-8")
    version = next((v for v in sorted(_EC_M) if len(payload) <= _capacity(v)), 0)
    if not version:
        raise QRError("payload too long for versions 1-10 ({} bytes)".format(len(payload)))

    size = 17 + 4 * version
    base = _new_matrix(size)
    _place_function_patterns(base, version)
    data_cells = _place_data(base, _codewords(payload, version))

    best, best_score = None, None
    for mask in range(8):
        cand = [row[:] for row in base]
        for (r, c) in data_cells:
            if _MASKS[mask](r, c):
                cand[r][c] ^= 1
        _apply_format(cand, mask, version)
        score = _penalty(cand)
        if best_score is None or score < best_score:
            best, best_score = cand, score
    return [[int(v or 0) for v in row] for row in best]


# ------------------------------------------------------------- rendering ---
def to_ansi(matrix, quiet: int = 3) -> str:
    """Render for a terminal, using half blocks with explicit colours.

    Colours are set explicitly rather than relying on the terminal's own
    palette: an inverted QR is unreliable for phone cameras, and a dark
    terminal theme would invert it.
    """
    size = len(matrix)
    grid = [[0] * (size + 2 * quiet) for _ in range(quiet)]
    for row in matrix:
        grid.append([0] * quiet + list(row) + [0] * quiet)
    grid += [[0] * (size + 2 * quiet) for _ in range(quiet)]
    if len(grid) % 2:
        grid.append([0] * len(grid[0]))

    lines = []
    for r in range(0, len(grid), 2):
        parts = []
        for c in range(len(grid[0])):
            top, bottom = grid[r][c], grid[r + 1][c]
            fg = 30 if top else 97          # dark module -> black ink
            bg = 40 if bottom else 107
            parts.append("\033[{};{}m▀".format(fg, bg))
        lines.append("".join(parts) + "\033[0m")
    return "\n".join(lines)


def to_ascii(matrix, quiet: int = 3) -> str:
    """Colour-free fallback: two spaces per module, inverse video for dark."""
    size = len(matrix)
    rows = []
    blank = "  " * (size + 2 * quiet)
    for _ in range(quiet):
        rows.append(blank)
    for row in matrix:
        line = "  " * quiet
        for v in row:
            line += "██" if v else "  "
        rows.append(line + "  " * quiet)
    for _ in range(quiet):
        rows.append(blank)
    return "\n".join(rows)


def to_png(matrix, scale: int = 8, quiet: int = 4) -> bytes:
    """Minimal 1-bit-ish greyscale PNG, used by the verification test."""
    size = len(matrix)
    dim = (size + 2 * quiet) * scale
    rows = []
    for y in range(dim):
        my = y // scale - quiet
        line = bytearray([0])                     # filter type 0
        for x in range(dim):
            mx = x // scale - quiet
            dark = (0 <= my < size and 0 <= mx < size and matrix[my][mx])
            line.append(0 if dark else 255)
        rows.append(bytes(line))
    raw = b"".join(rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", dim, dim, 8, 0, 0, 0, 0)   # 8-bit greyscale
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def render(text: str, *, colour: bool = True, quiet: int = 3) -> str:
    m = encode(text)
    return to_ansi(m, quiet) if colour else to_ascii(m, quiet)
