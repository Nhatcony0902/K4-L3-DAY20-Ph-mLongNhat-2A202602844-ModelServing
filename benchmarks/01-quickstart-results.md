# 01 - Measure: latency baseline

Model `Qwen3.5 0.8B` · host `Windows-AMD64` · llama.cpp `b10488`
Settings: `threads=14` `ngl=0` `ctx=2048`
`max_tokens=64` · warm-up discarded
Completed requests: `Q4_K_M` 10/10 · `UD-Q2_K_XL` 10/10

| Quantization | Size (GB) | Load (ms) | TTFT P50/P95 (ms) | TPOT P50/P95 (ms) | E2E P50/P95/P99 (ms) | Decode (tok/s) |
|:--|--:|--:|--:|--:|--:|--:|
| Q4_K_M | 0.50 | 1439 | 470 / 539 | 21.0 / 21.6 | 1787 / 1821 / 1821 | 47.7 |
| UD-Q2_K_XL | 0.39 | 1912 | 515 / 568 | 18.4 / 19.6 | 1687 / 1756 / 1756 | 54.4 |

- **TTFT** = prefill. Short prompts keep it small; long-context RAG is where it explodes.
- **TPOT** = per-output-token decode cost, bounded by memory bandwidth. `decode tok/s = 1000 / TPOT_p50`.
- `UD-Q2_K_XL` decodes **1.14x faster** than `Q4_K_M` here, for 0.11 GB less on disk.

## Nhận xét của tôi

**Tốc độ.** Trên máy tôi (i7-12700H, chạy CPU, `ngl=0`), UD-Q2_K_XL decode nhanh hơn
**1.14×** (TPOT P50 21.0 → 18.4 ms, 47.7 → 54.4 tok/s) và nhỏ hơn **22%** (0.50 → 0.39 GB).
Speedup nhỏ hơn mức giảm kích thước (0.50/0.39 ≈ 1.28×). Decode bị chặn bởi băng thông,
nhưng Q2_K cần nhiều lệnh dequant hơn cho mỗi weight. Bản "UD" (Unsloth Dynamic) còn giữ
một số tensor nhạy cảm ở bit cao hơn. Vì vậy số byte phải đọc mỗi token không giảm theo đúng
tỉ lệ 2-bit/4-bit.

**TTFT của 2-bit lại chậm hơn**: P50 470 → 515 ms, P95 539 → 568 ms. Prefill nhân ma trận
với ma trận nên bị chặn bởi compute. Đọc ít byte hơn không giúp gì ở đây, còn chi phí giải nén
Q2_K cao hơn thì làm chậm. Lưu ý: TTFT đo phía client và có khoảng 180–230 ms overhead, vì mỗi
request tạo một `httpx` client mới trên Windows (tôi đo riêng). Prefill thật chỉ khoảng 165 ms
(`make smoke`: 37 token / 165 ms).

**Chất lượng.** Tôi hỏi cả hai bản cùng 4 câu ở temperature 0 (`01-quality-q4-vs-q2.txt`).
Bản Q2 lặp nguyên đoạn văn và bịa dữ kiện ("Mercury… the second planet from the Sun",
"a liquid planet"). Nó cũng không làm đúng yêu cầu: khi dịch, nó thêm cả câu "Dịch sang
tiếng Việt:" vào kết quả. Bản Q4 dịch đúng và liệt kê hành tinh đúng thứ tự. Cả hai đều tính
sai 17×23 = 391 (Q4 ra 501, Q2 ra 381), vì model 0.8B không làm được phép nhân.

**Kết luận: 2-bit không đáng dùng trên máy này.** Tôi chỉ được nhanh hơn 14% khi decode, nhưng
chất lượng giảm rõ, TTFT lại chậm hơn, và 0.11 GB tiết kiệm được không có ý nghĩa với 16 GB RAM.
2-bit chỉ nên cân nhắc khi bản 4-bit **không vừa** bộ nhớ, ví dụ model lớn trên GPU 4 GB của
tôi. Khi đó câu hỏi là "có chạy được hay không", chứ không phải "nhanh hơn 14%".
