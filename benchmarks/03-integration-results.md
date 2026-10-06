# 03 - Integrate: RAG pipeline run

Host `Windows-AMD64` · llama.cpp `b10488` ·
retrieval backend: **keyword overlap** · 3 queries

| Query | Contexts retrieved | embed (ms) | retrieve (ms) | llm (ms) | total (ms) |
|:--|--:|--:|--:|--:|--:|
| Why is goodput more useful than raw throughp... | goodput, paged, radix | 0.0 | 0.0 | 3766.3 | 3766.4 |
| What problem does PagedAttention actually so... | paged, radix, disagg | 0.0 | 0.1 | 3959.7 | 3959.8 |
| When does splitting prefill and decode help?... | disagg, radix, batching | 0.0 | 0.1 | 5221.3 | 5221.4 |

Mean per stage (ms): embed **0.0** · retrieve **0.1** ·
llm **4315.8** · total **4315.9**
Dominant stage: **llm** (100% of total)

## Answers returned

**Why is goodput more useful than raw throughput?**

> Based on the provided context, **Goodput** is more useful than raw throughput because it focuses on **slops (Service Level Objects)** rather than ignoring them.

The text explicitly states:
> "Goodput@SLO counts only the requests per second that met the TTFT and TPOT targets."

In contrast, the context notes that throughput at saturation ignores SLOs. Since Goodput specifically tracks requests mee

**What problem does PagedAttention actually solve?**

> PagedAttention solves the problem of **internal fragmentation** in GPU memory.

By storing the Key-Value (KV) cache in non-contiguous pages, it avoids the wasted space that would occur if the cache were stored contiguously in contiguous memory blocks. This allows the engine to utilize more of the available GPU memory for tasks that are not strictly bound by memory bandwidth, such as the decoding p

**When does splitting prefill and decode help?**

> Splitting prefill and decode helps when the **prefill step is compute-bound** (requires significant CPU/GPU processing) and the **decode step is memory-bandwidth-bound** (requires significant memory throughput), but the total cost of running both steps together is too high due to the overhead of the prefill step.

By separating them, the system can prioritize the compute-bound prefill step, which 


## Phần nào của N16–N19 là real (nhận xét của tôi)

| Day | Piece | Real hay stub |
|--|--|--|
| N16 Cloud/IaC | chạy trên localhost, không có cluster hay Compose | **stub** |
| N17 Data pipeline | corpus là list `TOY_DOCS` viết sẵn trong code | **stub** |
| N18 Lakehouse | dict Python thay cho Delta/Iceberg | **stub** |
| N19 Vector + features | keyword overlap, không có embedding (`embed` = 0.0 ms) | **stub** |
| N20 Serving | `llama-server` b10488, Qwen3.5-0.8B Q4_K_M, CPU | **real** |

**Dominant stage là llm, chiếm 100%** (trung bình 4315.8 ms; retrieve 0.1 ms). Điều này đúng như
tôi kỳ vọng, vì retrieve chỉ so khớp từ trên 6 tài liệu.

**Điều bất ngờ nằm bên trong stage "llm".** Lần chạy đầu dùng `--base-url` mặc định
`http://localhost:8080` (`03-integration-results-localhost.md`). Ở lần đó llm trung bình là
**5892.9 ms**, trong khi server chỉ báo prefill + decode khoảng 2.2–4.8 s. Khoảng **2.4 s mỗi
request là thời gian kết nối**. Windows phân giải `localhost` thành `::1` trước, nhưng
llama-server chỉ nghe trên 127.0.0.1. Kết nối IPv6 bị từ chối, Windows chờ khoảng 2 s rồi mới
thử IPv4. Tôi đo riêng: `httpx.get` tới `localhost` mất 2260 ms, tới `127.0.0.1` mất 187 ms. Khi
chạy lại với `--base-url http://127.0.0.1:8080`, overhead (llm − prefill − decode) giảm từ
2.35–2.49 s xuống còn 0.28–0.56 s.

Phần thời gian LLM còn lại chủ yếu là **decode**. Ví dụ ở query 1: decode 3402 ms, prefill chỉ
82 ms. Ở lần chạy thứ hai, prefill chỉ còn 4 token, vì prompt cache của llama-server dùng lại
prefix giống hệt từ lần chạy trước.

**Muốn giảm latency 2×, tôi sẽ:**

1. Gọi `127.0.0.1` và dùng kết nối keep-alive. Đã làm: 5.89 → 4.32 s.
2. Cắt số token decode. Câu trả lời đang dài 68–156 token (qua hai lần chạy) với `max_tokens` 200. Yêu cầu trả lời
   ngắn (≤ 60 token) sẽ cắt decode khoảng 2×, vì decode bị chặn bởi băng thông và TPOT gần như cố
   định ở khoảng 25–36 ms/token.
3. Nếu vẫn cần nhanh hơn, đưa decode lên GPU.
