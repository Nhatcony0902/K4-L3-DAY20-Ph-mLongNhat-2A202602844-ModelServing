# Bonus - Quantization sweep (Qwen3.5 0.8B, Unsloth Dynamic ladder)

Host `Windows-AMD64` · llama.cpp `b10488` ·
`threads=14` `ngl=0` · metric `tg128`

| Quantization | Size (GB) | tg128 (tok/s) | vs UD-Q4_K_XL | tok/s per GB |
|:--|--:|--:|--:|--:|
| UD-Q2_K_XL | 0.39 | 55.4 | 1.14x | 142.0 |
| UD-Q4_K_XL | 0.52 | 48.8 | 1.00x | 93.8 |
| UD-Q6_K_XL | 0.72 | 38.0 | 0.78x | 52.7 |

Decode is memory-bandwidth-bound, so fewer bytes per weight usually means more
tokens per second -- the "tok/s per GB" column shows how much of that you are
actually getting back per gigabyte spent.

Speed is only half the trade. The other half is quality, and no benchmark here
measures it. Serve two of these (`make serve` and
`.venv/bin/python labs/02-serve/serve.py --compare`) and ask each the same three questions
before you claim a winner.

## Nhận xét của tôi

**Speedup nhỏ hơn mức giảm kích thước.** Từ UD-Q6 xuống UD-Q2, file nhỏ đi 1.85× (0.771 → 0.418 GB,
kích thước file thật) nhưng decode chỉ nhanh hơn 1.46× (37.95 → 55.38 tok/s). Băng thông hiệu dụng
(size × tok/s) **giảm** khi model nhỏ đi: 29.3 GB/s ở Q6, 27.2 ở Q4 và 23.1 ở Q2. Nếu decode bị chặn
thuần tuý bởi băng thông thì con số này phải không đổi.

**Mô hình hai thành phần.** Tôi giả sử thời gian mỗi token = bytes / BW + c và fit theo hai điểm
Q2 và Q6. Kết quả: **BW ≈ 42.6 GB/s** (83% của 51.2 GB/s lý thuyết) và **c ≈ 8.3 ms cố định mỗi
token**. Phần cố định này gồm dequant, cập nhật recurrent state của các layer không phải full attention, sampling
và đồng bộ thread. Mô hình dự đoán UD-Q4 đạt 46.8 tok/s, còn đo được là 48.75 (lệch 4%).

Hệ quả: ở Q2, phần cố định chiếm 8.3/18.1 ≈ 46% thời gian mỗi token. Giảm bit tiếp chỉ cắt được
nửa còn lại. Đây là lý do 2-bit chỉ cho 1.14× so với 4-bit trên model nhỏ này. Với model lớn hơn,
phần bytes/BW sẽ lấn át và lợi ích của quant thấp sẽ gần tuyến tính hơn.

**Bản tôi sẽ ship: bản 4-bit** (Q4_K_M, hoặc UD-Q4_K_XL nhanh tương đương). Chất lượng **vỡ ở Q2**:
tôi đã kiểm tra trong `01-quality-q4-vs-q2.txt` (lặp câu, bịa dữ kiện, không theo chỉ dẫn). Tôi
**chưa** kiểm tra chất lượng Q6 so với Q4. Q6 chậm hơn 22%, và với một model 0.8B, tôi không có bằng
chứng rằng chất lượng tăng đủ để bù. Đây là việc cần đo tiếp trước khi chọn Q6.
