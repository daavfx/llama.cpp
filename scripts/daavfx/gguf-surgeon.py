#!/usr/bin/env python3
# gguf-surgeon: MoE expert surgery for lfm2_moe-family GGUFs.
# FOUNDRY.md F1 (amputate) and F2 (merge), plus inspect and roundtrip-test.
#
# Design notes:
# - Own GGUF v3 codec. Unmodified KV payloads are copied as raw byte spans,
#   so a no-op rewrite is byte-identical (proven by roundtrip-test).
# - Amputation is raw block surgery: expert slabs are contiguous in the
#   quantized byte stream, so no dequantization is needed. Zero dependencies.
# - Merge needs dequantization, which comes from the fork's gguf-py
#   (gguf.quants). Merged tensors are rewritten whole, to F16 or Q8_0.
#   REVIEW-2: group members are permutation-aligned to the group anchor
#   (SwiGLU inner neurons are arbitrarily permuted across experts) before
#   averaging; output is streamed per tensor via producer callables, and
#   the writer pads inter-tensor gaps to each declared offset.
# - Surgery always writes a NEW file. Input is never modified.

import argparse
import json
import mmap
import os
import struct
import sys

GGUF_MAGIC = b"GGUF"
GGUF_VERSION = 3
DEFAULT_ALIGN = 32

# value type id -> (struct fmt, size) ; 7=bool(1 byte), 13=bf16(raw 2 bytes)
VT_SCALAR = {
    0:  ("<B", 1), 1:  ("<b", 1),
    2:  ("<H", 2), 3:  ("<h", 2),
    4:  ("<I", 4), 5:  ("<i", 4),
    6:  ("<f", 4), 7:  ("<B", 1),
    10: ("<Q", 8), 11: ("<q", 8), 12: ("<d", 8), 13: ("<H", 2),
}
VT_STRING = 8
VT_ARRAY = 9

GGML_F16 = 1
GGML_Q8_0 = 8

EXP_TENSORS = ("ffn_gate_exps", "ffn_up_exps", "ffn_down_exps")
ROUTER_TENSOR = "ffn_gate_inp"
BIAS_TENSOR = "exp_probs_b"


def align_up(x, a):
    return (x + a - 1) // a * a


class KV:
    __slots__ = ("vtype", "name", "raw", "value")

    def __init__(self, vtype, name, raw, value):
        self.vtype = vtype
        self.name = name
        self.raw = raw          # bytes of the value payload, verbatim
        self.value = value      # parsed python value (for edits/prints)


class TInfo:
    __slots__ = ("name", "dims", "gtype", "offset", "nbytes")

    def __init__(self, name, dims, gtype, offset, nbytes):
        self.name = name
        self.dims = dims        # file order: ne[0] (innermost) first
        self.gtype = gtype
        self.offset = offset    # relative to data start
        self.nbytes = nbytes


