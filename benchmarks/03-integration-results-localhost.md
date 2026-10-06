# 03 - Integrate: RAG pipeline run

Host `Windows-AMD64` · llama.cpp `b10488` ·
retrieval backend: **keyword overlap** · 3 queries

| Query | Contexts retrieved | embed (ms) | retrieve (ms) | llm (ms) | total (ms) |
|:--|--:|--:|--:|--:|--:|
| Why is goodput more useful than raw throughp... | goodput, paged, radix | 0.0 | 0.0 | 7124.8 | 7124.9 |
| What problem does PagedAttention actually so... | paged, radix, disagg | 0.0 | 0.1 | 4671.6 | 4671.7 |
| When does splitting prefill and decode help?... | disagg, radix, batching | 0.0 | 0.1 | 5882.4 | 5882.5 |

Mean per stage (ms): embed **0.0** · retrieve **0.1** ·
llm **5892.9** · total **5893.0**
Dominant stage: **llm** (100% of total)

## Answers returned

**Why is goodput more useful than raw throughput?**

> Based on the provided context, **Goodput** is more useful than raw throughput for the following reasons:

*   **SLO Compliance:** Goodput counts only requests per second that met the Target Time-to-Fill (TTFT) and Target Time-to-Poll (TPOT) targets. In contrast, raw throughput ignores SLOs (specifically throughput at saturation).
*   **Resource Utilization:** Goodput ensures that the system does n

**What problem does PagedAttention actually solve?**

> PagedAttention solves the problem of **internal fragmentation in GPU memory** caused by storing the Key-Value (KV) cache in non-contiguous pages.

By organizing the KV cache into non-contiguous pages, the model avoids wasting most of the GPU's memory capacity on unused memory regions, thereby improving memory efficiency and reducing latency.

**When does splitting prefill and decode help?**

> Based on the provided context, splitting prefill and decode helps when **prefill is compute-bound and decode is memory-bandwidth-bound**.

The context explains that this specific split is beneficial because:
1.  **Prefill** is compute-bound, meaning it requires significant processing power.
2.  **Decode** is memory-bandwidth-bound, meaning it requires significant data transfer speed.
3.  By separa


## Ghi chú: lần chạy qua localhost (nhận xét của tôi)

Đây là lần chạy `make pipeline` đầu tiên, dùng `--base-url` mặc định `http://localhost:8080`.
Tôi giữ file này làm bằng chứng cho khoảng **2.4 s overhead mỗi request**. Overhead đến từ việc
Windows thử IPv6 `::1` trước, trong khi llama-server chỉ nghe trên 127.0.0.1.

So sánh llm − (prefill + decode) theo số liệu server báo:

| Query | localhost | 127.0.0.1 |
|--|--:|--:|
| 1 | 7124.8 − 4777 = 2348 ms | 3766.3 − 3484 = 282 ms |
| 2 | 4671.6 − 2183 = 2489 ms | 3959.7 − 3461 = 499 ms |
| 3 | 5882.4 − 3401 = 2481 ms | 5221.3 − 4666 = 555 ms |

Phân loại N16–N19 (real/stub) và nhận xét đầy đủ nằm trong `03-integration-results.md`. Tóm tắt:
N16–N19 đều là stub, chỉ N20 (`llama-server`) là real, và llm chiếm 100% latency.
