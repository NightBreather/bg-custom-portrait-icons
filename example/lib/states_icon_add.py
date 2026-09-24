#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
states_icon_add.py
==================

Add custom *portrait icon* frames to an Infinity Engine ``STATES.BAM``.

Background
----------
In the Beamdog Enhanced Editions a "portrait icon" (the small status icon shown
next to a character portrait) is requested through opcode ``142`` with
``parameter2 = N``.  The engine resolves ``N`` like this:

    N = 0 .. 190   ->  STATES.BAM, sequence (N + 65)
    N >= 191       ->  the BAM stored in STATDESC.2DA, column 3 ("BAM_FILE")

The **character-record screen** ("Affects" tab) always uses the STATES.BAM path:
for every active effect it takes the icon index and draws STATES.BAM sequence
``index + 65``.  If STATDESC.2DA holds a BAM in column 3 for that index the record
screen tries that BAM instead and, when it cannot render it there, falls back to
a generic icon (Haste).  That is why adding only a STATDESC BAM makes the icon
show up on the sidebar but *not* in the record.

Working recipe
--------------
1. Choose an **unused** icon index ``N`` in the range ``0 .. 190``.  In BG:EE the
   rows ``160 .. 187`` of STATDESC.2DA are unused (``-1 ****``), so they are safe.
2. Put your artwork **inside STATES.BAM** at sequence ``N + 65`` (this script does
   exactly that: it appends 13x13 frames and repoints the chosen sequences).
3. In STATDESC.2DA set row ``N``: column 2 = your text strref, column 3 = ``****``
   (it **must stay empty**).
4. Point the effect at the icon: opcode ``142``, ``parameter2 = N``.

The icon is then drawn from STATES.BAM both on the sidebar and in the record.

Usage
-----
    python3 states_icon_add.py <vanilla_states.bam> <out_states.bam> N:png[:RRGGBB] ...

Example
-------
    weidu --biff-get states.bam
    python3 states_icon_add.py states.bam override/states.bam \
            179:icons/shield.png:3aa0ff  180:icons/spider.png:b400dc

Notes
-----
* The PNGs must be 8-bit grayscale (``colortype 0``).  They are downscaled to
  13x13; pixels darker than the threshold become transparent.
* Only the ``states.bam`` file produced here is needed at runtime (plus the
  STATDESC.2DA rows and the opcode 142 assignments described above).
