#!/usr/bin/env python3
"""Capture-sufficiency calculator for router histograms (zero-gate paper tool).

Reads a router histogram CSV with columns:
    layer,expert,selected,mass_selected,mass_all,tokens

and decides whether the capture is ADMISSIBLE or INSUFFICIENT-CAPTURE for a
cold-tail / expert-evolution verdict.

Uniform null model (the accountant's model):
  each of the S selections lands in any one of the N slots with prob 1/N, so
      P[slot still empty after S] = (1 - 1/N)^S = exp(-S/N) = q   (for N >> 1)
      E[occupied] = N * (1 - q)
      Var[occupied] = N*q*(1-q) + N*(N-1)*(b - q^2),  b = (1 - 2/N)^S
  which is exact; the second term is the (negative) covariance of two slot
  indicators and keeps the band honest for small N.

Coupon requirement (the gate): the expected occupancy must reach p of the
topology, E[occupied] = N*(1 - q) = p*N, so q = 1 - p and
      S_req = -N * ln(1 - p)
For p = 0.95 that is S_req = N * ln(20) = 2.996 * N.  (Stricter than the
expected-occupancy gate, P[no slot empty] = 0.95 needs ~N*(ln N + 1) draws;
that number is reported for context but is not the policy threshold.)

Verdict rule (both must pass, else INSUFFICIENT-CAPTURE):
  C1  S >= S_req(N, p)                            the coupon gate
  C2  observed occupied <= E[occupied] + 1.96*SD  histogram integrity: the
      capture must not claim more coverage than S draws can produce under the
      null (a count bug, a top-k mismatch or duplicated rows).  Occupancy
      BELOW the band is reported as a note (concentrated routing or an open
      window), not as a verdict driver.

Exit code 0 means ADMISSIBLE, 1 INSUFFICIENT-CAPTURE, 2 usage/parse error.
Stdlib only. ASCII only.
"""

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone

FLINT_N_DEFAULT = 12032  # Flint: 47 MoE layers x 256 experts
SCHEMA = "daavfx/capture-sufficiency/v1"
Z95 = 1.959963985


def capture_read(path):
    """Parse a router histogram CSV into slots, S and observed occupancy."""
    slots = {}
    token_counts = set()
    with open(path, newline="", encoding="utf-8") as fh:
        rdr = csv.DictReader(fh)
        need = {"layer", "expert", "selected", "tokens"}
        missing = need - set(rdr.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing column(s) {sorted(missing)}; "
                             f"found {rdr.fieldnames}")
        for row in rdr:
            key = (int(row["layer"]), int(row["expert"]))
            if key in slots:
                raise ValueError(f"{path}: duplicate row for slot {key}")
            slots[key] = int(float(row["selected"]))
            token_counts.add(int(row["tokens"]))
    return {
        "path": path,
        "slots": slots,
        "n_csv": len(slots),
        "layers": sorted({k[0] for k in slots}),
        "selections": sum(slots.values()),
        "observed_occupied": sum(1 for v in slots.values() if v > 0),
        "token_counts": sorted(token_counts),
    }


def expected_occupied(n, s):
    """E[occupied] = N * (1 - q), q = (1 - 1/N)^S = exp(-S/N) for N >> 1."""
    return n * (1.0 - (1.0 - 1.0 / n) ** s) if n > 0 else 0.0


def occupancy_sd(n, s):
    """SD of the occupied count: Var = N*q*(1-q) + N*(N-1)*(b - q^2).

    q = (1 - 1/N)^S, b = (1 - 2/N)^S; both exact, so the band stays valid
    for small N (the exp approximation breaks the cancellation here).
    """
    if n <= 0:
        return 0.0
    q = (1.0 - 1.0 / n) ** s
    b = (1.0 - 2.0 / n) ** s if n > 1 else 0.0
    var = n * q * (1.0 - q) + n * (n - 1) * (b - q * q)
    return math.sqrt(max(var, 0.0))


def selections_required(n, target):
    """S_req from E[occupied] = p*N:  1 - exp(-S/N) = p  =>  S = -N*ln(1-p).

    p = 0.95 gives S_req = N*ln(20) ~ 2.996*N.  This gates expected
    occupancy, not full coverage: P[some slot empty] = N*exp(-S/N) ~ 0.05
    at the same S, i.e. a handful of empty slots stays probable by design.
    """
    if not 0.0 < target < 1.0:
        raise ValueError("target must be in (0, 1)")
    return -n * math.log(1.0 - target)


def p_full_coverage(n, s):
    """P[no slot stays empty] = (1 - exp(-S/N))^N."""
    return (1.0 - math.exp(-s / n)) ** n if n > 0 else 1.0


def coupon_full(n):
    """E[draws to touch every slot] = N * (H(N) - gamma + 1/2) ~= N*ln(N)."""
    return n * (math.log(n) + 0.5772156649 + 0.5)