class GGUF:
    def __init__(self, path):
        self.path = path
        self.kvs = []
        self.tinfos = []
        self.alignment = DEFAULT_ALIGN
        self.data_start = 0
        self._parse()

    # ---- parse ----
    def _rd_str(self, mm, off):
        (n,) = struct.unpack_from("<Q", mm, off)
        off += 8
        b = mm[off:off + n]
        if len(b) != n:
            raise ValueError("truncated string")
        return b, off + n

    def _rd_value(self, mm, off, vt):
        # vt was already consumed by the caller. returns (value, raw, new_off)
        start = off
        if vt in VT_SCALAR:
            fmt, sz = VT_SCALAR[vt]
            (val,) = struct.unpack_from(fmt, mm, off)
            off += sz
        elif vt == VT_STRING:
            b, off = self._rd_str(mm, off)
            val = b.decode("utf-8", errors="backslashreplace")
        elif vt == VT_ARRAY:
            sub = struct.unpack_from("<I", mm, off)[0]
            off += 4
            (cnt,) = struct.unpack_from("<Q", mm, off)
            off += 8
            elems = []
            for _ in range(cnt):
                ev, _, off = self._rd_value_sub(mm, off, sub)
                elems.append(ev)
            val = elems
        else:
            raise ValueError(f"unsupported GGUF value type {vt} at offset {off}")
        return val, bytes(mm[start:off]), off

    def _rd_value_sub(self, mm, off, vt):
        # same as _rd_value but with the type already consumed
        start = off
        if vt in VT_SCALAR:
            fmt, sz = VT_SCALAR[vt]
            (val,) = struct.unpack_from(fmt, mm, off)
            off += sz
        elif vt == VT_STRING:
            b, off = self._rd_str(mm, off)
            val = b.decode("utf-8", errors="backslashreplace")
        elif vt == VT_ARRAY:
            sub = struct.unpack_from("<I", mm, off)[0]
            off += 4
            (cnt,) = struct.unpack_from("<Q", mm, off)
            off += 8
            val = []
            for _ in range(cnt):
                ev, _, off = self._rd_value_sub(mm, off, sub)
                val.append(ev)
        else:
            raise ValueError(f"unsupported GGUF value type {vt}")
        return val, bytes(mm[start:off]), off

    def _wr_str(self, b):
        return struct.pack("<Q", len(b)) + b

    def _wr_value(self, vt, val):
        if vt in VT_SCALAR:
            fmt, _ = VT_SCALAR[vt]
            return struct.pack(fmt, val)
        if vt == VT_STRING:
            return self._wr_str(str(val).encode("utf-8"))
        if vt == VT_ARRAY:
            sub = VT_STRING if val and isinstance(val[0], str) else 4
            out = struct.pack("<I", sub) + struct.pack("<Q", len(val))
            for e in val:
                out += self._wr_value(sub, e)
            return out
        raise ValueError(f"cannot re-encode value type {vt}")

    def _parse(self):
        f = open(self.path, "rb")
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        self._mm = mm
        if mm[:4] != GGUF_MAGIC:
            raise ValueError("not a GGUF file")
        ver, nt, nk = struct.unpack_from("<IQQ", mm, 4)
        if ver != GGUF_VERSION:
            raise ValueError(f"GGUF v{ver} unsupported (need 3)")
        off = 24
        for _ in range(nk):
            key, off = self._rd_str(mm, off)
            vt = struct.unpack_from("<I", mm, off)[0]
            off += 4
            val, raw, off = self._rd_value(mm, off, vt)
            self.kvs.append(KV(vt, key.decode("utf-8"), raw, val))
        for _ in range(nt):
            name, off = self._rd_str(mm, off)
            nd = struct.unpack_from("<I", mm, off)[0]
            off += 4
            dims = list(struct.unpack_from("<" + "Q" * nd, mm, off))
            off += 8 * nd
            gtype, = struct.unpack_from("<I", mm, off)
            off += 4
            toff, = struct.unpack_from("<Q", mm, off)
            off += 8
            self.tinfos.append(TInfo(name.decode("utf-8"), dims, gtype, toff, 0))
        for t in self.tinfos:
            t.nbytes = self.type_nbytes(t.gtype, t.dims)
        self.alignment = self.kv_get("general.alignment", DEFAULT_ALIGN)
        self.data_start = align_up(off, self.alignment)

    def type_nbytes(self, gtype, dims):
        # generic: use elements*size. must know per-type block layout.
        n = 1
        for d in dims:
            n *= d
        tname = GGML_TYPE_NAMES.get(gtype)
        if tname is None:
            raise ValueError(f"unknown ggml type id {gtype}")
        if tname == "F32": return n * 4
        if tname == "F16" or tname == "BF16": return n * 2
        if tname == "F64": return n * 8
        if tname == "I8" or tname == "I16" or tname == "I32":
            return n * int(tname[1]) // 8
        bs, be = GGML_BLOCK_SIZES[tname]
        if n % bs != 0:
            raise ValueError(f"{tname}: {n} elements not a multiple of block {bs}")
        return (n // bs) * be

    def kv_get(self, name, default=None):
        for kv in self.kvs:
            if kv.name == name:
                return kv.value
        return default

    def tensor_bytes(self, t):
        mm = self._mm
        base = self.data_start + t.offset
        return mm[base:base + t.nbytes]

    def close(self):
        try:
            self._mm.close()
        except Exception:
            pass

    def tensor_bytes_by_name(self, name):
        for t in self.tinfos:
            if t.name == name:
                return self.tensor_bytes(t)
        raise KeyError(name)

    # ---- write ----
    def write_with_layout(self, out_path, kv_overrides=None, tensor_plan=None, extra_kvs=None):
        # robust writer: compute offsets, write header/kv/infos, then data
        kv_overrides = kv_overrides or {}
        tensor_plan = tensor_plan or {}
        extra_kvs = extra_kvs or []
        nt = len(self.tinfos)
        nk = len(self.kvs) + len(extra_kvs)

        # build kv section bytes and info section bytes to know exact length
        kv_blob = bytearray()
        for kv in self.kvs:
            kv_blob += self._wr_str(kv.name.encode("utf-8"))
            kv_blob += struct.pack("<I", kv.vtype)
            if kv.name in kv_overrides:
                kv_blob += self._wr_value(kv.vtype, kv_overrides[kv.name])
            else:
                kv_blob += kv.raw
        for vtype, name, val in extra_kvs:
            kv_blob += self._wr_str(name.encode("utf-8"))
            kv_blob += struct.pack("<I", vtype)
            kv_blob += self._wr_value(vtype, val)

        plan_out = []
        for t in self.tinfos:
            if t.name in tensor_plan:
                dims, gtype, data = tensor_plan[t.name]
                nb = data[0] if isinstance(data, tuple) else len(data)
            else:
                dims, gtype, data = t.dims, t.gtype, None
                nb = t.nbytes
            plan_out.append([t.name, dims, gtype, data, nb, 0])

        # infos are built ONCE with real offsets; data_start derives from
        # len(info2), never from an offset-less estimate (the 8-byte offset
        # field per tensor made the old two-pass lengths disagree)
        info2 = bytearray()
        cursor = 0
        for item in plan_out:
            name, dims, gtype, data, nb = item[:5]
            item[5] = cursor
            info2 += self._wr_str(name.encode("utf-8"))
            info2 += struct.pack("<I", len(dims))
            for d in dims:
                info2 += struct.pack("<Q", d)
            info2 += struct.pack("<I", gtype)
            info2 += struct.pack("<Q", cursor)
            cursor = align_up(cursor + nb, self.alignment)

        header_len = 4 + 4 + 8 + 8
        data_start = align_up(header_len + len(kv_blob) + len(info2), self.alignment)

        with open(out_path, "wb") as f:
            f.write(GGUF_MAGIC)
            f.write(struct.pack("<IQQ", GGUF_VERSION, nt, nk))
            f.write(kv_blob)
            f.write(info2)
            here = f.tell()
            if here > data_start:
                raise AssertionError("data_start underflow: header+kv+infos exceed data_start")
            f.write(b"\x00" * (data_start - here))
            for name, dims, gtype, data, nb, off in plan_out:
                # pad to the tensor's declared offset: tensor sizes are not
                # always alignment multiples, inter-tensor gaps are REQUIRED
                cur = f.tell() - data_start
                if cur > off:
                    raise AssertionError(f"{name}: stream at {cur} past offset {off}")
                if cur < off:
                    f.write(b"\x00" * (off - cur))
                if data is None:
                    f.write(self.tensor_bytes_by_name(name))
                elif isinstance(data, tuple):
                    payload = data[1]()
                    if len(payload) != nb:
                        raise AssertionError(f"{name}: producer returned {len(payload)} bytes, expected {nb}")
                    f.write(payload)
                else:
                    f.write(data)
            f.flush()
        return data_start


GGML_TYPE_NAMES = {
    0: "F32", 1: "F16", 2: "Q4_0", 3: "Q4_1", 6: "Q5_0", 7: "Q5_1",
    8: "Q8_0", 9: "Q8_1", 10: "Q2_K", 11: "Q3_K", 12: "Q4_K", 13: "Q5_K",
    14: "Q6_K", 15: "Q8_K", 16: "IQ2_XXS", 17: "IQ2_XS", 18: "IQ5_XXS",
    19: "IQ3_XXS", 20: "IQ1_S", 21: "IQ4_NL", 22: "IQ3_S", 23: "IQ2_S",
    24: "IQ4_XS", 25: "IQ8_0?no", 26: "BF16", 27: "Q4_0_4_4", 28: "Q4_0_4_8",
    29: "Q4_0_8_8", 30: "TQ1_0", 31: "TQ2_0",
}
# block sizes: {name: (elements_per_block, bytes_per_block)}
GGML_BLOCK_SIZES = {
    "Q4_0": (32, 18), "Q4_1": (32, 20), "Q5_0": (32, 22), "Q5_1": (32, 24),
    "Q8_0": (32, 34), "Q8_1": (32, 40), "Q2_K": (256, 84), "Q3_K": (256, 110),
    "Q4_K": (256, 144), "Q5_K": (256, 176), "Q6_K": (256, 210), "Q8_K": (256, 292),
    "IQ2_XXS": (256, 66), "IQ2_XS": (256, 74), "IQ5_XXS": (256, 166),
    "IQ3_XXS": (256, 98), "IQ1_S": (256, 40), "IQ4_NL": (32, 18),
    "IQ3_S": (256, 110), "IQ2_S": (256, 84), "IQ4_XS": (256, 96),
    "TQ1_0": (256, 66), "TQ2_0": (256, 82),
}


def find_moe_layers(g):
    layers = []
    for t in g.tinfos:
        if t.name.endswith(".ffn_gate_exps.weight"):
            il = int(t.name.split(".")[1])
            layers.append(il)
    return sorted(set(layers))


def expert_axis(t, n_expert):
    hits = [i for i, d in enumerate(t.dims) if d == n_expert]
    if len(hits) != 1:
        return None
    return hits[0]


def find_tensor(g, name):
    for t in g.tinfos:
        if t.name == name:
            return t
    return None


def get_expert_count(g):
    for kv in g.kvs:
        if kv.name.endswith(".expert_count") or kv.name == "expert_count":
            if "vision" in kv.name or "attention" in kv.name:
                continue
            return kv
    return None


def get_used_count(g):
    for kv in g.kvs:
        if kv.name.endswith(".expert_used_count") or kv.name == "expert_used_count":
            if "vision" in kv.name or "attention" in kv.name:
                continue
            return kv
    return None


def cmd_inspect(args):
    g = GGUF(args.gguf)
    arch = g.kv_get("general.architecture", "?")
    blk = g.kv_get(f"{arch}.block_count", "?")
    print(f"file: {args.gguf}")
    print(f"arch: {arch}  block_count: {blk}  alignment: {g.alignment}")
    for kv in g.kvs:
        if "expert" in kv.name.lower():
            v = kv.value
            if isinstance(v, list) and len(v) > 8:
                v = f"[{v[0]}, {v[1]}, ... x{len(kv.value)}]"
            print(f"  kv {kv.name} = {v}")
    ec = get_expert_count(g)
    if ec is None:
        print("no expert_count metadata found; is this a MoE GGUF?")
        return 1
    ne = ec.value
    layers = find_moe_layers(g)
    print(f"MoE layers: {len(layers)} -> {layers}")
    for il in layers:
        for suffix in EXP_TENSORS:
            t = find_tensor(g, f"blk.{il}.{suffix}.weight")
            if t is None:
                print(f"  layer {il}: MISSING {suffix}")
                continue
            ax = expert_axis(t, ne)
            slab = t.nbytes / ne if ne else 0
            ok = (ax == len(t.dims) - 1) and (t.nbytes % ne == 0)
            print(f"  layer {il} {suffix:14s} type={GGML_TYPE_NAMES.get(t.gtype, t.gtype):8s} "
                  f"dims={t.dims} axis={ax} slab={slab:.1f}B contiguous={'OK' if ok else 'BAD'}")
        rt = find_tensor(g, f"blk.{il}.{ROUTER_TENSOR}.weight")
        if rt is not None:
            print(f"  layer {il} {ROUTER_TENSOR:14s} type={GGML_TYPE_NAMES.get(rt.gtype, rt.gtype):8s} "
                  f"dims={rt.dims} row={rt.nbytes / ne:.1f}B")
        bt = find_tensor(g, f"blk.{il}.{BIAS_TENSOR}.bias")
        if bt is not None:
            print(f"  layer {il} {BIAS_TENSOR:14s} type={GGML_TYPE_NAMES.get(bt.gtype, bt.gtype):8s} "
                  f"dims={bt.dims} entry={bt.nbytes / ne:.1f}B")
    g.close()
    return 0


def cmd_roundtrip(args):
    g = GGUF(args.gguf)
    g.write_with_layout(args.out)
    g.close()
    a = open(args.gguf, "rb")
    b = open(args.out, "rb")
    sa, sb = os.path.getsize(args.gguf), os.path.getsize(args.out)
    ok = sa == sb
    if ok:
        CH = 4 * 1024 * 1024
        pos = 0
        while True:
            ca, cb = a.read(CH), b.read(CH)
            if ca != cb:
                ok = False
                print(f"first divergence at byte {pos}")
                break
            if not ca:
                break
            pos += len(ca)
    print(f"roundtrip: {'IDENTICAL' if ok else 'MISMATCH'}  ({sa} vs {sb} bytes)")
    a.close()
    b.close()
    return 0 if ok else 1


def plan_layers(g, args_layers):
    all_layers = find_moe_layers(g)
    if not args_layers or args_layers == "all":
        return all_layers
    want = {int(x) for x in args_layers.split(",")}
    bad = want - set(all_layers)
    if bad:
        raise ValueError(f"layers {sorted(bad)} are not MoE layers (have: {all_layers})")
    return [l for l in all_layers if l in want]


_GGUF_QUANTS = None

def _gguf_quants(explicit=None):
    global _GGUF_QUANTS
    if _GGUF_QUANTS is None:
        gguf_py = explicit or os.environ.get("GGUF_PY_PATH")
        if not gguf_py:
            cand = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "gguf-py")
            if os.path.isdir(cand):
                gguf_py = os.path.normpath(cand)
        if not gguf_py or not os.path.isdir(gguf_py):
            raise ValueError("needs the fork's gguf-py (pass --gguf-py or set GGUF_PY_PATH)")
        sys.path.insert(0, gguf_py)
        import numpy as np
        from gguf.quants import dequantize as deq, quantize as quant
        from gguf.constants import GGMLQuantizationType
        _GGUF_QUANTS = (np, deq, quant, GGMLQuantizationType)
    return _GGUF_QUANTS

