# 02 - Continuous batching under load (u50)

Host `Windows-AMD64` · `--parallel 4` · 14 samples over
60s at 2.0s intervals · raw CSV: `02-server-metrics-u50.csv`

| Gauge | Peak observed |
|:--|--:|
| `n_busy_slots_per_decode` (avg/decode) | 3.94 of 4 slots (98%) |
| `requests_processing` | 4 |
| `requests_deferred` | 46 |
| `kv_cache_usage_ratio` | n/a — not exported by llama.cpp `b10488` |
| `tokens_predicted_total` (final) | 7770 |

Highest sampled value was **3.94 of 4** slots. Note this gauge is llama.cpp's *average* busy slots per decode step, so the number below is the highest average we sampled, not an instantaneous maximum batch width. A peak near 1 means
requests were served one at a time -- either the load was too light to overlap, or
they arrived too far apart. A peak approaching `--parallel` means the scheduler was
genuinely packing concurrent requests into shared decode steps.
`requests_deferred` went above zero: more requests arrived than there were slots, so some waited. That wait is the queue time in your P95.

## Nhận xét của tôi

**Batch width.** Peak `n_busy_slots_per_decode` là **3.94/4** (98%). `requests_processing` bằng 4
suốt 60 s, và `requests_deferred` lên tới 46 (≈ 50 user − 4 slot). Continuous batching đang chạy:
gần như mọi decode step đều xử lý 4 sequence cùng lúc.

**Con số này có khớp với effective concurrency (28.1) trong `02-server-results.md` không?** Hai số
khác nhau nhưng không mâu thuẫn, vì chúng đo hai thứ khác nhau:

- 3.94 là số request **đang được tính toán**. Nó bị chặn trên bởi `--parallel 4`.
- 28.1 (theo Little's Law) là số request **đang nằm trong hệ thống**, gồm cả những request đang
  xếp hàng.

Hiệu 28.1 − 3.94 ≈ 24 chính là độ dài hàng đợi trung bình. Muốn biết slot có đang được dùng hết
không, tôi tin gauge của server. Muốn biết người dùng phải chờ bao lâu, tôi tin Little's Law.

**Batching giúp ít hơn tôi nghĩ khi chạy trên CPU.** `tokens_predicted_total` tăng từ 4180 lên
7770 trong 58.3 s, tức khoảng **62 tok/s tổng**, so với khoảng 48 tok/s khi chạy một luồng (bench).
Vậy batching chỉ cho khoảng **1.3×**. `n_decode_total` tăng 879 bước trong 58.3 s, tức khoảng
66 ms mỗi bước cho khoảng 4 token, trong khi một luồng chạy riêng chỉ mất 21 ms mỗi bước.

Như vậy batch 4 làm mỗi bước chậm đi khoảng 3×. Gộp batch giúp đọc weight một lần cho 4 sequence,
nhưng phần tính toán thì tăng theo số sequence. Thêm vào đó, prefill của các request mới chen vào
cùng bước: `prompt_tokens_total` tăng 3234 token trong cùng khoảng thời gian. Locust (50 user) cũng
chạy trên cùng CPU. Trên CPU, compute nhanh chóng thành nút cổ chai, nên batching không gần như
"miễn phí" như trên GPU.
