# Capture sufficiency: why the Flint-Q2 router histogram cannot carry a cold-tail verdict

Zero-gate paper task, batch 1 (auditor-ISAYY). No box time, no model runs, no
servers: reading and writing files only. Everything below is reproducible with

    python docs/daavfx/auditor-ISAYY/batch1/capture-sufficiency.py <csv>

Artifacts:
- calculator: `shared/llama.cpp-abelianIUT/docs/daavfx/auditor-ISAYY/batch1/capture-sufficiency.py`
- test input: `shared/llama.cpp-abelianIUT/scripts/daavfx/results/flint/router-q2xl-initial.csv`
- this report: the file you are reading

## 1. The formula

Uniform null: each of the S recorded routing decisions independently lands in
any one of the N topology slots with probability 1/N. Define
q = P[a given slot stays empty after S selections] = (1 - 1/N)^S.

For N >> S this is q ~= exp(-S/N), so the expected occupied count is

    E[occupied] = N * (1 - q)  =  N * (1 - exp(-S/N))                    (1)

Occupied-slot indicators are not independent, so the exact variance carries the
covariance term (b = (1 - 2/N)^S is P[two specific slots both stay empty]):

    Var[occupied] = N*q*(1-q) + N*(N-1)*(b - q^2)                        (2)

The second term is negative and must be computed with exact powers: mixing the
exp approximation into q while keeping (1 - 2/N)^S for b breaks the
cancellation and can produce a negative variance (an early draft of the
calculator returned sd = 0.0 this way). The script uses exact powers for both
(`capture-sufficiency.py:77` expected_occupied, `capture-sufficiency.py:82`
occupancy_sd).

Requirement derivation (the gate). A cold-tail verdict needs unoccupied slots
to be improbable, i.e. expected occupancy must reach p of the topology:

    E[occupied] = p*N  =>  1 - q = p  =>  q = 1 - p
    (1 - 1/N)^S = 1 - p  =>  S = ln(1 - p) / ln(1 - 1/N) = -N*ln(1-p)     (3)

(the last step is N >> 1). For p = 0.95, S_req = N*ln(20) = 2.996*N
(`capture-sufficiency.py:96` selections_required). Context, not policy: seeing
every slot at least once (the full coupon collector) needs
N*(ln N + gamma + 1/2) ~= N*ln(N) draws (`capture-sufficiency.py:113`
coupon_full), and P[no slot stays empty] = (1 - q)^N is printed per run
(`capture-sufficiency.py:108` p_full_coverage).

Policy note on the brief's numbers: the brief quotes "~243 slots expected for
N=704, S=394". Formula (1) gives 704*(1 - exp(-394/704)) = 301.9, not 243,
and "~404" for N=12032, S=394 gives 12032*(1 - exp(-394/12032)) = 387.6.
The law in the brief ("solve properly and document the formula you use") wins:
this report and the calculator use (1), (2), (3) as written above.

Verdict rule (both gates must pass, `capture-sufficiency.py:118` evaluate):
- C1 coupon gate: S >= S_req(base_n, target) with p configurable via
  `--target` (default 0.95). Fail means an empty slot is the uniform
  expectation and a cold-tail finding is inseparable from undersampling.
- C2 integrity: observed occupied <= E[occupied] + 1.96*SD over the captured
  window (the capture must not claim more coverage than S draws can produce
  under the null; it catches count bugs, top-k mismatches and duplicated
  rows). Occupancy BELOW the band is reported as a note (concentrated routing
  or an open window), not as a verdict driver.

N is the real model topology, not the slice: `--base-n` defaults to 12032 =
Flint's 47 MoE layers x 256 experts (`capture-sufficiency.py:44`), so a 6%
slice is judged against the whole mesh.

## 2. Exact output on the reject case

Command:

    python docs/daavfx/auditor-ISAYY/batch1/capture-sufficiency.py \
      scripts/daavfx/results/flint/router-q2xl-initial.csv

