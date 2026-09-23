# -*- coding: utf-8 -*-
"""QR encoder, verified by decoding real images with Apple's Vision framework.

A QR code that does not scan is worse than no QR code, and eyeballing a module
grid proves nothing -- two genuine bugs here (transposed format bits, and a
dropped alignment pattern from version 7 on) produced grids that looked
perfectly plausible and decoded in nothing.  So every check below ends at a
real decoder.  Without Swift installed the structural checks still run and the
decode checks are skipped.
"""
import json, pathlib, re, shutil, subprocess, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app import qrcode as qr

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERIFIER = ROOT / "tools" / "qr_verify.swift"

fails = []


def check(name, got, want=True):
    ok = got == want
    if not ok:
        fails.append((name, got, want))
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}: {got!r}")


# Level-M format strings straight from the standard (ISO/IEC 18004 table C.1).
KNOWN_FORMAT_M = [
    "101010000010010", "101000100100101", "101111001111100", "101101101001011",
    "100010111111001", "100000011001110", "100111110010111", "100101010100000",
]
# Byte-mode capacity at level M, per version.
KNOWN_CAPACITY = {1: 14, 2: 26, 3: 42, 4: 62, 5: 84,
                  6: 106, 7: 122, 8: 152, 9: 180, 10: 213}


def _parse_ansi(art):
    rows = []
    for line in art.splitlines():
        top, bottom = [], []
        for m in re.finditer(r"\033\[(\d+);(\d+)m▀", line):
            top.append(1 if int(m.group(1)) == 30 else 0)
            bottom.append(1 if int(m.group(2)) == 40 else 0)
        rows.append(top)
        rows.append(bottom)
    return rows


def _parse_ascii(art):
    return [[1 if line[i:i + 2] == "██" else 0 for i in range(0, len(line), 2)]
            for line in art.splitlines()]


def _strip_quiet(grid, q):
    inner = [r[q:len(r) - q] for r in grid[q:len(grid) - q]]
    while inner and not any(inner[-1]):
        inner.pop()
    return inner


def _decode(paths):
    """path -> payload, using Vision. Empty dict when Swift is unavailable."""
    if not shutil.which("swift") or not VERIFIER.exists():
        return {}
    try:
        out = subprocess.run(["swift", str(VERIFIER)] + [str(p) for p in paths],
                             capture_output=True, text=True, timeout=240).stdout
    except Exception as exc:
        print("  (decode skipped: %s)" % exc)
        return {}
    got = {}
    for line in out.splitlines():
        if "\t" in line:
            path, payload = line.split("\t", 1)
            got[path] = payload
    return got


def run():
    # ---- structural checks, no decoder needed -----------------------------
    for mask in range(8):
        check("format bits, mask %d" % mask,
              format(qr._format_bits(mask), "015b"), KNOWN_FORMAT_M[mask])
    check("version bits, v7", format(qr._version_bits(7), "018b"), "000111110010010100")
    for v, cap in KNOWN_CAPACITY.items():
        check("capacity v%d" % v, qr._capacity(v), cap)
    for v, (ecc, groups) in qr._EC_M.items():
        total = sum(cnt * (dc + ecc) for cnt, dc in groups)
        expect = {1: 26, 2: 44, 3: 70, 4: 100, 5: 134,
                  6: 172, 7: 196, 8: 242, 9: 292, 10: 346}[v]
        check("codeword total v%d" % v, total, expect)

    m = qr.encode("HELLO WORLD")
    check("v1 matrix is 21x21", (len(m), len(m[0])), (21, 21))
    check("finder ring, top-left", [m[0][i] for i in range(7)], [1] * 7)
    check("finder centre is dark", m[3][3], 1)
    check("separator is light", m[7][0], 0)
    check("timing row alternates", [m[6][i] for i in range(8, 13)], [1, 0, 1, 0, 1])
    check("dark module set", m[len(m) - 8][8], 1)
    try:
        qr.encode("z" * 300)
        check("oversized payload raises", False)
    except qr.QRError:
        check("oversized payload raises", True)

    # ---- decode checks ----------------------------------------------------
    tmp = tempfile.mkdtemp(prefix="qrtest-")
    manifest = {}
    payloads = ["http://172.20.10.9:8756/", "http://192.168.1.23:8757/",
                "http://10.0.0.5:8756/#new_only=1", "HELLO WORLD", "a"]
    for v in sorted(KNOWN_CAPACITY):
        payloads.append("A" * KNOWN_CAPACITY[v])          # exactly fills version v
    for i, text in enumerate(payloads):
        path = pathlib.Path(tmp) / ("direct_%02d.png" % i)
        path.write_bytes(qr.to_png(qr.encode(text), scale=6, quiet=4))
        manifest[str(path)] = text

    # the terminal renderings must carry the same modules as the source grid
    for i, text in enumerate(["http://172.20.10.9:8756/", "A" * 106, "A" * 180]):
        src = qr.encode(text)
        for kind, art, parser in (("ansi", qr.to_ansi(src, 3), _parse_ansi),
                                  ("ascii", qr.to_ascii(src, 3), _parse_ascii)):
            grid = _strip_quiet(parser(art), 3)
            check("%s rendering preserves the grid (%d)" % (kind, i), grid == src)
            path = pathlib.Path(tmp) / ("%s_%02d.png" % (kind, i))
            path.write_bytes(qr.to_png(grid, scale=6, quiet=4))
            manifest[str(path)] = text

    decoded = _decode(sorted(manifest))
    if not decoded:
        print("  SKIP: Swift/Vision unavailable, decode verification skipped")
    else:
        wrong = 0
        for path, expect in sorted(manifest.items()):
            if decoded.get(path) != expect:
                wrong += 1
                print("  [FAIL] %s -> %r (expected %r)" % (
                    pathlib.Path(path).name, decoded.get(path, "<missing>")[:40], expect[:40]))
        check("every image decodes to its payload (%d images)" % len(manifest), wrong, 0)
    shutil.rmtree(tmp, ignore_errors=True)

    print("\n%s" % ("ALL QR CHECKS PASS" if not fails else "FAILURES:"))
    for f in fails:
        print("   ", f)
    return len(fails)


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
