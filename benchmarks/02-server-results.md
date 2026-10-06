# 02 - Serve: load test + saturation reading

Host `Windows-AMD64` · llama.cpp `b10488` ·
`--parallel 4` · `ctx=2048` · `threads=14` ·
`ngl=0`

| Users | Reqs | RPS | P50 (ms) | P95 (ms) | P99 (ms) | Eff. concurrency | Failures |
|:--|--:|--:|--:|--:|--:|--:|--:|
| 10 | 71 | 1.24 | 6600 | 9700 | 11000 | 8.5 | 0.0% |
| 50 | 56 | 0.95 | 30000 | 53000 | 54000 | 28.1 | 0.0% |

*Effective concurrency = RPS x average latency (Little's Law) -- how many requests were
really in flight, regardless of how many users locust simulated. It counts queued requests
too, so the occupancy/slot ratio can legitimately exceed 1.0; it is occupancy, not
utilisation. For true slot utilisation use the server's own gauges (`make metrics`).*

## What these two runs say

| Going from 10 to 50 users | |
|:--|--:|
| Offered load | 5x |
| Throughput actually delivered | **0.76x** (15% of linear) |
| P95 latency | **5.46x** |
| Effective concurrency at 50 users | 28.1 vs `--parallel 4` slots (occupancy/slot ratio 7.04) |

**Saturated.** Throughput delivered only 0.76x for 5x the offered load, and effective concurrency (28.1) is at or above all 4 decode slots. Saturation sets in somewhere at or below 50 users; the load you added beyond that point became queue time rather than throughput.

Throughput moved 0.76x while P95 moved 5.46x. That gap is the goodput argument: past saturation you buy throughput by spending latency, and if your SLO is a P95 target then the requests you added are no longer being served within it. (This lab does not fix an SLO number for you -- pick one in your write-up and state how much goodput you keep at it.)

## Nhận xét của tôi

**Server đã bão hoà ngay từ 10 user.** Điểm bão hoà không nằm ở đâu đó giữa 10 và 50 user.
Con số thuyết phục tôi là effective concurrency ở 10 user: **8.5, lớn hơn 4 slot**. Nghĩa là
trung bình đã có khoảng 4.5 request phải chờ. Một request short chạy một mình mất khoảng 1.5 s
(TTFT ~0.5 s + 48 token × ~21 ms), nhưng P50 ở 10 user đã là 6.6 s.

**Từ 10 lên 50 user**, offered load tăng 5× nhưng throughput **giảm** còn 0.76× (1.24 → 0.95 RPS),
còn P95 tăng 5.46× (9.7 → 53 s). Throughput không tăng vì 4 slot đã bận 98%
(`02-server-batching-u50.md`). Nó còn giảm vì ba lý do:

1. Tỉ lệ long-rag trong các request hoàn thành tăng từ 13% lên 25%. Mỗi long-rag có khoảng 300
   token prompt và 96 token output.
2. Latency 30–54 s trong một cửa sổ 60 s, nên nhiều request chưa kịp xong khi locust dừng và
   không được đếm.
3. Locust chạy 50 user trên cùng máy và giành CPU với llama-server.

**Phần latency tăng thêm là queue time, không phải compute time.** Theo Little's Law,
W = L/λ = 28.1 / 0.95 ≈ 30 s. Trong khi đó, phần compute của một request trong batch 4 chỉ
khoảng 66 ms/bước × 48–96 token ≈ 3–6 s, cộng thêm prefill. Vậy khoảng 80% thời gian P50 là chờ
slot. `requests_deferred` = 46 xác nhận trực tiếp điều này.

Lưu ý: locust gọi `http://localhost:8080`. Trên máy tôi, mỗi kết nối mới tới `localhost` tốn
thêm khoảng 2 s (Windows thử IPv6 `::1` trước, xem `03-integration-results.md`). Vì locust giữ
kết nối keep-alive cho mỗi user, chi phí này chỉ rơi vào request đầu tiên của mỗi user.

**Goodput@SLO.** Tôi chọn SLO là P95 end-to-end ≤ 10 s.

- Ở 10 user, P95 = 9.7 s, nên gần như toàn bộ 1.24 RPS là goodput.
- Ở 50 user, P50 đã là 30 s (min 4.5 s). Goodput gần bằng 0, dù throughput vẫn là 0.95 RPS.

**Knob tôi sẽ đổi trước.** Đầu tiên là **admission control**: giới hạn concurrency phía trước
server và trả 429 sớm. Server đang thiếu năng lực chứ không cấu hình sai: slot đã bận 98%, và
thêm slot trên CPU chỉ được khoảng 1.3× (đã đo), trong khi offered load gấp nhiều lần. Trả lỗi
sớm tốt hơn để request chờ 50 s rồi vẫn vi phạm SLO.

Trong llama-server, knob tiếp theo là `--parallel 8` kèm `--ctx-size 4096` (giữ 512 token mỗi
slot cho long-rag) và `-t 8 -tb 20` (xem `01-tuning-pp512.md`), để tăng tổng tok/s. Nhưng muốn
giữ P95 ≤ 10 s ở 50 user thì phải giảm tải đầu vào, hoặc đưa decode lên GPU. RTX 3050 có băng
thông GDDR6 gấp khoảng 4 lần RAM DDR4 của máy.
