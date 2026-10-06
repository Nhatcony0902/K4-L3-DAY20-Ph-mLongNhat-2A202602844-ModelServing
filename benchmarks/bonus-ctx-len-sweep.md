# Bonus - Context-length sweep (prefill cost)

Host `Windows-AMD64` · llama.cpp `b10488` ·
`threads=14` `ngl=0` · RAM 15.7 GB

| Prompt tokens | Prefill (tok/s) | TTFT contribution (ms) | vs linear scaling |
|:--|--:|--:|--:|
| 256 | 342.5 | 747.4 | 1.00x |
| 1024 | 326.1 | 3139.7 | 1.05x |
| 2048 | 301.9 | 6784.2 | 1.13x |
| 4096 | 218.8 | 18719.4 | 1.57x |
| 8192 | 192.8 | 42496.2 | 1.78x |

At 8192 tokens, prefill costs **42496 ms** --
1.78x what linear scaling from the smallest point would predict. That excess
is attention's O(N^2) term becoming visible, and every millisecond of it lands in TTFT
before the user sees a single token.

Either way, this is the number to remember when someone proposes stuffing more retrieved
context into a RAG prompt "because the context window allows it". Prefill is paid in full,
on every request, before the first token appears.

## Nhận xét của tôi

**Prefill bắt đầu lấn át latency từ khoảng 1k token.** Ở 256 token, prefill chỉ tốn 747 ms. Ở
1024 token nó đã là 3.1 s, lớn hơn cả phần decode của một câu trả lời 64 token (khoảng 1.3 s
với TPOT 21 ms). Ở 4096 token, prefill mất 18.7 s.

**Có thấy đoạn cong bậc hai.** Từ 256 đến 1024 token, đường gần như tuyến tính (1.05×). Sau đó
nó cong rõ: 1.13× ở 2048, 1.57× ở 4096 và 1.78× ở 8192. Tốc độ prefill giảm từ 342 xuống 193
tok/s, vì phần attention O(N²) lớn dần so với phần matmul O(N). Đoạn cong ở model này còn nhẹ hơn
model transformer thuần: Qwen3.5 0.8B chỉ có 6/24 layer là full attention, 18 layer còn lại là
recurrent (thấy trong log `llama_memory_recurrent`, đo ở `bonus-c2-kv-cache.md`), và chi phí của
các layer recurrent tăng tuyến tính theo độ dài.

**Hệ quả cho RAG.** Pipeline của tôi đang nhét 3 chunk (khoảng 110–150 token prompt) và có TTFT
dưới 0.6 s. Nếu muốn TTFT ≤ 2 s trên CPU này, ngân sách là khoảng 600 token context, tức khoảng
10 chunk 60 token. Mỗi chunk thêm vào phải trả phí prefill ở mọi request, trừ khi prefix được
cache (llama-server chỉ tái dùng khi prefix giống từng byte).