"""

import os
import struct
import sys
import zlib

# --------------------------------------------------------------------------- #
# minimal PNG decoder (8-bit grayscale, non-interlaced or Adam7)
# --------------------------------------------------------------------------- #

def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def load_png_gray(path):
    """Return (width, height, bytearray) for an 8-bit grayscale PNG."""
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("%s: not a PNG file" % path)
    i = 8
    idat = b""
    w = h = bd = ct = inter = None
    while i < len(data):
        ln = struct.unpack(">I", data[i:i + 4])[0]
        typ = data[i + 4:i + 8]
        chunk = data[i + 8:i + 8 + ln]
        i += 12 + ln
        if typ == b"IHDR":
            w, h, bd, ct, _comp, _filt, inter = struct.unpack(">IIBBBBB", chunk)
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
    if bd != 8 or ct != 0:
        raise ValueError("%s: only 8-bit grayscale PNGs are supported "
                         "(bitdepth=%s colortype=%s)" % (path, bd, ct))
    raw = zlib.decompress(idat)
    out = bytearray(w * h)
    if inter == 0:
        pos = 0
        prev = bytearray(w)
        for y in range(h):
            f = raw[pos]
            pos += 1
            line = bytearray(raw[pos:pos + w])
            pos += w
            if f == 1:
                for x in range(1, w):
                    line[x] = (line[x] + line[x - 1]) & 255
            elif f == 2:
                for x in range(w):
                    line[x] = (line[x] + prev[x]) & 255
            elif f == 3:
                for x in range(w):
                    a = line[x - 1] if x >= 1 else 0
                    line[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
            elif f == 4:
                for x in range(w):
                    a = line[x - 1] if x >= 1 else 0
                    c = prev[x - 1] if x >= 1 else 0
                    line[x] = (line[x] + _paeth(a, prev[x], c)) & 255
            out[y * w:(y + 1) * w] = line
            prev = line
    else:
        passes = [(0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
                  (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2)]
        pos = 0
        for (xo, yo, xs, ys) in passes:
            pw = (w - xo + xs - 1) // xs
            ph = (h - yo + ys - 1) // ys
            prev = bytearray(pw)
            for y in range(ph):
                f = raw[pos]
                pos += 1
                line = bytearray(raw[pos:pos + pw])
                pos += pw
                if f == 1:
                    for x in range(1, pw):
                        line[x] = (line[x] + line[x - 1]) & 255
                elif f == 2:
                    for x in range(pw):
                        line[x] = (line[x] + prev[x]) & 255
                elif f == 3:
                    for x in range(pw):
                        a = line[x - 1] if x >= 1 else 0
                        line[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
                elif f == 4:
                    for x in range(pw):
                        a = line[x - 1] if x >= 1 else 0
                        c = prev[x - 1] if x >= 1 else 0
                        line[x] = (line[x] + _paeth(a, prev[x], c)) & 255
                for x in range(pw):
                    out[(yo + y * ys) * w + (xo + x * xs)] = line[x]
                prev = line
    return w, h, out


def downscale(w, h, px, ow, oh):
    """Box-filter downscale of a grayscale image."""
    out = bytearray(ow * oh)
    for oy in range(oh):
        for ox in range(ow):
            x0 = ox * w // ow
            x1 = max(x0 + 1, (ox + 1) * w // ow)
            y0 = oy * h // oh
            y1 = max(y0 + 1, (oy + 1) * h // oh)
            s = n = 0
            for y in range(y0, y1):
                row = y * w
                for x in range(x0, x1):
                    s += px[row + x]
                    n += 1
            out[oy * ow + ox] = s // max(1, n)
    return out


# --------------------------------------------------------------------------- #
# BAM V1 reader / writer
# --------------------------------------------------------------------------- #

class Bam:
    def __init__(self, data):
        self.raw = data
        self.frame_cnt = struct.unpack_from("<H", data, 0x08)[0]
        self.cycle_cnt = data[0x0A]
        self.comp = data[0x0B]
        self.frame_off = struct.unpack_from("<I", data, 0x0C)[0]
        self.pal_off = struct.unpack_from("<I", data, 0x10)[0]
        self.lut_off = struct.unpack_from("<I", data, 0x14)[0]

        self.frames = []
        for i in range(self.frame_cnt):
            w, h, x, y, off = struct.unpack_from(
                "<HHHHI", data, self.frame_off + i * 12)
            self.frames.append({"w": w, "h": h, "x": x, "y": y,
                                "off": off & 0x7FFFFFFF,
                                "unc": bool(off >> 31)})

        cyc_off = self.frame_off + self.frame_cnt * 12
        self.cycles = []
        for i in range(self.cycle_cnt):
            c, l = struct.unpack_from("<HH", data, cyc_off + i * 4)
            self.cycles.append({"cnt": c, "lut": l})

        self.pal = [tuple(data[self.pal_off + i * 4:self.pal_off + i * 4 + 4])
                    for i in range(256)]

        max_lut = max((c["lut"] + c["cnt"] for c in self.cycles), default=0)
        self.lut = [struct.unpack_from("<H", data, self.lut_off + i * 2)[0]
                    for i in range(max_lut)]

    def used_palette(self):
        used = set()
        for f in self.frames:
            o = f["off"]
            n = f["w"] * f["h"]
            if f["unc"]:
                used.update(self.raw[o:o + n])
                continue
            got = 0
            while got < n:
                p = self.raw[o]
                if p == self.comp:
                    o += 1
                    got += self.raw[o] + 1
                else:
                    got += 1
                o += 1
            used.add(self.comp)
        return used

    @staticmethod
    def _rle(data, comp):
        out = bytearray()
        run = 0
        for p in data:
            if p == comp:
                run += 1
                if run == 256:
                    out += bytes([comp, 255])
                    run = 0
            else:
                if run:
                    out += bytes([comp, run - 1])
                    run = 0
                out.append(p)
        if run:
            out += bytes([comp, run - 1])
        return bytes(out)

    def add_frame(self, pixels, slot, w=13, h=13, x=0, y=0):
        """Append an uncompressed 13x13 frame; return its new frame index."""
        self.frames.append({"w": w, "h": h, "x": x, "y": y,
                            "off": None, "unc": False, "data": bytes(pixels)})
        return len(self.frames) - 1

    def point_sequence(self, seq, frame_index):
        """Make sequence ``seq`` show ``frame_index`` (single frame)."""
        self.lut.append(frame_index)
        self.cycles[seq] = {"cnt": 1, "lut": len(self.lut) - 1}

    def build(self):
        frame_cnt = len(self.frames)
        cycle_cnt = len(self.cycles)
        frame_off = 0x18
        cyc_off = frame_off + frame_cnt * 12
        pal_off = cyc_off + cycle_cnt * 4
        lut_off = pal_off + 256 * 4
        data_off = lut_off + len(self.lut) * 2

        blob = bytearray()
        offsets = []
        for f in self.frames:
            if f.get("data") is not None:
                enc = self._rle(f["data"], self.comp)
            elif f["unc"]:
                enc = self.raw[f["off"]:f["off"] + f["w"] * f["h"]]
            else:
                o, n, start = f["off"], f["w"] * f["h"], f["off"]
                got = 0
                while got < n:
                    p = self.raw[o]
                    if p == self.comp:
                        o += 1
                        got += self.raw[o] + 1
                    else:
                        got += 1
                    o += 1
                enc = self.raw[start:o]
            offsets.append(data_off + len(blob))
            blob += enc

        out = bytearray(b"BAM " + b"V1  ")
        out += struct.pack("<H", frame_cnt)
        out += struct.pack("<B", cycle_cnt)
        out += struct.pack("<B", self.comp)
        out += struct.pack("<I", frame_off)
        out += struct.pack("<I", pal_off)
        out += struct.pack("<I", lut_off)
        for i, f in enumerate(self.frames):
            out += struct.pack("<HHHHI", f["w"], f["h"], f["x"], f["y"], offsets[i])
        for c in self.cycles:
            out += struct.pack("<HH", c["cnt"], c["lut"])
        for p in self.pal:
            out += bytes(p)
        for l in self.lut:
            out += struct.pack("<H", l)
        out += blob
        return out


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

DEFAULT_TINT = (0x3A, 0xA0, 0xFF)  # blue


def parse_spec(spec):
    """Parse ``N:path`` or ``N:path:RRGGBB``."""
    parts = spec.split(":")
    if len(parts) < 2:
        raise ValueError("bad spec %r (expected N:png[:RRGGBB])" % spec)
    index = int(parts[0])
    path = parts[1]
    tint = DEFAULT_TINT
    if len(parts) >= 3:
        h = parts[2].lstrip("#")
        tint = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return index, path, tint


def main(argv):
    if len(argv) < 4:
        sys.stderr.write(__doc__)
        return 2

    src, dst = argv[1], argv[2]
    specs = [parse_spec(s) for s in argv[3:]]

    bam = Bam(open(src, "rb").read())
    free = [i for i in range(1, 256) if i not in bam.used_palette()]
    if len(free) < len(specs):
        raise SystemExit("not enough free palette slots (%d needed, %d free)"
                         % (len(specs), len(free)))

    for k, (index, path, tint) in enumerate(specs):
        seq = index + 65
        if seq >= bam.cycle_cnt:
            raise SystemExit("index %d -> sequence %d is out of range (max %d)"
                             % (index, seq, bam.cycle_cnt - 1))
        slot = free[k]
        bam.pal[slot] = (tint[2], tint[1], tint[0], 255)  # stored B,G,R,A
        w, h, px = load_png_gray(path)
        g = downscale(w, h, px, 13, 13)
        pixels = bytes(slot if v >= 40 else 0 for v in g)
        fi = bam.add_frame(pixels, slot)
        bam.point_sequence(seq, fi)
        print("index %3d -> sequence %3d -> frame %3d  (%s)"
              % (index, seq, fi, os.path.basename(path)))

    open(dst, "wb").write(bam.build())
    print("written %s (%d bytes)" % (dst, os.path.getsize(dst)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
