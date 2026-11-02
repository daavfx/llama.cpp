# BREAK1650 - the GTX 1650 program: context, facts, and the full plan

**Auditor brief: this folder is self-contained.** You have this folder and
nothing else. Everything you need to judge the plan is inside these files.
External paths are given only as optional deep-reads for the human operator;
where a fact matters, the number and its provenance are inlined here.

---

## What this program is

A staged engineering program to maximize LLM decode and load speed on one
specific machine (a Ryzen 5 5600G + GTX 1650 4GB + Vega 7 iGPU + 32 GB DDR4
desktop), culminating in the "2x" question: can this box double its measured
throughput (18.9 t/s CPU-split baseline on an 8B MoE; 74.77 t/s on a 0.5B
dense GPU-resident) through software alone?

The program was born from three convergences:

1. A measured hardware datasheet (E0, 2026-10-24) that established the card's
   real ceilings: PCIe copy 13.3 GB/s, FP16 FMA 3.2 TFLOPS achieved (~53% of
   ~6 TFLOP theoretical), host-visible in-shader read 1.4 GB/s on the dGPU
   vs 4.8 GB/s on the iGPU, dispatch 178/50 ns.
2. A storage audit that found the models live on a 7200rpm SATA HDD
   (F:) while an NVMe (C:) with 35.6 GB free sits nearly idle. Measured:
   4K random QD1 ~12 ms/op on F: vs ~0.28 ms on C: (~40x).
3. A four-agent audit of the operator's own research archive
   (`local_llm\GGUF\RYIUK`, 8933 files) which produced a trust ledger:
   17 claims VERIFIED, 13 FALSIFIED with death receipts, 14 UNVERIFIED but
   testable - and discovered the operator's own matured design notes
   (PROJECT KITTYHAWK / `kimi_k3_aproach.md`) that independently converge
   with this program's arithmetic.

## Reading order

| File | What |
|---|---|
| `README.md` | this file - the brief |
| `00-CONTEXT.md` | hardware, software stack, lanes, standing rules, what is correlated elsewhere |
| `01-MEASURED-FACTS.md` | every number with provenance (E0, storage, campaign, archive-verified) |
| `02-TRUST-LEDGER.md` | the claim classification (16 verified / 13 falsified / 14 testable), copied in full |
| `03-THE-PLAN.md` | P0-P4: the full program with gates and falsifiable hypotheses |
| `04-LOADER-DEEP-DIVE.md` | the model-loading redesign - from stock mmap to an LLM-era layout compiler (the operator's explicit priority) |
| `05-EXPERIMENTS.md` | the executable experiment list: hypothesis, one settling test, cost, gate, owner |
| `TASK-REGISTER.md` | every open task, its lane, gate, and window order - the single place to see what is next (includes the STOPPED-now state and the G-1..G-4 candidates) |
| `08-THINKING-DEEP-DIVE.md` | the reasoning-token tax: measured proof (77% of generation on this box), the CoT/test-time-compute mechanism, the field's levers, and our P1 plan |
| `09-COT-RESEARCH/` | the chain-of-thought deep research: 6 sourced papers/reports, our mechanics, the duplication question answered, and the reuse-first plan |
| `06-PRIOR-RUNS.md` | digest of all past runs and benchmarks (LFM campaign, MT5 agent bench, Flint state, RYIUK archive) |
| `07-CORRELATED-LANES.md` | what the other agents/lanes are cooking and what must not be touched |

## The one-paragraph thesis

On this box the enemy is **bytes moved per token**, not FLOPS: decode at
18.9 t/s on an 8B MoE uses ~94 GFLOPS (trivial) while streaming ~0.54 GB of
expert weights per token from a 7200rpm HDD-class store (brutal) - the 0.54
is the measured pair (`05-EXPERIMENTS.md` EXP-3: 10.2 GB/s at 18.9 t/s);
the 0.85 this paragraph used to carry was 58% high and unreconciled. Every
lever in this program either **shrinks bytes** (precision depth-map, expert
surgery when the hot set is real), **hides bytes** (copy-stream staging
rings, router-guided prefetch, concurrent theater reads), or **moves bytes
faster** (drive-aware io_engine, NVMe-resident working set, co-activation
cluster layouts). The compute side (kernels) matters for prefill - where
the measured disaster is 0.14-0.39 t/s - and for the dense speed lane.

## Standing rules (binding on every experiment)

1. **Nothing local runs without the operator's explicit green light, every
   time** - including llama-server, benches, and probes. This rule was
   earned the hard way (a PC-slowdown incident on 2026-10-23).
2. Every claim moves between evidence classes only by an instrument run
   recorded with a command line and binary identity - never by argument.
3. One falsifiable hypothesis per experiment; the result lands in the
   ledger either way (see `02-TRUST-LEDGER.md` for the classes).
4. Kills are clean: no orphan llama-servers, python scorers, or launchers;
   the operator's own processes are never touched.
5. ASCII only in all files; commits end with `Work-Note: <agent-id>` +
   `Assisted-by:`; no pushes without the operator.
