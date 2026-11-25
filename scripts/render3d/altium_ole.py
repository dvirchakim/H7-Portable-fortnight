"""Read components, nets and pads of an Altium PcbDoc (an OLE compound file) with the standard library only:
no Altium, no KiCad, no windows.  Record layouts follow KiCad's Altium importer (altium_parser_pcb.cpp).

  python -I altium_pads.py PCB.PcbDoc out.json
"""
import os
import sys
import json
import struct

END = 0xFFFFFFFA            # sector ids at or above this end a chain
U = 2.54e-6                 # Altium internal unit (0.1 micro-inch) in mm


def cfb(path):
    data = open(path, 'rb').read()
    if data[:8] != bytes.fromhex('D0CF11E0A1B11AE1'):
        raise SystemExit('not an OLE compound file')
    major, = struct.unpack_from('<H', data, 0x1A)
    ssz = 1 << struct.unpack_from('<H', data, 0x1E)[0]
    mssz = 1 << struct.unpack_from('<H', data, 0x20)[0]
    nfat, dir_start = struct.unpack_from('<II', data, 0x2C)
    cutoff, = struct.unpack_from('<I', data, 0x38)
    mf_start, _n_mf, difat_start, n_difat = struct.unpack_from('<IIII', data, 0x3C)
    difat = list(struct.unpack_from('<109I', data, 0x4C))
    per = ssz // 4

    def sec(n):
        return data[(n + 1) * ssz:(n + 2) * ssz]
    s = difat_start
    for _ in range(n_difat):
        d = struct.unpack('<%dI' % per, sec(s))
        difat += d[:-1]
        s = d[-1]
    fat = []
    for f in difat[:nfat]:
        fat += struct.unpack('<%dI' % per, sec(f))

    def chain(start, table):
        out, seen = [], set()
        while start < END:
            if start in seen:
                raise SystemExit('loop in sector chain')
            seen.add(start)
            out.append(start)
            start = table[start]
        return out

    def big(start):
        return b''.join(sec(n) for n in chain(start, fat))
    dirdata = big(dir_start)
    ents = []
    for i in range(len(dirdata) // 128):
        e = dirdata[i * 128:(i + 1) * 128]
        nlen, = struct.unpack_from('<H', e, 0x40)
        left, right, child = struct.unpack_from('<III', e, 0x44)
        start, = struct.unpack_from('<I', e, 0x74)
        size, = struct.unpack_from('<Q', e, 0x78)
        if major == 3:
            size &= 0xFFFFFFFF
        ents.append(dict(name=e[:max(nlen - 2, 0)].decode('utf-16-le', 'replace'), type=e[0x42],
                         left=left, right=right, child=child, start=start, size=size))
    mini = big(ents[0]['start'])
    mfat = []
    for n in chain(mf_start, fat):
        mfat += struct.unpack('<%dI' % per, sec(n))
    paths = {}

    def walk(i, prefix, depth=0):
        stack = [i]
        while stack:
            i = stack.pop()
            if i >= len(ents) or depth > 8:
                continue
            e = ents[i]
            stack += [e['left'], e['right']]
            if e['type'] == 2:
                paths[prefix + e['name']] = e
            elif e['type'] == 1:
                walk(e['child'], prefix + e['name'] + '/', depth + 1)
    walk(ents[0]['child'], '')

    def get(p):
        e = paths[p]
        if e['size'] < cutoff:
            return b''.join(mini[n * mssz:(n + 1) * mssz] for n in chain(e['start'], mfat))[:e['size']]
        return big(e['start'])[:e['size']]
    return paths, get


def props(buf):
    out, i = [], 0
    while len(buf) - i >= 4:
        n, = struct.unpack_from('<I', buf, i)
        i += 4
        n &= 0x00FFFFFF
        txt = buf[i:i + n].split(b'\0')[0].decode('latin-1')
        i += n
        d = {}
        for kv in txt.split('|'):
            if '=' in kv:
                k, v = kv.split('=', 1)
                d[k.upper()] = v
        out.append(d)
    return out