Output (exit code 1):

    == capture-sufficiency certificate (daavfx/capture-sufficiency/v1) ==
    source           : F:\DAAVILE_ECOSYSTEM\trading_ecosystem_11\trading_ecosystem_9.0\shared\llama.cpp-abelianIUT\scripts\daavfx\results\flint\router-q2xl-initial.csv
    slots in csv     : 704 (22 layers, span 2..23, [32] experts/layer)
    model topology   : N = 12032 slots (capture covers 5.85% of topology)
    selections       : S = 394 recorded routing decisions (rows carry routed_tokens=[8960])
    observed occupied: 209 of 704 slots (29.69%)
    -- uniform null (coupon math) --
    capture window N=704: E[occupied]=301.9 sd=6.6 ci95=[288.9, 314.9] fill z=-14.04
    full topology  N=12032: E[occupied]=387.6 sd=2.5 ci95=[382.8, 392.5]
    target occupancy: 95% -> S_req=36045 (=-N*ln(1-p), p=95%, N=12032)
    selection ratio : S/S_req = 1.09% (394 present vs 36045 needed)
    full collection : ~126006 selections to touch every slot once; P[zero empty at S]=0.000e+00
    -- verdict --
    C1 coupon gate (S >= S_req)          : False
    C2 integrity (occupancy <= 95% upper): True
    VERDICT: INSUFFICIENT-CAPTURE
      reason: coupon gate: S=394 selections vs S_req=36045 (=-N*ln(1-p), p=95%, N=12032); at this S an empty slot is the uniform expectation (E[occupied]=387.6+/-4.8 over the full topology), so a cold-tail finding cannot be separated from plain undersampling
      note: info: observed occupied=209 is below the uniform 95% lower bound 288.9 for the captured window; routing is concentrated or the window is open - inconclusive at this S, which is itself a reason to recapture
    policy: no X-ray verdict without an admissible capture certificate

Ground truth of the input file, read with Import-Csv (705 lines = 1 header +
704 data rows, `router-q2xl-initial.csv:1` for the header): layers 2..23 (22
distinct values), 32 experts per layer, sum(selected) = 394, rows with
selected > 0 = 209, tokens = 8960 on every row. The calculator derives all of
these from the CSV itself (`capture-sufficiency.py:49` capture_read); the only
external input is N via `--base-n` (`capture-sufficiency.py:284`).

The criterion is met: the 394-selection, 5.85%-of-topology capture is
classified INSUFFICIENT-CAPTURE for a cold-tail verdict. The original "cold
tail - surgery is live" verdict stays rejected, and now with a machine-checkable
reason instead of an argument.

Positive control (so the tool cannot be accused of always rejecting): a
synthetic 47x256 histogram with S = 40000 uniform draws over 12032 slots
returns VERDICT: ADMISSIBLE (C1 and C2 both True, exit code 0; observed 11615
occupied sits inside ci95=[11561.5, 11636.5]).

## 3. The policy it encodes

**No X-ray verdict without an admissible capture certificate.** A router
histogram may be quoted as raw numbers; it may not support a structural claim
(cold tail, dead experts, surgery targets, expert-evolution trend) unless the
capture it came from passes the coupon gate for the model's true topology. The
certificate transports the verdict, the criteria results and the reasons, so a
reviewer re-checks the decision without re-deriving it. The verdict string is
printed by `capture-sufficiency.py:272` and embedded in the JSON at
`capture-sufficiency.py:230`.

## 4. How the router logger should emit the certificate at capture time

1. Always write the full CSV schema (layer,expert,selected,mass_selected,
   mass_all,tokens) with one row per slot, including zero rows; the calculator
   rejects duplicate slots and zero-selection captures (`capture-sufficiency.py:63`,
   `capture-sufficiency.py:302`).
2. Run the calculator on the fresh file at capture time with the model's real
   N (`--target 0.95`, or the target of the verdict being prepared) and
   `--emit cert.json` beside the CSV (`capture-sufficiency.py:288`). Exit
   code 1 = INSUFFICIENT-CAPTURE must block the X-ray report build; exit
   code 0 = ADMISSIBLE is the only certificate worth attaching
   (`capture-sufficiency.py:326`).
3. Emit-verbatim JSON schema `daavfx/capture-sufficiency/v1`
   (`capture-sufficiency.py:162` build_certificate): source_csv, capture block
   (slots, layers, selections_total, observed_occupied, routed_tokens),
   model_topology (base_slots_n, capture_share_of_topology), uniform_null
   (per-window E[occupied], sd, ci95, fill_z), requirement (occupancy_target,
   selections_required, selection_headroom, full_coupon_selections_est),
   decision (verdict, per-criterion booleans, reasons, notes, policy), and
   per_layer detail so a reviewer can audit one layer without rerunning.
4. When S_req exceeds available selections, the logger must say how many more
   decisions are needed (S_req - S, and for full coverage ~N*ln(N)); recapture
   is the remedy, not a weaker verdict on the same file.
5. Record the occupied-count fill z per run: a large negative z means the
   capture window is open or routing is concentrated, and both make the same
   capture useless for extrapolation - recapture with a closed window.

ASCII only. Stdlib only. Exit codes: 0 ADMISSIBLE, 1 INSUFFICIENT-CAPTURE,
2 usage/parse error.
