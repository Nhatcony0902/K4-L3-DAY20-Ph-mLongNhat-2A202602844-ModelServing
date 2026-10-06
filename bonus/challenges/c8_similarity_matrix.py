#!/usr/bin/env python3
"""BONUS C8 - Why no single threshold works: the full similarity distribution.

semantic-cache-demo.py only prints each prompt's best match against what is already
cached, so it shows symptoms. This scores EVERY pair of prompts with the lab's
embedding server (chat model in mean-pooling mode), labels each pair as a true
paraphrase or unrelated, and sweeps the threshold to count false hits and false
misses at each value. If the two distributions overlap, no threshold fixes both.

    make serve-embed     # :8081
    .venv/bin/python bonus/challenges/c8_similarity_matrix.py
"""
from __future__ import annotations

import itertools
import json
import pathlib
import sys

import httpx
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import labkit  # noqa: E402

# Same 8-prompt stream as semantic-cache-demo.py, plus three prompts from far-away topics.
PROMPTS = [
    "What is goodput at SLO?",                 # 1  topic A
    "Explain TTFT and TPOT.",                  # 2  topic B
    "Can you define goodput@SLO?",             # 3  A
    "What does time to first token mean?",     # 4  B
    "How does PagedAttention work?",           # 5  C
    "Tell me what goodput@SLO is.",            # 6  A
    "What is prefix caching?",                 # 7  D (new topic)
    "Describe how PagedAttention works.",      # 8  C
    "What is the capital of France?",          # 9  E (unrelated)
    "Give me a recipe for banana pancakes.",   # 10 F (unrelated)
    "How do I renew my passport?",             # 11 G (unrelated)
]
TOPIC = ["A", "B", "A", "B", "C", "A", "D", "C", "E", "F", "G"]
THRESHOLDS = [0.80, 0.85, 0.88, 0.90, 0.92, 0.95]


def embed(texts: list[str], url: str) -> np.ndarray:
    r = httpx.post(f"{url}/v1/embeddings", json={"model": "local", "input": texts}, timeout=120)
    r.raise_for_status()
    vecs = []
    for d in r.json()["data"]:
        a = np.asarray(d["embedding"], dtype=float)
        vecs.append(a.mean(axis=0) if a.ndim == 2 else a)
    m = np.vstack(vecs)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def main() -> int:
    url = f"http://127.0.0.1:{labkit.embed_port()}"
    vecs = embed(PROMPTS, url)
    sim = vecs @ vecs.T
    pairs = []
    for i, j in itertools.combinations(range(len(PROMPTS)), 2):
        pairs.append({"i": i + 1, "j": j + 1, "sim": round(float(sim[i, j]), 4),
                      "paraphrase": TOPIC[i] == TOPIC[j]})
    para = sorted((p for p in pairs if p["paraphrase"]), key=lambda p: p["sim"])
    unrel = sorted((p for p in pairs if not p["paraphrase"]), key=lambda p: -p["sim"])

    md = ["# Bonus C8 - Semantic cache: similarity diagnosis", "",
          f"Embedder: `llama-server --embedding --pooling mean` on "
          f"`{labkit.load_active()['primary_model']}` (a chat model, not an embedding model) · "
          f"llama.cpp `{labkit.LLAMA_CPP_BUILD}`", "",
          "## Prompts", "", "| # | topic | prompt |", "|--:|:--|:--|"]
    md += [f"| {k + 1} | {TOPIC[k]} | {p} |" for k, p in enumerate(PROMPTS)]
    md += ["", "## Cosine similarity matrix", "",
           "| | " + " | ".join(str(k + 1) for k in range(len(PROMPTS))) + " |",
           "|--:|" + "--:|" * len(PROMPTS)]
    for a in range(len(PROMPTS)):
        md.append(f"| **{a + 1}** | " + " | ".join(f"{sim[a, b]:.2f}" for b in range(len(PROMPTS))) + " |")
    md += ["", "## The two distributions", "",
           f"- True paraphrase pairs ({len(para)}): "
           + ", ".join(f"{p['i']}-{p['j']} = {p['sim']:.3f}" for p in para),
           f"- Lowest-scoring true paraphrase: **{para[0]['i']}-{para[0]['j']} = {para[0]['sim']:.3f}**",
           f"- Highest-scoring unrelated pairs: "
           + ", ".join(f"{p['i']}-{p['j']} = {p['sim']:.3f}" for p in unrel[:5]),
           f"- Highest-scoring unrelated pair: **{unrel[0]['i']}-{unrel[0]['j']} = {unrel[0]['sim']:.3f}**",
           "", "## Threshold sweep over all pairs", "",
           "| threshold | false hits (unrelated pairs >= t) | false misses (paraphrase pairs < t) |",
           "|--:|--:|--:|"]
    for t in THRESHOLDS:
        fh = sum(p["sim"] >= t for p in unrel)
        fm = sum(p["sim"] < t for p in para)
        md.append(f"| {t:.2f} | {fh} / {len(unrel)} | {fm} / {len(para)} |")
    md += ["", "## Diagnosis (required -- replace this line)", ""]

    out = labkit.repo_root() / "benchmarks" / "bonus-c8-semantic-cache.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps({"prompts": PROMPTS, "topic": TOPIC,
                                                    "pairs": pairs}, indent=2), encoding="utf-8")
    print("\n".join(md))
    print(f"\n==> Wrote {out.relative_to(labkit.repo_root())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