def rows_to_float(raw, gtype, dims):
    np, deq, _quant, GQT = _gguf_quants()
    arr = np.frombuffer(bytes(raw), dtype=np.uint8)
    if gtype == GGML_F16:
        return np.frombuffer(arr.tobytes(), dtype="<f2").astype(np.float32)
    if gtype == 0:
        return np.frombuffer(arr.tobytes(), dtype="<f4").astype(np.float32)
    return deq(arr, GQT(gtype)).astype(np.float32).ravel()

def neuron_perm(gate_m, up_m, gate_a, up_a, n_inner):
    np, _deq, _quant, _GQT = _gguf_quants()
    fe = np.concatenate([gate_m, up_m], axis=1)
    fr = np.concatenate([gate_a, up_a], axis=1)
    fe = fe / (np.linalg.norm(fe, axis=1, keepdims=True) + 1e-12)
    fr = fr / (np.linalg.norm(fr, axis=1, keepdims=True) + 1e-12)
    S = fe @ fr.T
    try:
        from scipy.optimize import linear_sum_assignment
        ri, ci = linear_sum_assignment(-S)
        perm = np.empty(n_inner, dtype=np.int64)
        perm[ri] = ci
    except ImportError:
        pref = np.argsort(-S, axis=1)
        used = np.zeros(n_inner, dtype=bool)
        perm = np.empty(n_inner, dtype=np.int64)
        for r in np.argsort(-S.max(axis=1)):
            for c in pref[r]:
                if not used[c]:
                    used[c] = True
                    perm[r] = c
                    break
    return perm

