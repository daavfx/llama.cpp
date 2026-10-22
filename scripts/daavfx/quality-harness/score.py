#!/usr/bin/env python3
# score.py - deterministic scorer for the FOUNDRY quality-budget harness.
# stdlib only. Reads taskset.json + a responses jsonl, emits score jsonl and
# prints a summary. Pass rate is the destruction-budget number.

import argparse
import json
import re
import sys
import os


def first_json_block(text):
    m = re.search(r"\{.*?\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def run_check(check, text):
    t = check["type"]
    if t == "json_valid_first_block":
        obj = first_json_block(text)
        return obj is not None and isinstance(obj, dict)
    if t == "json_has_keys":
        obj = first_json_block(text)
        return obj is not None and all(k in obj for k in check["keys"])
    if t == "json_tags_is_array":
        obj = first_json_block(text)
        return obj is not None and isinstance(obj.get("tags"), list)
    if t == "contains":
        return check["text"].lower() in text.lower()
    if t == "not_contains":
        return check["text"].lower() not in text.lower()
    if t == "regex":
        return re.search(check["pattern"], text) is not None
    if t == "word_count_range":
        n = len(text.split())
        return check["min"] <= n <= check["max"]
    raise ValueError(f"unknown check type {t}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", required=True)
    ap.add_argument("--taskset", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "taskset.json"))
    ap.add_argument("--out", default=None, help="score jsonl out path (default: alongside responses)")
    args = ap.parse_args()

    with open(args.taskset, "r", encoding="utf-8") as f:
        tasks = {t["id"]: t for t in json.load(f)["tasks"]}

    rows = []
    raw = open(args.responses, "rb").read()
    text = None
    for enc in ("utf-8-sig", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = raw.decode("utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    out_path = args.out or args.responses.replace("responses-", "score-")
    total_checks = 0
    total_pass = 0
    with open(out_path, "w", encoding="utf-8") as f:
        print(f"{'task':<26} {'task_ok':<8} checks")
        for r in rows:
            t = tasks.get(r["id"])
            if t is None:
                continue
            results = []
            task_ok = r.get("ok", False)
            if task_ok:
                for c in t["checks"]:
                    ok = run_check(c, r.get("response", ""))
                    results.append((c.get("label", c["type"]), ok))
                    total_checks += 1
                    total_pass += 1 if ok else 0
                task_ok = all(ok for _, ok in results)
            row = {"tag": r["tag"], "id": r["id"], "task_ok": task_ok, "checks": results}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            marks = ",".join("+" if ok else "-" for _, ok in results)
            print(f"{r['id']:<26} {'PASS' if task_ok else 'FAIL':<8} {marks}")

    n_tasks = len(rows)
    n_ok = sum(1 for r in rows if r["id"] in tasks and
               all(run_check(c, r.get("response", "")) for c in tasks[r["id"]]["checks"])
               and r.get("ok", False))
    print()
    print(f"tasks: {n_ok}/{n_tasks} pass  ({100.0 * n_ok / n_tasks:.1f}% task rate)" if n_tasks else "no rows")
    print(f"checks: {total_pass}/{total_checks}  ({100.0 * total_pass / max(total_checks,1):.1f}%)")
    print(f"score file: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
