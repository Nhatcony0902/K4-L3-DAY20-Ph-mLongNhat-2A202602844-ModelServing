# Bonus - Batch-size sweep (chunked prefill)

Host `Windows-AMD64` · llama.cpp `b10488` ·
`threads=14` `ngl=0` · metric `pp512`

| -b (logical) | -ub (micro) | pp512 (tok/s) | vs best |
|:--|--:|--:|--:|
| 128 | 128 | 269.6 | 100% |
| 256 | 256 | 263.1 | 98% |
| 512 | 256 | 262.9 | 98% |
| 512 | 512 | 253.8 | 94% |
| 1024 | 512 | 258.7 | 96% |
| 2048 | 512 | 258.0 | 96% |

Best: `-b 128 -ub 128` at 269.6 tok/s
(1.06x the slowest point tested).

This sweep only measures the throughput half of the trade. The cost it hides is
TTFT for queued requests: a larger micro-batch holds the device longer per step,
so anything waiting behind it waits longer. To see both halves, re-run
`make load-50` with your best and worst settings via
`.venv/bin/python labs/02-serve/serve.py -- -b N -ub M` and compare P95.

## Nhận xét của tôi

**Đường gần như phẳng.** Mọi cấu hình nằm trong khoảng 253.8–269.6 tok/s (chênh 6%).
`-b 128 -ub 128` đứng đầu, nhưng chênh lệch này **nằm trong biên nhiễu** của máy tôi. Cùng phép
đo pp512 ở 14 thread cho 316.1 tok/s khi chạy `make tune` và khoảng 260 tok/s ở lần này.
Laptop bị giảm xung do nhiệt sau nhiều lượt benchmark liên tiếp, và mức trôi giữa hai lần chạy
(khoảng 20%) lớn hơn nhiều so với hiệu ứng của knob (6%). Vì vậy tôi **không** kết luận
`-ub 128` nhanh hơn.

**Vì sao phẳng trên CPU.** Micro-batch lớn có lợi trên GPU, vì nó lấp đầy hàng nghìn core và chia
nhỏ chi phí launch kernel. Trên CPU 14 thread, một micro-batch 128 token đã đủ việc cho mọi thread
và dữ liệu nằm vừa cache. Tăng `-ub` không thêm parallelism thực sự, mà chỉ tăng kích thước buffer
trung gian.

**Production.** Tôi sẽ chọn `-b 512 -ub 256` (hoặc giữ default). Throughput không đổi, mà micro-batch
nhỏ hơn giữ mỗi bước compute ngắn hơn, nên decode của các slot khác không bị chặn lâu khi có prefill
lớn chen vào. Để chắc chắn nó không làm hại P95, tôi cần chạy `make load-50` với `-ub 128` và
`-ub 512`, so P95 TPOT của request short khi có long-rag chen vào, và chạy lặp vài lần ở cùng nhiệt
độ máy để tách tín hiệu khỏi nhiễu.