def cmd_amputate(args):
    g = GGUF(args.gguf)
    ec = get_expert_count(g)
    if ec is None:
        raise ValueError("no expert_count metadata")
    ne = ec.value
    layers = plan_layers(g, args.layers)
    layer_keeps = {}  # il -> ordered keep list; Trap A: SAME list, SAME
                      # order, slices all five tensors of that layer

    if args.policy:
        # per-layer guided policy: {"layers": {"2": [21,11,...], ...}}
        # every listed layer must keep the SAME count K (expert_count is a
        # single global hyperparameter); lists may be in any order (e.g.
        # mass-ranked) as long as all five tensors use them identically.
        pol = json.load(open(args.policy, encoding="utf-8-sig"))
        pl = pol.get("layers", {})
        want = set(layers)
        have = {int(k) for k in pl}
        if want != have:
            raise ValueError(f"policy layers {sorted(have)} != MoE layers {sorted(want)}")
        Ks = {len(v) for v in pl.values()}
        if len(Ks) != 1:
            raise ValueError(f"policy keep counts differ across layers: {sorted(Ks)}")
        K = Ks.pop()
        for k, v in pl.items():
            kl = [int(x) for x in v]
            if len(set(kl)) != len(kl):
                raise ValueError(f"layer {k}: duplicate experts in keep list")
            if any(x < 0 or x >= ne for x in kl):
                raise ValueError(f"layer {k}: expert index out of range")
            layer_keeps[int(k)] = kl
        print(f"amputate (guided policy): n_expert {ne} -> {K} on {len(layers)} layers" + (" +1 ghost" if args.ghost else ""))
    else:
        if args.keep and args.drop:
            raise ValueError("use --keep or --drop, not both")
        if args.keep:
            keep = sorted({int(x) for x in args.keep.split(",")})
        elif args.drop:
            dset = {int(x) for x in args.drop.split(",")}
            keep = [e for e in range(ne) if e not in dset]
        else:
            raise ValueError("need --keep, --drop, or --policy")
        if not keep:
            raise ValueError("surgery keeps zero experts")
        if keep == list(range(ne)):
            print("nothing to amputate (keep == all)")
            return 0
        K = len(keep)
        for il in layers:
            layer_keeps[il] = list(keep)
        print(f"amputate: n_expert {ne} -> {K} on layers {layers}")
        print(f"  keep: {keep}")

    mass = {}
    if args.ghost:
        np, deq, quant, GQT = _gguf_quants(getattr(args, "gguf_py", None))
        if args.mass:
            import csv as _csv
            for row in _csv.DictReader(open(args.mass, encoding="utf-8-sig")):
                mass[(int(row["layer"]), int(row["expert"]))] = float(row["mass_selected"])

    tensor_plan = {}
    for il in layers:
        kp = layer_keeps[il]
        comp = [e for e in range(ne) if e not in kp] if args.ghost else None
        clusters = []
        cws = []
        canchors = []
        cperms = {}
        if args.ghost:
            # REVIEW-6: multi-ghost clustering. A single-centroid ghost
            # starves (fill ratio 0.005 measured in F2 run 1): group the
            # complement by router-row cosine so each ghost stays
            # direction-coherent (dilution ~1/sqrt(cluster size) within a
            # coherent cluster instead of 1/sqrt(m) across orthogonal ones).
            rt_t = find_tensor(g, f"blk.{il}.{ROUTER_TENSOR}.weight")
            rlen = rt_t.nbytes // ne
            rsrc = g.tensor_bytes(rt_t)
            rvecs = {m: rows_to_float(rsrc[m * rlen:(m + 1) * rlen], rt_t.gtype, rt_t.dims) for m in comp}

            def rcos(a, b):
                na = float(np.linalg.norm(rvecs[a]))
                nb = float(np.linalg.norm(rvecs[b]))
                if na < 1e-12 or nb < 1e-12:
                    return 0.0
                return float(np.dot(rvecs[a], rvecs[b]) / (na * nb))

            order = sorted(comp, key=lambda m: -mass.get((il, m), 0.0))
            for m in order:
                best, bestc = -1, -2.0
                for ci, cl in enumerate(clusters):
                    c = rcos(m, cl[0])
                    if c > bestc:
                        best, bestc = ci, c
                if best >= 0 and bestc >= 0.25:
                    clusters[best].append(m)
                elif len(clusters) < max(1, args.ghosts):
                    clusters.append([m])
                else:
                    clusters[best if best >= 0 else 0].append(m)
            # Trap A invariant: K_phys must be CONSTANT across layers, so
            # every layer gets exactly args.ghosts clusters - split the
            # lowest-cosine members out of large clusters until N reached
            while len(clusters) < max(1, args.ghosts):
                worst_ci, worst_m, worst_c = -1, None, 2.0
                for ci, cl in enumerate(clusters):
                    if len(cl) < 2:
                        continue
                    for m in cl:
                        c = rcos(m, cl[0])
                        if c < worst_c:
                            worst_ci, worst_m, worst_c = ci, m, c
                if worst_m is None:
                    break
                clusters[worst_ci].remove(worst_m)
                clusters.append([worst_m])
            clusters.sort(key=lambda cl: -sum(mass.get((il, m), 0.0) for m in cl))
            K_phys = K + len(clusters)
            gt = find_tensor(g, f"blk.{il}.ffn_gate_exps.weight")
            ut = find_tensor(g, f"blk.{il}.ffn_up_exps.weight")
            n_inner = gt.dims[1]
            gslab = gt.nbytes // ne
            uslab = ut.nbytes // ne
            gsrc = g.tensor_bytes(gt)
            usrc = g.tensor_bytes(ut)
            for cl in clusters:
                anchor = max(cl, key=lambda m: mass.get((il, m), 0.0))
                canchors.append(anchor)
                ms = [mass.get((il, m), 0.0) for m in cl]
                tot = sum(ms)
                cws.append({m: (ms[i] / tot if tot > 0 else 1.0 / len(cl)) for i, m in enumerate(cl)})
                g_a = rows_to_float(gsrc[anchor * gslab:(anchor + 1) * gslab],
                                    gt.gtype, gt.dims).reshape(n_inner, gt.dims[0])
                u_a = rows_to_float(usrc[anchor * uslab:(anchor + 1) * uslab],
                                    ut.gtype, ut.dims).reshape(n_inner, ut.dims[0])
                for m in cl:
                    if m == anchor:
                        continue
                    g_m = rows_to_float(gsrc[m * gslab:(m + 1) * gslab],
                                        gt.gtype, gt.dims).reshape(n_inner, gt.dims[0])
                    u_m = rows_to_float(usrc[m * uslab:(m + 1) * uslab],
                                        ut.gtype, ut.dims).reshape(n_inner, ut.dims[0])
                    cperms[m] = neuron_perm(g_m, u_m, g_a, u_a, n_inner)
            print(f"  layer {il}: kept {len(kp)} + {len(clusters)} ghost(s), cluster sizes {[len(c) for c in clusters]}")
        else:
            K_phys = K
        for suffix in EXP_TENSORS:
            t = find_tensor(g, f"blk.{il}.{suffix}.weight")
            if t is None:
                raise ValueError(f"missing blk.{il}.{suffix}.weight")
            ax = expert_axis(t, ne)
            if ax != len(t.dims) - 1:
                raise ValueError(f"{t.name}: expert axis {ax} is not outermost; cannot slice raw")
            if t.nbytes % ne:
                raise ValueError(f"{t.name}: {t.nbytes} not divisible by {ne}")
            slab = t.nbytes // ne
            src = g.tensor_bytes(t)
            is_down = (suffix == "ffn_down_exps")
            gtype_out = t.gtype

            def cluster_ghost_mats(mat_src, m_slab):
                # per-cluster ghost: weighted, neuron-aligned merge of its
                # members, returned as float32 matrices in cluster order
                out_m = []
                for ci, cl in enumerate(clusters):
                    acc = None
                    for m in cl:
                        flat = rows_to_float(mat_src[m * m_slab:(m + 1) * m_slab],
                                             t.gtype, t.dims)
                        m2 = flat.reshape(t.dims[1], t.dims[0])
                        p = cperms.get(m)
                        if p is not None:
                            m2 = m2[:, p] if is_down else m2[p, :]
                        w = cws[ci][m]
                        acc = w * m2 if acc is None else acc + w * m2
                    out_m.append(acc)
                return out_m

            def mat_bytes(m):
                if args.f16 or t.gtype == GGML_F16:
                    return m.astype("<f2").tobytes()
                if t.gtype == 0:
                    return m.astype("<f4").tobytes()
                return quant(np.ascontiguousarray(m), GQT(t.gtype))

            if args.f16 and t.gtype != GGML_F16:
                # whole planned tensor -> f16 (kept slabs dequant; the llama-
                # quantize pass then restores Q4_K_M identically on both A/B
                # arms so the delta measures only the ghost effect)
                parts = [rows_to_float(src[e * slab:(e + 1) * slab],
                                       t.gtype, t.dims).reshape(t.dims[1], t.dims[0]) for e in kp]
                if args.ghost:
                    parts += cluster_ghost_mats(src, slab)
                data = b"".join(p.astype("<f2").tobytes() for p in parts)
                gtype_out = GGML_F16
            else:
                # kept slabs stay RAW at the original quant type
                data = b"".join(bytes(src[e * slab:(e + 1) * slab]) for e in kp)
                if args.ghost:
                    data = data + b"".join(mat_bytes(m) for m in cluster_ghost_mats(src, slab))
            dims = list(t.dims)
            dims[ax] = K_phys
            tensor_plan[t.name] = (dims, gtype_out, data)
        rt = find_tensor(g, f"blk.{il}.{ROUTER_TENSOR}.weight")
        if rt is not None:
            if rt.nbytes % ne:
                raise ValueError(f"{rt.name}: {rt.nbytes} not divisible by {ne}")
            row = rt.nbytes // ne
            src = g.tensor_bytes(rt)
            data = b"".join(bytes(src[e * row:(e + 1) * row]) for e in kp)
            if args.ghost:
                for ci, cl in enumerate(clusters):
                    r_g = None
                    n_target = 0.0
                    for m in cl:
                        rv = rows_to_float(src[m * row:(m + 1) * row], rt.gtype, rt.dims)
                        w = cws[ci][m]
                        term = w * rv
                        r_g = term if r_g is None else r_g + term
                        n_target += w * float(np.linalg.norm(rv))
                    n_g = float(np.linalg.norm(r_g))
                    # REVIEW-4: restore the merged router row to the
                    # weighted-mean member norm so the ghost's routing
                    # logit is not crushed by averaging
                    if n_g > 1e-12 and n_target > 0:
                        r_g = r_g * (n_target / n_g)
                    if rt.gtype == GGML_F16:
                        data = data + r_g.astype("<f2").tobytes()
                    else:
                        data = data + r_g.astype("<f4").tobytes()
            dims = list(rt.dims)
            dims[expert_axis(rt, ne)] = K_phys
            tensor_plan[rt.name] = (dims, rt.gtype, data)
        bt = find_tensor(g, f"blk.{il}.{BIAS_TENSOR}.bias")
        if bt is not None:
            ent = bt.nbytes // ne
            src = g.tensor_bytes(bt)
            data = b"".join(bytes(src[e * ent:(e + 1) * ent]) for e in kp)
            if args.ghost:
                for ci, cl in enumerate(clusters):
                    b_g = None
                    for m in cl:
                        term = cws[ci][m] * rows_to_float(src[m * ent:(m + 1) * ent], bt.gtype, bt.dims)
                        b_g = term if b_g is None else b_g + term
                    if bt.gtype == GGML_F16:
                        data = data + b_g.astype("<f2").tobytes()
                    else:
                        data = data + b_g.astype("<f4").tobytes()
            dims = list(bt.dims)
            dims[expert_axis(bt, ne)] = K_phys
            tensor_plan[bt.name] = (dims, bt.gtype, data)

    K_meta = K + (0 if not args.ghost else len(clusters) if clusters else 1)
    kv_over = {ec.name: K_meta}
    uc = get_used_count(g)
    warn_used = None
    if uc is not None:
        if isinstance(uc.value, list):
            used = uc.value
            if any(u > K_meta for u in used):
                if not args.clamp_used:
                    raise ValueError(f"{uc.name} has values > {K}; pass --clamp-used to clamp")
                warn_used = uc.name
                kv_over[uc.name] = [min(u, K_meta) for u in used]
        else:
            if uc.value > K_meta:
                if not args.clamp_used:
                    raise ValueError(f"{uc.name}={uc.value} > {K}; pass --clamp-used to clamp")
                warn_used = uc.name
                kv_over[uc.name] = K_meta
    if warn_used:
        print(f"  clamped {warn_used} to <= {K_meta}")

    note = json.dumps({
        "op": "amputate", "source": os.path.basename(args.gguf),
        "n_expert": ne, "kept": K, "kept_plus_ghost": K_meta, "ghost": bool(args.ghost), "guided": bool(args.policy),
        "layers": {str(il): layer_keeps[il] for il in sorted(layer_keeps)},
    }, separators=(",", ":"))
    extra = [(VT_STRING, "general.foundry_note", note)]

    print(f"writing {args.out} ...")
    g.write_with_layout(args.out, kv_overrides=kv_over, tensor_plan=tensor_plan, extra_kvs=extra)
    g.close()
    v = GGUF(args.out)
    ec2 = get_expert_count(v)
    print(f"verify: reopened, expert_count = {ec2.value if ec2 else '?'}")
    v.close()
    return 0


