# 01 - Tune: thread-count sweep

Model `Qwen3.5-0.8B-Q4_K_M.gguf` · host `Windows-AMD64` · llama.cpp `b10488`
CPU: **14 physical · 20 logical** cores · `ngl=0` · metric `tg128`

| threads (-t) | tg128 (tok/s) | vs best |
|:--|--:|--:|
| 1 | 7.8 | 16% |
| 7 | 50.4 | 100% |
| 14 | 50.3 | 100% |
| 20 | 37.1 | 74% |
| 40 | 20.3 | 40% |

**Best**: `-t 7` at 50.4 tok/s
**Slowest tested**: `-t 1` at 7.8 tok/s (6.44x spread)
**Against the physical-core default** (`-t 14`, 50.3 tok/s): 1.00x

Use this in your run:

```bash
LAB_N_THREADS=7 make bench
```

## Giải thích của tôi

**Knee nằm ở khoảng 4 thread, không phải ở 14 physical core.** Tôi chạy thêm một sweep mịn
(`01-tuning-fine-tg128.txt`). Kết quả decode theo số thread:

| -t | 1 | 2 | 4 | 6 | 8 | 10 | 12 | 14 | 16 | 20 | 40 |
|--|--|--|--|--|--|--|--|--|--|--|--|
| tok/s | 7.8 | 37.9 | 48.0 | 49.9 | 50.7 | 51.3 | 50.9 | 50.3 | 47.0 | 37.1 | 20.3 |

Từ 4 đến 14 thread, đường cong gần như phẳng (chênh không quá 7%). Đây là **bức tường băng thông**.

**Vì sao decode chạm trần sớm.** Với model dense này, mỗi token mới phải đọc gần như toàn bộ
khoảng 0.52 GB weight. 50 tok/s × 0.52 GB ≈ **26 GB/s**, tức khoảng một nửa băng thông lý
thuyết của RAM DDR4-3200 dual-channel (51.2 GB/s). Đây là mức thực tế thường đạt được. Khoảng
4–6 core đã gửi đủ memory request để làm bão hoà memory controller. Thêm core chỉ thêm FLOPs,
mà decode không thiếu FLOPs, nên tốc độ đi ngang. Với 1 thread chỉ đạt 7.8 tok/s, vì một core
không tạo đủ memory request đồng thời, lại còn phải tự làm hết phần dequant.

**Vì sao tụt ở 16, 20 và 40 thread.** i7-12700H là CPU lai: 6 P-core (có hyperthreading) và
8 E-core. llama.cpp chia đều mỗi phép matmul cho N thread, rồi chờ tất cả ở một barrier sau mỗi
op. Khi N vượt số core thật đang rảnh, có thread phải chạy trên E-core chậm hơn hoặc dùng chung
core với một hyperthread khác. Thread chậm nhất quyết định tốc độ của cả bước. Ở 40 thread
(oversubscribe), OS phải chia thời gian CPU giữa các thread. Các thread đang spin-wait ở barrier
chiếm CPU của thread đang làm việc, nên tốc độ chỉ còn 40% so với mức tốt nhất.

**Kết luận.** Default của lab (14 physical core) đã nằm trên plateau (1.00×). Vì vậy tune
thread **không** làm nhanh hơn default. Nhưng so với `-t 20` (dùng hết logical thread, cách cấu
hình nhiều người hay chọn), `-t 7` nhanh hơn **1.36×** (37.1 → 50.4 tok/s) mà chỉ dùng một nửa
số core.
