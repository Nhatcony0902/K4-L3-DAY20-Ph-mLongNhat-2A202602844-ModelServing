#!/usr/bin/env python3
"""BONUS C2 - KV cache quantization: f16 vs q8_0 vs q4_0.

For each KV cache type, starts llama-server with a large context, then measures:
  - KV cache size, as reported by llama-server's own load log
  - process memory (private bytes) after load and after a long prompt
  - TTFT / TPOT on a ~4.8k-token prompt
  - quality: 10 needle-in-a-haystack questions, graded automatically

The long prompt matters: with a 20-token prompt the KV cache barely holds anything,
so quantizing it cannot change the answer. Ten facts buried in filler text force the
model to attend back across thousands of cached tokens.

    .venv/bin/python bonus/challenges/c2_kv_cache_quant.py
"""
from __future__ import annotations

import json
import pathlib
import random
import re
import subprocess
import sys
import time

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import labkit  # noqa: E402

PORT = 8095
CTX = 32768
CACHE_TYPES = ["f16", "q8_0", "q4_0"]

FACTS = [
    ("the blue warehouse", "4821"), ("the night shift manager", "7395"),
    ("locker 12", "2064"), ("the red bicycle", "5537"), ("the garden gate", "9182"),
    ("the server room", "3476"), ("the old piano", "6609"), ("the library safe", "1748"),
    ("the rooftop door", "8253"), ("the boat shed", "4930"),
]
FILLER = [
    "The committee reviewed the quarterly logistics report and noted minor delays.",
    "Weather in the coastal region stayed mild for most of the week.",
    "Several volunteers repainted the community hall before the festival.",
    "The bakery on the corner introduced a new rye loaf that sold out quickly.",
    "Traffic on the northern bridge was diverted during routine maintenance.",
    "A local choir rehearsed twice a week in preparation for the winter concert.",
]


def build_document(seed: int = 7, filler_per_fact: int = 32) -> str:
    rng = random.Random(seed)
    parts = []
    for subject, code in FACTS:
        parts += [rng.choice(FILLER) for _ in range(filler_per_fact)]
        parts.append(f"Note: the access code for {subject} is {code}.")
    parts += [rng.choice(FILLER) for _ in range(filler_per_fact)]
    return " ".join(parts)


def private_mb(pid: int) -> float:
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"(Get-Process -Id {pid}).PrivateMemorySize64"],
        capture_output=True, text=True, check=False).stdout.strip()
    return int(out) / 2**20 if out.isdigit() else float("nan")


def kv_size_from_log(log: str) -> str:
    sizes = re.findall(r"llama_kv_cache: size =\s*([\d.]+) MiB", log)
    return f"{sum(float(s) for s in sizes):.1f}" if sizes else "n/a"


def ask(doc: str, question: str) -> dict:
    t0 = time.perf_counter()
    r = httpx.post(f"http://127.0.0.1:{PORT}/v1/chat/completions", timeout=600, json={
        "model": "local", "temperature": 0, "max_tokens": 16,
        "messages": [{"role": "user", "content":
                      f"{doc}\n\nQuestion: {question} Answer with only the 4-digit code."}],
    })
    r.raise_for_status()
    body = r.json()
    return {"answer": body["choices"][0]["message"]["content"].strip(),
            "wall_ms": (time.perf_counter() - t0) * 1000.0,
            "timings": body.get("timings") or {}}


def run(cache_type: str, doc: str) -> dict:
    model = labkit.repo_root() / labkit.load_active()["primary_model"]
    cmd = [str(labkit.runtime_bin("llama-server")), "-m", str(model),
           "--host", "127.0.0.1", "--port", str(PORT), "-t", str(labkit.threads()),
           "-ngl", "0", "--ctx-size", str(CTX), "--parallel", "1",
           "--reasoning", "off", "-fa", "on", "-lv", "4",  # -lv 4 logs the KV size
           "--cache-type-k", cache_type, "--cache-type-v", cache_type]
    log_path = labkit.repo_root() / "benchmarks" / ".llama-server.log"
    with open(log_path, "w") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        try:
            if not labkit.wait_healthy(PORT, proc=proc):
                raise SystemExit(f"server failed for {cache_type}:\n{log_path.read_text()[-2000:]}")
            mem_loaded = private_mb(proc.pid)
            results = []
            for i, (subject, code) in enumerate(FACTS):
                res = ask(doc, f"What is the access code for {subject}?")
                res["correct"] = code in res["answer"]
                results.append(res)
                print(f"   [{cache_type}] {i + 1:2}/10  want {code}  got {res['answer']!r:12} "
                      f"{'ok' if res['correct'] else 'WRONG'}")
            mem_after = private_mb(proc.pid)
        finally:
            proc.terminate()
            proc.wait(timeout=30)
    first = results[0]["timings"]
    tpots = [r["timings"]["predicted_per_token_ms"] for r in results
             if r["timings"].get("predicted_per_token_ms")]
    return {
        "cache_type": cache_type,
        "kv_mib": kv_size_from_log(log_path.read_text(errors="replace")),
        "mem_loaded_mb": round(mem_loaded, 1),
        "mem_after_mb": round(mem_after, 1),
        "prompt_tokens": first.get("prompt_n"),
        "ttft_cold_ms": round(first.get("prompt_ms", 0), 1),
        "tpot_ms_median": round(sorted(tpots)[len(tpots) // 2], 2) if tpots else None,
        "accuracy": sum(r["correct"] for r in results),
        "answers": [r["answer"] for r in results],
    }


def main() -> int:
    doc = build_document()
    labkit.banner(f"C2 - KV cache quantization  (ctx {CTX}, parallel 1)")
    rows = [run(ct, doc) for ct in CACHE_TYPES]

    md = [
        "# Bonus C2 - KV cache quantization",
        "",
        f"Model `{labkit.load_active()['model']}` (`{labkit.load_active()['primary_quant']}`) · "
        f"host `Windows-AMD64` · llama.cpp `{labkit.LLAMA_CPP_BUILD}` · "
        f"`--ctx-size {CTX} --parallel 1 -fa on -ngl 0 -t {labkit.threads()}`",
        "",
        "Eval: one ~4.8k-token document with 10 four-digit access codes buried in filler; "
        "10 questions, temperature 0, graded by exact code match.",
        "",
        "| KV type | KV cache (MiB, server log) | Private mem after load (MB) | after eval (MB) "
        "| Prompt tok | Cold TTFT (ms) | TPOT P50 (ms) | Accuracy |",
        "|:--|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for r in rows:
        md.append(f"| {r['cache_type']} | {r['kv_mib']} | {r['mem_loaded_mb']} | {r['mem_after_mb']} "
                  f"| {r['prompt_tokens']} | {r['ttft_cold_ms']} | {r['tpot_ms_median']} "
                  f"| {r['accuracy']}/10 |")
    md += ["", "Answers per question:", ""]
    for r in rows:
        md.append(f"- `{r['cache_type']}`: {', '.join(r['answers'])}")
    md += ["", "## Analysis (required -- replace this line)", ""]
    out = labkit.repo_root() / "benchmarks" / "bonus-c2-kv-cache.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("\n".join(md))
    print(f"\n==> Wrote {out.relative_to(labkit.repo_root())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
