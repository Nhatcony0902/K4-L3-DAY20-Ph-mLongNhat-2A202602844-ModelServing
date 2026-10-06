# 01 - Tune: thread-count sweep

Model `Qwen3.5-0.8B-Q4_K_M.gguf` · host `Windows-AMD64` · llama.cpp `b10488`
CPU: **14 physical · 20 logical** cores · `ngl=0` · metric `pp512`

| threads (-t) | pp512 (tok/s) | vs best |
|:--|--:|--:|
| 1 | 15.9 | 5% |
| 7 | 256.5 | 79% |
| 14 | 316.1 | 97% |
| 20 | 326.2 | 100% |
| 40 | 283.5 | 87% |

**Best**: `-t 20` at 326.2 tok/s
**Slowest tested**: `-t 1` at 15.9 tok/s (20.54x spread)
**Against the physical-core default** (`-t 14`, 316.1 tok/s): 1.03x

Use this in your run:

```bash
LAB_N_THREADS=20 make bench
```

## Giải thích của tôi

Prefill có hình dạng khác hẳn decode (`01-tuning-tg128.md`). Tốc độ tăng gần tuyến tính đến
7 thread (15.9 → 256.5 tok/s), tiếp tục tăng ở 14 thread (316.1), và **đạt đỉnh ở 20 logical
thread** (326.2). Nó chỉ tụt khi oversubscribe lên 40 thread (283.5).

**Cơ chế.** Prefill 512 token là phép nhân ma trận với ma trận. Mỗi weight chỉ cần nạp một lần
nhưng được dùng cho cả 512 token. Arithmetic intensity vì thế cao, nên prefill bị chặn bởi
**compute** chứ không phải băng thông. Mỗi core thêm vào, kể cả E-core và hyperthread, đều thêm
FLOPs hữu ích. Phần tăng thêm nhỏ: từ 14 lên 20 thread chỉ được +3%. Lý do là hyperthread dùng
chung execution unit AVX2 với thread anh em, và E-core yếu hơn P-core. Ở 40 thread, chi phí lập
lịch và barrier lớn hơn lợi ích.

**Hệ quả.** Số thread tối ưu cho prefill (20) khác với decode (khoảng 8–10). llama-server cho
phép đặt riêng hai giá trị: `-t` cho decode và `-tb` cho batch/prefill. Cấu hình hợp lý cho máy
này là `-t 8 -tb 20`. Default của lab dùng một số chung (14) cho cả hai, nên chưa tối ưu cho
phần nào.
