"""Minimal KiCad .kicad_sym reader: S-expression parser + symbol/pin extraction (KiCad 6-10 format)."""
import os, re

LIBDIR = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"


def tokenize(s):
    for m in re.finditer(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', s):
        yield m.group(0)


def parse(s):
    stack, cur = [], []
    for tok in tokenize(s):
        if tok == "(":
            stack.append(cur); cur = []
        elif tok == ")":
            done = cur; cur = stack.pop(); cur.append(done)
        else:
            cur.append(tok)
    return cur


def dump(x):
    if isinstance(x, list):
        return "(" + " ".join(dump(i) for i in x) + ")"
    return x


_cache = {}


def load_lib(lib):
    if lib not in _cache:
        tree = parse(open(os.path.join(LIBDIR, lib + ".kicad_sym")).read())[0]
        _cache[lib] = {n[1].strip('"'): n for n in tree if isinstance(n, list) and n and n[0] == "symbol"}
    return _cache[lib]


def get_symbol(lib_id):
    """Return the symbol s-expr with 'extends' resolved, renamed to the full lib_id."""
    lib, name = lib_id.split(":")
    syms = load_lib(lib)
    sym = syms[name]
    ext = [n for n in sym if isinstance(n, list) and n and n[0] == "extends"]
    if ext:
        parent = syms[ext[0][1].strip('"')]
        merged = [x for x in parent if not (isinstance(x, list) and x and x[0] == "property")]
        props = [x for x in sym if isinstance(x, list) and x and x[0] == "property"]
        # keep parent's graphics/pins (sub-symbols renamed), child's properties
        body = []
        for x in merged[2:]:
            if isinstance(x, list) and x and x[0] == "symbol":
                x = [x[0], '"' + x[1].strip('"').replace(parent[1].strip('"'), name) + '"'] + x[2:]
            body.append(x)
        sym = ["symbol", '"' + name + '"'] + props + body
    out = ["symbol", '"' + lib_id + '"'] + sym[2:]
    return out


def pins(sym):
    """List of (number, name, x, y, angle, type) for unit 1 + unit 0 pins."""
    res = []

    def walk(node, unit_ok):
        for x in node:
            if not isinstance(x, list) or not x:
                continue
            if x[0] == "symbol":
                nm = x[1].strip('"')
                m = re.search(r"_(\d+)_(\d+)$", nm)
                unit = int(m.group(1)) if m else 0
                walk(x, unit in (0, 1))
            elif x[0] == "pin" and unit_ok:
                at = next(i for i in x if isinstance(i, list) and i[0] == "at")
                name = next(i for i in x if isinstance(i, list) and i[0] == "name")[1].strip('"')
                num = next(i for i in x if isinstance(i, list) and i[0] == "number")[1].strip('"')
                res.append((num, name, float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0, x[1]))
    walk(sym, True)
    return res