def evaluate(cap, base_n, target):
    """Apply C1 (coupon gate) and C2 (integrity) to the capture."""
    s = cap["selections"]
    s_req = selections_required(base_n, target)
    mean_c = expected_occupied(cap["n_csv"], s)
    sd_c = occupancy_sd(cap["n_csv"], s)
    upper_c = mean_c + Z95 * sd_c
    lower_c = mean_c - Z95 * sd_c
    mean_t = expected_occupied(base_n, s)
    sd_t = occupancy_sd(base_n, s)
    c1 = s >= s_req
    c2 = cap["observed_occupied"] <= upper_c
    reasons = []
    if not c1:
        reasons.append(
            f"coupon gate: S={s} selections vs S_req={math.ceil(s_req)} "
            f"(=-N*ln(1-p), p={target:.0%}, N={base_n}); at this S an empty "
            f"slot is the uniform expectation (E[occupied]="
            f"{mean_t:.1f}+/-{Z95 * sd_t:.1f} over the full topology), so a "
            f"cold-tail finding cannot be separated from plain undersampling")
    if not c2:
        reasons.append(
            f"integrity: observed occupied={cap['observed_occupied']} exceeds "
            f"the uniform 95% upper bound {upper_c:.1f} for S={s} over the "
            f"captured {cap['n_csv']} slots; histogram over-claims coverage")
    notes = []
    if c2 and cap["observed_occupied"] < lower_c:
        notes.append(
            f"info: observed occupied={cap['observed_occupied']} is below the "
            f"uniform 95% lower bound {lower_c:.1f} for the captured window; "
            f"routing is concentrated or the window is open - inconclusive at "
            f"this S, which is itself a reason to recapture")
    return {
        "verdict": "ADMISSIBLE" if (c1 and c2) else "INSUFFICIENT-CAPTURE",
        "c1": c1, "c2": c2, "reasons": reasons, "notes": notes,
        "s_req": s_req,
        "cap_mean": mean_c, "cap_sd": sd_c, "cap_lo": lower_c, "cap_hi": upper_c,
        "top_mean": mean_t, "top_sd": sd_t,
        "p_full": p_full_coverage(base_n, s),
        "coupon_full": coupon_full(base_n),
        "fill_z": ((cap["observed_occupied"] - mean_c) / sd_c) if sd_c > 0 else 0.0,
    }


def build_certificate(cap, ev, base_n, target, kt):
    """JSON-able certificate; the logger should emit this at capture time."""
    by_layer = {}
    for (layer, expert), sel in cap["slots"].items():
        by_layer.setdefault(layer, {})[expert] = sel
    per_layer = [{
        "layer": layer,
        "experts": len(experts),
        "selections": sum(experts.values()),
        "occupied": sum(1 for v in experts.values() if v > 0),
        "expected_occupied": round(
            expected_occupied(len(experts), sum(experts.values())), 2),
    } for layer, experts in sorted(by_layer.items())]
    s, obs = cap["selections"], cap["observed_occupied"]
    return {
        "schema": SCHEMA,
        "kind": "router-capture-sufficiency-certificate",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_csv": cap["path"],
        "capture": {
            "slots_in_csv": cap["n_csv"],
            "layers": len(cap["layers"]),
            "layer_span": [cap["layers"][0], cap["layers"][-1]] if cap["layers"] else [],
            "experts_per_layer": sorted({len(v) for v in by_layer.values()}),
            "router_topk_assumed": kt,
            "routed_tokens_per_row": cap["token_counts"],
            "selections_total": s,
            "observed_occupied": obs,
            "observed_share": round(obs / cap["n_csv"], 6) if cap["n_csv"] else 0.0,
        },
        "model_topology": {
            "base_slots_n": base_n,
            "captured_slots": cap["n_csv"],
            "capture_share_of_topology": round(cap["n_csv"] / base_n, 6),
            "note": ("capture judged as a uniform sample of the full topology; "
                     "N and p are set from the real model, not from the slice"),
        },
        "uniform_null": {
            "capture_window": {
                "n": cap["n_csv"],
                "expected_occupied": round(ev["cap_mean"], 1),
                "sd": round(ev["cap_sd"], 1),
                "ci95": [round(ev["cap_lo"], 1), round(ev["cap_hi"], 1)],
                "fill_z": round(ev["fill_z"], 2),
            },
            "full_topology": {
                "n": base_n,
                "expected_occupied": round(ev["top_mean"], 1),
                "sd": round(ev["top_sd"], 1),
                "ci95": [round(ev["top_mean"] - Z95 * ev["top_sd"], 1),
                         round(ev["top_mean"] + Z95 * ev["top_sd"], 1)],
            },
        },
        "requirement": {
            "occupancy_target": target,
            "formula": "S_req = -N*ln(1-p)",
            "selections_required": math.ceil(ev["s_req"]),
            "selections_present": s,
            "selection_headroom": round(s / ev["s_req"], 4),
            "full_coupon_selections_est": math.ceil(ev["coupon_full"]),
            "p_zero_empty_at_S": ev["p_full"],
        },
        "decision": {
            "verdict": ev["verdict"],
            "criteria": {"C1_selections_ge_required": ev["c1"],
                         "C2_observed_within_integrity_band": ev["c2"]},
            "reasons": ev["reasons"],
            "notes": ev["notes"],
            "policy": "no X-ray verdict without an admissible capture certificate",
        },
        "per_layer": per_layer,
    }


