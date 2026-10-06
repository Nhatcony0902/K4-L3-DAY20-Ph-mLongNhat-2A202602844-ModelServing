# Bonus C2 - KV cache quantization

Model `Qwen3.5 0.8B` (`Q4_K_M`) · host `Windows-AMD64` · llama.cpp `b10488` · `--ctx-size 32768 --parallel 1 -fa on -ngl 0 -t 14`

Eval: one ~4.8k-token document with 10 four-digit access codes buried in filler; 10 questions, temperature 0, graded by exact code match.

| KV type | KV cache (MiB, server log) | Private mem after load (MB) | after eval (MB) | Prompt tok | Cold TTFT (ms) | TPOT P50 (ms) | Accuracy |
|:--|--:|--:|--:|--:|--:|--:|--:|
| f16 | 384.0 | 1163.6 | 1225.8 | 4768 | 19524.3 | 30.01 | 10/10 |
| q8_0 | 204.0 | 984.4 | 1046.0 | 4768 | 23331.9 | 34.36 | 10/10 |
| q4_0 | 108.0 | 887.8 | 950.2 | 4768 | 27480.3 | 40.85 | 10/10 |

Answers per question:

- `f16`: 4821, 7395, 2064, 5537, 9182, 3476, 6609, 1748, 8253, 4930
- `q8_0`: 4821, 7395, 2064, 5537, 9182, 3476, 6609, 1748, 8253, 4930
- `q4_0`: 4821, 7395, 2064, 5537, 9182, 3476, 6609, 1748, 8253, 4930

## Phân tích của tôi

**Bộ nhớ: giảm đúng như lý thuyết.** KV cache ở ctx 32768 giảm từ 384 MiB (f16) xuống 204 MiB (q8_0,
còn 53%) và 108 MiB (q4_0, còn 28%). Đây đúng là tỉ lệ 8.5/16 và 4.5/16 bit mỗi phần tử, vì mỗi
block 32 giá trị có thêm một scale f16. Private memory của process giảm tương ứng: 1164 → 984 → 888 MB.

**Điều deck chưa nói: KV ở model này nhỏ hơn nhiều so với một transformer thuần.** Log cho thấy
`32768 cells, 6 layers`. Qwen3.5 là kiến trúc lai: chỉ 6/24 layer là full attention
(`full_attention_interval = 4`), 18 layer còn lại dùng recurrent state cố định 19 MiB và không lớn
theo context. Với 2 KV head × 256 dim, mỗi token chỉ tốn 2 × 2 × 256 × 2 B × 6 layer = 12 KiB.
Một transformer thuần cùng cỡ sẽ tốn gấp 4 lần. Vì thế lợi ích tuyệt đối của KV quant ở đây
chỉ là 180–276 MB, rất nhỏ so với máy 16 GB. KV quant chỉ quan trọng khi KV là phần chiếm chỗ lớn:
model dense, context dài, nhiều slot, hoặc khi phải nhét vừa VRAM 4 GB.

**Latency: tôi trả giá bằng prefill.** Cold TTFT cho 4768 token tăng từ 19.5 s (f16) lên 23.3 s
(q8_0, +20%) và 27.5 s (q4_0, +41%). Lần chạy đầu cho cùng chiều (+14% và +17%). Mỗi K/V mới phải
được lượng tử hoá khi ghi. Log còn cho thấy `attn_rot_k = 1` khi KV bị quant: llama.cpp xoay
(rotate) K/V trước khi lượng tử hoá để làm phẳng outlier, và bước này tốn thêm compute. TPOT
**không kết luận được**: lần 1 cho f16 34.4 / q8 27.4 / q4 30.6 ms, lần 2 cho 30.0 / 34.4 / 40.9 ms.
Mỗi câu trả lời chỉ dài khoảng 5 token nên số đo rất nhiễu. Về lý thuyết, KV nhỏ hơn giúp decode ở
context dài, vì mỗi token phải đọc lại toàn bộ KV. Nhưng với 12 KiB/token × 4.8k token ≈ 56 MiB,
lượng này nhỏ so với 0.5 GB weight, nên hiệu ứng bị chìm trong nhiễu.

**Chất lượng: 10/10 ở cả ba cấu hình**, với các câu trả lời giống hệt nhau. Bài kiểm tra
needle-in-haystack trên 4.8k token không phân biệt được ba cấu hình, có lẽ nhờ bước rotation ở
trên. Đây là eval dễ: chỉ cần tìm lại 4 chữ số. Một eval cần suy luận dài trên context sẽ nhạy hơn.

**Kết luận cho máy này:** q8_0 KV không đáng bật. Tôi tiết kiệm 180 MB nhưng TTFT dài hơn 14–20%.
Nó chỉ đáng khi bộ nhớ là ràng buộc cứng.
