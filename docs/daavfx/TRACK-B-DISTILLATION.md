# TRACK-B-DISTILLATION - teacher to small local agent

Date: 2026-10-22
Status: PLAN ONLY. No data collection, training, or evaluation has run.
Teacher is not selected yet: it must first pass the MT5 task.

## 1. Goal

Turn the winning large local model (Flint, or the best small model if Flint
fails) into a small, fast, local tool agent for the MT5 backtest workflow.

Target deployment:

- GTX 1650 4 GB box, GGUF Q4/Q5, 2B-class model.
- Oracle micro only as a gateway or embedding host, never as the model host.
- The agent must drive the same MCP tools, not a new API.

Success is not "sounds good". Success is:

1. Full MT5 task completion with the sealed values within tolerance.
2. Tool-call argument accuracy at or above the teacher on held-out tasks.
3. Fewer or equal turns than the teacher for the same task.
4. Runs on the 4 GB card at a usable speed.

## 2. Teacher selection

Do not start until one model passes the MT5 gate.

| Candidate | Role | Condition |
|---|---|---|
| Flint Q3_K_XL / IQ4_XS | primary teacher if it passes MT5 | Preferred: 39.8B total, strong agentic scores |
| qwen3.5-4b | fallback teacher | Current full verified MT5 card |
| Flint Q2_K_XL | speed reference only | Not a teacher if quality fails |

The teacher must run at the on-spec sampling and the exact harness v1.3 tool
catalog. A teacher that only works at a different sampling regime is not a
clean distillation source.

## 3. Data contract

Collect trajectories, not chat logs. Each record must contain:

- task id, task family, and a hash of the prompt
- full message list, including system and tool schema version
- every assistant reasoning block (kept separate from content)
- every tool call: name, JSON arguments, raw text fallback
- every tool result: success, error, latency, and truncated payload
- final answer and the programmatic verifier result
- sampling parameters, model, quant, binary commit
- turn count, token counts, wall clock

Freeze the tool catalog and schema before collection. If the catalog changes,
version it and recollect; do not mix schema versions in one training set.

Storage: JSONL, one trajectory per line, plus a manifest with the exact
teacher build and task set.

## 4. Data collection

Sources, in order:

1. The 12-task quality harness, multiple seeds and sampling runs.
2. The full MT5 task, repeated with different seeds.
3. Agent prompts from the benchmark suite, including tool-error recovery.
4. Synthetic variants of the 12 tasks that change symbols, dates, setfiles,
   and failure modes, generated only from the frozen schema.

Target volume, to be confirmed after the first collection:

- 300-1000 successful full trajectories.
- 2,000-5,000 individual tool-call examples extracted from them.
- A held-out set of 20-30 percent of task families, never trained on.

Do not train on the sealed MT5 answer text. The verifier values can be used as
labels, but the prompt must not contain them.

## 5. Curation

Keep:

- trajectories with a verified success and no schema violation
- recoveries from a tool error that end in success
- long-horizon runs with a clean tool sequence

Drop:

- truncated runs, empty turns, and reasoning-budget failures
- runs with wrong `run_backtest` arguments, even if the final text is plausible
- duplicated prompts and near-duplicates
- any run that used a different tool schema

Balance task families. A dataset that is 90 percent `list_directory` teaches
the student to list directories, not to backtest.

## 6. Student candidates

| Student | Params | Local fit | Notes |
|---|---|---|---|
| qwen3.5-2b | 2B | Q4 on 4 GB card | First training target |
| qwen3.5-4b | 4B | Q4 tight on 4 GB | Train only with a larger GPU or A1 free |
| LFM2.5-1.2B | 1.2B | CPU or 4 GB card | Edge fallback; check tool-call temperament |

Do not start with the 4B on the 1650. QLoRA on a 4B model needs more VRAM than
the card has once activations and sequence length are counted. Train the 2B
first, prove the data pipeline, then scale.

## 7. Training recipe

Baseline QLoRA:

- 4-bit NF4 base, double quant, bfloat16 compute where supported
- LoRA rank 16-32, alpha 32, dropout 0.05
- target all linear projections, including the MLP and attention output
- learning rate 1e-4 to 2e-4, cosine schedule, warmup 3 percent
- 2-3 epochs, early stop on held-out loss
- sequence length 8192 for the first pass; 4096 if memory fails
- gradient checkpointing on
- pack short examples, mask tool-result tokens from the loss
- train on assistant tokens only: reasoning, tool call, and final answer

Do not mask the tool call itself. The student must learn the JSON arguments.

Optional second stage:

- DPO or ORPO on success/failure pairs from the same tasks, only after SFT
  produces valid tool calls.
- Rejection sampling with the teacher as the judge, capped to avoid teacher
  bias.

## 8. Evaluation

Three gates:

1. Tool-call accuracy: exact function name plus JSON arguments on held-out
   tasks. Target at or above the teacher.
2. Quality harness: 12 tasks, same scorer, three seeds. Target at least 80
   percent of the teacher's score, with no silent wrongness.
3. MT5 task: full run, sealed values within tolerance, no wrong
   `run_backtest` call.

Report per-family results, not only the aggregate. A student that passes easy
tasks and fails the MT5 task is not shippable.

Also measure:

- turns to completion
- wall clock per task
- tool errors per run
- reasoning length
- tokens per second on the 1650

## 9. Deployment

1. Merge LoRA, convert to GGUF, quantize Q4_K_M and Q5_K_M.
2. Run `llama-server` with the same tool catalog and Jinja template.
3. Point the harness at the local server; do not change the driver.
4. Keep the teacher command and the student command in the same scorecard.
5. Package the winner with `launch-llm.ps1` or a dedicated launcher.

The Oracle micros stay on gateway, embedding, and puller duty. A 1 GB micro
cannot host a 2B model.

## 10. Risks

| Risk | Mitigation |
|---|---|
| Teacher never passes MT5 | Do not start Track B; use the current small-model winner or fix the teacher |
| 12-task overfit | Hold out entire task families; add synthetic variants |
| Schema drift | Freeze and version the tool catalog; recollect on change |
| Sealed-answer leakage | Never put ground-truth values in prompts |
| Reasoning leakage | Keep reasoning separate; train on it only if the student has a reasoning channel |
| 4 GB training wall | 2B QLoRA first; rent or wait for a larger GPU for 4B |
| Teacher bias | Evaluate on programmatic verifiers, not teacher preference |
| License | Flint Apache-2.0; check the student license before redistribution |

## 11. Phase plan

| Phase | Work | Gate |
|---|---|---|
| B0 | Freeze schema, write collector, verify one trajectory round-trips | Schema test passes |
| B1 | Collect teacher data after MT5 pass | At least 300 successful trajectories |
| B2 | Curate and split by task family | No leakage, balanced families |
| B3 | Train 2B QLoRA | Held-out loss falls, valid tool calls |
| B4 | Evaluate 2B | Tool accuracy and quality gates |
| B5 | Quantize and deploy 2B | Runs on 4 GB card, MT5 pass |
| B6 | Scale to 4B or LFM if needed | Only with a larger training GPU |

## 12. Artifacts

- Raw trajectories: `llm_bench\distill\raw\`
- Curated dataset: `llm_bench\distill\curated\`
- Training config: `llm_bench\distill\config\`
- Adapters: `llm_bench\distill\adapters\`
- Merged and quantized: `...\local_llm\GGUF\llm-collection\22-distilled\`
- Eval: `llm_bench\distill\eval\`
- Scorecard: `docs\daavfx\moe-lab\TRACK-B-RESULTS.md` after data exists

## 13. Open decisions

1. Teacher: Flint or the current qwen3.5-4b winner.
2. Student: qwen3.5-2b first, or LFM2.5-1.2B for CPU-only.
3. Training host: local 1650 for 2B only, or a rented 12-16 GB GPU for 4B.
4. Whether reasoning traces are trained or only used for tool-call extraction.
5. Minimum MT5 pass rate before shipping: 100 percent or a documented failure
   budget.