def print_report(cert, ev):
    c, t, n = cert["capture"], cert["model_topology"], cert["uniform_null"]
    r = cert["requirement"]
    cw, tw = n["capture_window"], n["full_topology"]
    print(f"== capture-sufficiency certificate ({cert['schema']}) ==")
    print(f"source           : {cert['source_csv']}")
    print(f"slots in csv     : {c['slots_in_csv']} ({c['layers']} layers, span "
          f"{c['layer_span'][0]}..{c['layer_span'][-1]}, "
          f"{c['experts_per_layer']} experts/layer)")
    print(f"model topology   : N = {t['base_slots_n']} slots "
          f"(capture covers {t['capture_share_of_topology']:.2%} of topology)")
    print(f"selections       : S = {c['selections_total']} recorded routing "
          f"decisions (rows carry routed_tokens={c['routed_tokens_per_row']})")
    print(f"observed occupied: {c['observed_occupied']} of {c['slots_in_csv']} "
          f"slots ({c['observed_share']:.2%})")
    print("-- uniform null (coupon math) --")
    print(f"capture window N={cw['n']}: E[occupied]={cw['expected_occupied']} "
          f"sd={cw['sd']} ci95=[{cw['ci95'][0]}, {cw['ci95'][1]}] "
          f"fill z={cw['fill_z']:+.2f}")
    print(f"full topology  N={tw['n']}: E[occupied]={tw['expected_occupied']} "
          f"sd={tw['sd']} ci95=[{tw['ci95'][0]}, {tw['ci95'][1]}]")
    print(f"target occupancy: {r['occupancy_target']:.0%} -> "
          f"S_req={r['selections_required']} "
          f"(=-N*ln(1-p), p={r['occupancy_target']:.0%}, N={tw['n']})")
    print(f"selection ratio : S/S_req = {r['selection_headroom']:.2%} "
          f"({r['selections_present']} present vs {r['selections_required']} needed)")
    print(f"full collection : ~{r['full_coupon_selections_est']} selections to "
          f"touch every slot once; P[zero empty at S]={r['p_zero_empty_at_S']:.3e}")
    print("-- verdict --")
    print(f"C1 coupon gate (S >= S_req)          : {ev['c1']}")
    print(f"C2 integrity (occupancy <= 95% upper): {ev['c2']}")
    print(f"VERDICT: {ev['verdict']}")
    for why in ev["reasons"]:
        print(f"  reason: {why}")
    for note in ev["notes"]:
        print(f"  note: {note}")
    print(f"policy: {cert['decision']['policy']}")


def main(argv):
    ap = argparse.ArgumentParser(
        description="Admissibility calculator for router histogram captures: a "
                    "cold-tail or expert-evolution verdict requires an "
                    "ADMISSIBLE certificate, not just an occupied bin.",
        epilog=f"ADMISSIBLE iff C1 (S >= S_req) and C2 (occupancy within the "
               f"integrity band) both pass; certificate JSON is {SCHEMA}.")
    ap.add_argument("csv", help="router histogram CSV "
                                "(layer,expert,selected,mass_selected,mass_all,tokens)")
    ap.add_argument("--base-n", type=int, default=FLINT_N_DEFAULT,
                    help=f"full topology slot count N to judge against "
                         f"(default {FLINT_N_DEFAULT} = Flint 47 layers x 256 experts)")
    ap.add_argument("--kt", type=int, default=1,
                    help="router top-k per token, metadata only (default 1)")
    ap.add_argument("--target", type=float, default=0.95,
                    help="occupancy confidence target p in (0,1) (default 0.95)")
    ap.add_argument("--emit", metavar="PATH",
                    help="also write the certificate JSON to PATH")
    args = ap.parse_args(argv)

    try:
        cap = capture_read(args.csv)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if cap["selections"] <= 0:
        print(f"error: {args.csv}: zero selections; capture is empty",
              file=sys.stderr)
        return 2

    ev = evaluate(cap, args.base_n, args.target)
    cert = build_certificate(cap, ev, args.base_n, args.target, args.kt)
    print_report(cert, ev)
    if args.emit:
        with open(args.emit, "w", encoding="utf-8") as fh:
            json.dump(cert, fh, indent=2)
            fh.write("\n")
        print(f"certificate written: {args.emit}")
    return 0 if ev["verdict"] == "ADMISSIBLE" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