def cmd_merge(args):
    np, deq, quant, GQT = _gguf_quants(args.gguf_py)

    g = GGUF(args.gguf)
    ec = get_expert_count(g)
    if ec is None:
        raise ValueError("no expert_count metadata")
    ne = ec.value
    groups = json.loads(args.groups) if isinstance(args.groups, str) else args.groups
    groups = [tuple(x) for x in groups]
    if not groups:
        raise ValueError("need --groups [[a,b],[c,d],...]")
    members = {e for grp in groups for e in grp}
    if any(e >= ne for e in members):
        raise ValueError("group member out of range")
    firsts = {min(grp): grp for grp in groups}
    out_type = args.out_type
    layers = plan_layers(g, args.layers)
    print(f"merge: n_expert {ne} -> {ne - sum(len(x) - 1 for x in groups)} on layers {layers}")
    print(f"  groups: {groups}  out_type: {out_type}")

    # REVIEW-4: gating-mass weights from the Phase 3b router histogram
    # (DAAVFX_ROUTER_LOG csv). Ghost averaging uses w_i = M_i / sum(M);
    # anchor = highest-mass member; router rows get L2-norm restore.
    mass = {}
    if args.mass:
        import csv as _csv
        for row in _csv.DictReader(open(args.mass, encoding="utf-8-sig")):
            mass[(int(row["layer"]), int(row["expert"]))] = float(row["mass_selected"])
        print(f"  mass loaded for {len(mass)} (layer, expert) pairs from {args.mass}")

    def grp_weights(il, grp):
        ms = [mass.get((il, m), 0.0) for m in grp]
        tot = sum(ms)
        if tot <= 0:
            u = 1.0 / len(grp)
            return {m: u for m in grp}
        return {m: (mass.get((il, m), 0.0) / tot) for m in grp}

    K_total = ne - sum(len(x) - 1 for x in groups)

    # REVIEW-2 pass 1: SwiGLU neuron-permutation alignment (module-level
    # neuron_perm; hoisted so amputate --ghost shares it). Align each
    # group's members to the group's highest-mass anchor before averaging.

    perms = {}  # (il, member) -> int64 perm into anchor neuron order
    # REVIEW-4: alignment anchor = the group's HIGHEST-GATING-MASS member
    # (from --mass router histogram); fallback = lowest index.
    def grp_anchor(il, grp):
        ms = [(mass.get((il, m), 0.0), -m, m) for m in grp]
        return max(ms)[2]

    for il in layers:
        gt = find_tensor(g, f"blk.{il}.ffn_gate_exps.weight")
        ut = find_tensor(g, f"blk.{il}.ffn_up_exps.weight")
        if gt is None or ut is None:
            raise ValueError(f"layer {il}: missing gate/up expert tensors")
        n_inner = gt.dims[1]
        if ut.dims[1] != n_inner:
            raise ValueError(f"layer {il}: gate/up inner dims disagree")
        gslab = gt.nbytes // ne
        uslab = ut.nbytes // ne
        gsrc = g.tensor_bytes(gt)
        usrc = g.tensor_bytes(ut)
        for _pos, grp in firsts.items():
            if len(grp) < 2:
                continue
            anchor = grp_anchor(il, grp)
            ga = rows_to_float(gsrc[anchor * gslab:(anchor + 1) * gslab],
                               gt.gtype, gt.dims).reshape(n_inner, gt.dims[0])
            ua = rows_to_float(usrc[anchor * uslab:(anchor + 1) * uslab],
                               ut.gtype, ut.dims).reshape(n_inner, ut.dims[0])
            for m in grp:
                if m == anchor:
                    continue
                gm = rows_to_float(gsrc[m * gslab:(m + 1) * gslab],
                                   gt.gtype, gt.dims).reshape(n_inner, gt.dims[0])
                um = rows_to_float(usrc[m * uslab:(m + 1) * uslab],
                                   ut.gtype, ut.dims).reshape(n_inner, ut.dims[0])
                perms[(il, m)] = neuron_perm(gm, um, ga, ua, n_inner)
        n_al = sum(1 for k in perms if k[0] == il)
        print(f"  layer {il}: permutation-aligned {n_al} member(s)")

    # pass 2: per-tensor producers (memory-safe: one tensor's output bytes
    # exist at a time; nothing is accumulated across layers)
    def emit(m):
        if out_type == "f16":
            return m.astype("<f2").tobytes()
        return quant(np.ascontiguousarray(m), GGMLQuantizationType.Q8_0)

    tensor_plan = {}
    for il in layers:
        for suffix in EXP_TENSORS:
            t = find_tensor(g, f"blk.{il}.{suffix}.weight")
            if t is None:
                raise ValueError(f"missing blk.{il}.{suffix}.weight")
            ax = expert_axis(t, ne)
            if ax != len(t.dims) - 1:
                raise ValueError(f"{t.name}: expert axis not outermost; merge needs contiguous experts")
            if t.nbytes % ne:
                raise ValueError(f"{t.name}: {t.nbytes} not divisible by {ne}")
            ne0 = t.dims[0]
            ne1 = t.dims[1]
            is_down = (suffix == "ffn_down_exps")
            if out_type == "f16":
                slab_out = ne0 * ne1 * 2
            else:
                if ne0 % 32:
                    raise ValueError(f"{t.name}: ne0 {ne0} not divisible by 32 for q8_0")
                slab_out = ne1 * (ne0 // 32) * 34
            gtype_out = GGML_F16 if out_type == "f16" else GGML_Q8_0

            def produce(t=t, il=il, ne0=ne0, ne1=ne1, is_down=is_down):
                slab = t.nbytes // ne
                src = g.tensor_bytes(t)
                out = bytearray()
                for e in range(ne):
                    if e in members:
                        if e in firsts:
                            grp = firsts[e]
                            ws = grp_weights(il, grp)
                            acc = None
                            for m in grp:
                                flat = rows_to_float(src[m * slab:(m + 1) * slab],
                                                     t.gtype, t.dims)
                                m2 = flat.reshape(ne1, ne0)
                                p = perms.get((il, m))
                                if p is not None:
                                    m2 = m2[:, p] if is_down else m2[p, :]
                                w = ws[m]
                                acc = w * m2 if acc is None else acc + w * m2
                            out += emit(acc)
                    else:
                        flat = rows_to_float(src[e * slab:(e + 1) * slab],
                                             t.gtype, t.dims)
                        out += emit(flat.reshape(ne1, ne0))
                return bytes(out)

            dims = list(t.dims)
            dims[ax] = K_total
            tensor_plan[t.name] = (dims, gtype_out, (K_total * slab_out, produce))
        rt = find_tensor(g, f"blk.{il}.{ROUTER_TENSOR}.weight")
        if rt is not None:
            row = rt.nbytes // ne
            src = g.tensor_bytes(rt)
            rf = {e: rows_to_float(src[e * row:(e + 1) * row], rt.gtype, rt.dims) for e in sorted(members)}
            out = bytearray()
            K = 0
            for e in range(ne):
                if e in members:
                    if e in firsts:
                        grp = firsts[e]
                        ws = grp_weights(il, grp)
                        r_g = None
                        n_target = 0.0
                        for m in grp:
                            w = ws[m]
                            term = w * rf[m]
                            r_g = term if r_g is None else r_g + term
                            n_target += w * float(np.linalg.norm(rf[m]))
                        n_g = float(np.linalg.norm(r_g))
                        # REVIEW-4: averaging shrinks the router row's L2
                        # norm, crushing the ghost's routing logit; restore
                        # to the weighted-mean member norm
                        if n_g > 1e-12 and n_target > 0:
                            r_g = r_g * (n_target / n_g)
                        out += r_g.astype("<f2").tobytes()
                        K += 1
                else:
                    out += rows_to_float(src[e * row:(e + 1) * row], rt.gtype, rt.dims).astype("<f2").tobytes()
                    K += 1
            dims = list(rt.dims)
            dims[expert_axis(rt, ne)] = K
            tensor_plan[rt.name] = (dims, GGML_F16, bytes(out))
        bt = find_tensor(g, f"blk.{il}.{BIAS_TENSOR}.bias")
        if bt is not None:
            ent = bt.nbytes // ne
            src = g.tensor_bytes(bt)
            bf = {e: rows_to_float(src[e * ent:(e + 1) * ent], bt.gtype, bt.dims) for e in sorted(members)}
            out = bytearray()
            K = 0
            for e in range(ne):
                if e in members:
                    if e in firsts:
                        grp = firsts[e]
                        ws = grp_weights(il, grp)
                        b_g = None
                        for m in grp:
                            term = ws[m] * bf[m]
                            b_g = term if b_g is None else b_g + term
                        out += b_g.astype("<f2").tobytes()
                        K += 1
                else:
                    out += rows_to_float(src[e * ent:(e + 1) * ent], bt.gtype, bt.dims).astype("<f2").tobytes()
                    K += 1
            dims = list(bt.dims)
            dims[expert_axis(bt, ne)] = K
            tensor_plan[bt.name] = (dims, GGML_F16, bytes(out))

    kv_over = {ec.name: K_total}
    uc = get_used_count(g)
    if uc is not None:
        if isinstance(uc.value, list):
            if any(u > K_total for u in uc.value):
                kv_over[uc.name] = [min(u, K_total) for u in uc.value]
        elif uc.value > K_total:
            kv_over[uc.name] = K_total

    note = json.dumps({
        "op": "merge", "source": os.path.basename(args.gguf),
        "n_expert": ne, "groups": [list(x) for x in groups],
        "layers": layers, "out_type": out_type,
        "neuron_perm_alignment": True,
    }, separators=(",", ":"))
    extra = [(VT_STRING, "general.foundry_note", note)]

    print(f"writing {args.out} ...")
    g.write_with_layout(args.out, kv_overrides=kv_over, tensor_plan=tensor_plan, extra_kvs=extra)
    g.close()
    v = GGUF(args.out)
    print(f"verify: reopened, expert_count = {get_expert_count(v).value}")
    v.close()
    return 0


def main():
    ap = argparse.ArgumentParser(description="MoE expert surgery for GGUF (lfm2_moe family)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("inspect")
    p.add_argument("--gguf", required=True)

    p = sub.add_parser("roundtrip-test")
    p.add_argument("--gguf", required=True)
    p.add_argument("--out", required=True)

    p = sub.add_parser("amputate")
    p.add_argument("--gguf", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--keep", default=None, help="comma list of experts to keep")
    p.add_argument("--drop", default=None, help="comma list of experts to drop")
    p.add_argument("--layers", default="all")
    p.add_argument("--clamp-used", action="store_true")
    p.add_argument("--ghosts", type=int, default=1, help="number of cosine-clustered ghosts per layer (default 1; 3-4 recommended)")
    p.add_argument("--ghost", action="store_true",
                   help="append ONE mass-weighted, neuron-aligned ghost slab per "
                        "layer for the complement experts (kept slabs stay raw at "
                        "original quant; routers sliced to kept+1 ghost row with "
                        "L2 restore); requires numpy/gguf-py")
    p.add_argument("--mass", default=None,
                   help="router-hist.csv (DAAVFX_ROUTER_LOG) for ghost weighting "
                        "and anchor choice; uniform fallback if omitted")
    p.add_argument("--f16", action="store_true",
                   help="write planned expert tensors as f16 (kept slabs dequant; "
                        "routers/bias untouched) - the input for an identical "
                        "f16 -> llama-quantize pass on both A/B arms")
    p.add_argument("--policy", default=None,
                   help="guided policy JSON: {\"layers\": {\"2\": [keep...], ...}}; "
                        "same keep count K on every MoE layer; each list is used "
                        "verbatim (same order) on all five tensors of that layer")

    p = sub.add_parser("merge")
    p.add_argument("--gguf", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--groups", required=True, help="JSON list of lists, e.g. [[3,17],[8,21]]")
    p.add_argument("--layers", default="all")
    p.add_argument("--out-type", choices=["f16", "q8_0"], default="f16")
    p.add_argument("--gguf-py", default=None)
    p.add_argument("--mass", default=None,
                   help="router-hist.csv (DAAVFX_ROUTER_LOG) for mass-weighted ghosts, "
                        "anchor by highest mass, router-row L2 norm restore")

    args = ap.parse_args()
    fn = {"inspect": cmd_inspect, "roundtrip-test": cmd_roundtrip,
          "amputate": cmd_amputate, "merge": cmd_merge}[args.cmd]
    sys.exit(fn(args))


if __name__ == "__main__":
    main()


