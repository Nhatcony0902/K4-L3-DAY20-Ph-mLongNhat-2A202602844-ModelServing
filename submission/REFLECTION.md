# Reflection — Day 20 Lab (Personal Report)

> **Đây là báo cáo cá nhân.** Số liệu của bạn **không** so sánh được với bạn cùng lớp
> — chỉ so **before vs after trên chính máy bạn**. Rubric chấm độ rõ ràng của setup,
> đo lường và **lập luận**, không chấm tốc độ tuyệt đối.
>
> `make verify` sẽ fail nếu còn placeholder chưa điền. Đó là cố ý.

**Họ Tên:** Phạm Long Nhật
**MSSV:** 2A202602844
**Cohort:** A20-K4
**Ngày submit:** 2026-10-06

---

## 1. Hardware & runtime  *(rubric 1, 2 — 10 điểm)*

> Từ `make probe` (`hardware.json`) và `models/active.json`.

- **OS:** Windows 11 Pro (build 26200). `hardware.json` ghi `release: "10"`, đó là cách Python báo
  Windows 11.
- **CPU:** 12th Gen Intel Core i7-12700H, kiến trúc lai 6 P-core (có HT) + 8 E-core
- **Cores:** 14 physical / 20 logical
- **CPU extensions:** `system_info` của llama-server báo AVX, AVX2, AVX_VNNI, FMA, F16C và BMI2.
  Không có AVX-512, vì Alder Lake tắt nó.
- **RAM:** 15.7 GB, DDR4-3200 dual-channel (2 × 8 GB, băng thông lý thuyết 51.2 GB/s)
- **Accelerator:** có NVIDIA RTX 3050 Laptop 4 GB (CUDA + Vulkan được phát hiện), nhưng **không
  dùng**. Toàn bộ lab chạy CPU-only, `ngl=0` (lý do ở setup story).
- **llama.cpp asset đã tải:** `llama-b10488-bin-win-cpu-x64.zip` (build b10488)
- **Model đã dùng:** Qwen3.5 0.8B (`LAB_MODEL=qwen35-0.8b`)
- **Quantization:** Q4_K_M + UD-Q2_K_XL (từ `models/active.json`)

**Chạy ở đâu:** laptop của tôi (không dùng cloud)

**Setup story:**

- Mạng hôm làm lab chỉ đạt 20–200 KB/s và hay bị treo. Vì vậy tôi đổi model khuyến nghị là
  Gemma 4 E2B (5.2 GB) sang Qwen3.5 0.8B. `hardware.json` vẫn ghi khuyến nghị Gemma/CUDA của bước
  probe.
- Tôi cũng đổi runtime CUDA (250 MB + cudart) sang bản CPU 18.5 MB.
- Downloader của Hugging Face treo ở 305 MB. Tôi tải tiếp bằng `curl -C -` và kiểm tra sha256 khớp.
- `lab.ps1` không chạy được trên PowerShell 5.1 vì file UTF-8 không có BOM; tôi lưu lại có BOM.
- Các file `.md` được sinh ra bằng cp1252, nên tôi chuyển chúng sang UTF-8.

**Ghi chú về screenshots:** Ảnh `02-bench`, `04-locust-10` và `05-locust-50` được chụp ở một lần
chạy lại sau đó trên cùng máy. Vì vậy số trong ảnh khác số đã báo
cáo trong file này. Số liệu thô của lần chạy lại được lưu ở `benchmarks/rerun-screenshots/`.
Mọi phân tích dùng lần chạy gốc, vì `make metrics` và `make load-report` được đo cùng với lần đó.

So sánh hai lần chạy:

| Phép đo | Lần gốc | Lần chạy lại |
|---|--:|--:|
| Q4_K_M decode | 47.7 tok/s | 44.9 tok/s |
| UD-Q2_K_XL decode | 54.4 tok/s | 47.3 tok/s |
| Q2 nhanh hơn Q4 | 1.14× | 1.05× |
| 10 user: RPS / P95 | 1.24 / 9.7 s | 1.02 / 12 s |
| 50 user: RPS / P95 | 0.95 / 53 s | 1.01 / 50 s |

Lợi thế của 2-bit còn nhỏ hơn ở lần chạy lại, nên kết luận "không đáng" càng chắc. Ở 50 user,
hai lần cho kết quả rất gần nhau (0.95 và 1.01 RPS; P95 53 s và 50 s), nên trần năng lực khoảng
1 RPS là ổn định. Dù vậy, cả hai lần đều cho thấy server bão
hoà: offered load tăng 5× nhưng throughput chỉ thay đổi 0.76–0.99×, còn P95 ở 50 user lớn gấp 4.2–5.5
lần so với lúc 10 user.

---

## 2. Đo lường  *(rubric 3, 4, 5 — 20 điểm)*

> Từ `benchmarks/01-quickstart-results.md` (`make bench`, 14 thread, ctx 2048, 64 token/request).

| Quantization | Size (GB) | Load (ms) | TTFT P50/P95 (ms) | TPOT P50/P95 (ms) | E2E P50/P95/P99 (ms) | Decode (tok/s) |
|---|--:|--:|--:|--:|--:|--:|
| Q4_K_M | 0.50 | 1439 | 470 / 539 | 21.0 / 21.6 | 1787 / 1821 / 1821 | 47.7 |
| UD-Q2_K_XL | 0.39 | 1912 | 515 / 568 | 18.4 / 19.6 | 1687 / 1756 / 1756 | 54.4 |

**Quan sát:** 2-bit decode nhanh hơn 1.14× và nhỏ hơn 22%, nhưng TTFT lại chậm hơn 10%, vì prefill
bị chặn bởi compute và dequant Q2_K tốn hơn. Tôi đã hỏi cả hai bản cùng 4 câu
(`benchmarks/01-quality-q4-vs-q2.txt`). Bản Q2 lặp câu, bịa dữ kiện ("Mercury là hành tinh thứ
hai") và dịch sai yêu cầu. **Không đáng dùng** trên máy 16 GB.

---

## 3. Serving under load  *(rubric 8, 9, 10 — 20 điểm)*

> Từ `benchmarks/02-server-results.md` (`make load-report`), `--parallel 4`, ctx 2048.

| Users | RPS | P50 (ms) | P95 (ms) | P99 (ms) | Eff. concurrency | Failures |
|--:|--:|--:|--:|--:|--:|--:|
| 10 | 1.24 | 6600 | 9700 | 11000 | 8.5 | 0 (0%) |
| 50 | 0.95 | 30000 | 53000 | 54000 | 28.1 | 0 (0%) |

- **Offered load tăng 5×, throughput thực tăng:** 0.76× (thực tế là giảm)
- **P95 tăng:** 5.46×
- **Effective concurrency ở 50 users:** 28.1 so với `--parallel` = 4 slots

**Peak `llamacpp:n_busy_slots_per_decode`** (từ `make metrics` khi `make load-50` đang
chạy): 3.94 / 4 slots (`requests_deferred` lên tới 46)

**Saturation reading:** Server đã bão hoà **ngay từ 10 user**. Effective concurrency lúc đó là
8.5, lớn hơn 4 slot.

Ở 50 user, slot bận 98% và có 46 request bị deferred. Theo Little's Law, W ≈ 28.1/0.95 ≈ 30 s,
trong khi compute chỉ khoảng 3–6 s (66 ms/bước × 48–96 token). Vậy latency tăng thêm là
**queue time**.

Tôi sẽ thêm admission control trước tiên (giới hạn concurrency, trả 429 sớm), vì server thiếu năng
lực chứ không cấu hình sai: batching trên CPU chỉ cho khoảng 1.3× tổng tok/s.

---

## 4. Integration  *(rubric 12, 13 — 15 điểm)*

> Từ `make pipeline` (`benchmarks/03-integration-results.md`). Lần chạy cuối dùng
> `--base-url http://127.0.0.1:8080`. Lần chạy đầu dùng mặc định `localhost`, kết quả ở
> `benchmarks/03-integration-results-localhost.md`.

| Day | Piece | Real hay stub? |
|---|---|---|
| N16 Cloud/IaC | chỉ chạy localhost, không có cluster hay Compose | stub |
| N17 Data pipeline | list `TOY_DOCS` viết sẵn trong code | stub |
| N18 Lakehouse | dict Python thay cho Delta/Iceberg | stub |
| N19 Vector + features | keyword overlap, không có embedding | stub |
| N20 Serving | `llama-server` | real |

**Latency split** (mean của 3 query, lần chạy với 127.0.0.1):

- embed: 0.0 ms (không có embedding server, retrieval dùng keyword overlap)
- retrieve: 0.1 ms
- llm: 4315.8 ms (lần chạy qua `localhost`: 5892.9 ms)
- **stage chiếm nhiều nhất:** llm (100% của total)

**Reflection:** Bottleneck là llm, đúng như tôi kỳ vọng. Bên trong stage này, decode chiếm áp đảo
(ví dụ 3402 ms decode so với 82 ms prefill).

Bất ngờ là trên Windows, gọi `localhost` tốn thêm khoảng 2.4 s mỗi request, vì Windows thử IPv6
`::1` trước. Muốn giảm latency 2×: gọi `127.0.0.1` (đã làm, 5.89 → 4.32 s) và giới hạn độ dài câu
trả lời.

---

## 5. The single change that mattered most  *(rubric 11 — 10 điểm)*

> Nguồn: `benchmarks/01-tuning-tg128.md` (`make tune`), sweep mịn ở
> `benchmarks/01-tuning-fine-tg128.txt`, và sweep prefill ở `benchmarks/01-tuning-pp512.md`.

**Change:** hạ số thread decode từ `-t 20` (dùng hết 20 logical thread của CPU) xuống `-t 7`.

```
before:  37.1 tok/s   (-t 20, tg128, Q4_K_M, CPU)
after:   50.4 tok/s   (-t 7)
speedup: 1.36×        (so với default 14 physical core của lab: 1.00×, vì 14 đã nằm trên plateau)
```

**Tại sao nó work:**

Mỗi token decode phải đọc lại gần như toàn bộ khoảng 0.52 GB weight từ RAM. Ở 50 tok/s, đó là
khoảng **26 GB/s**, tức khoảng một nửa băng thông lý thuyết 51.2 GB/s của DDR4-3200 dual-channel.
Đây là mức đạt được trong thực tế. Sweep mịn cho thấy throughput tăng nhanh từ 1 lên 4 thread
(7.8 → 48 tok/s), vì một core không tạo đủ memory request đồng thời. Từ 4 đến 14 thread thì đi
ngang trong khoảng 48–51 tok/s: memory controller đã bão hoà, thêm core chỉ thêm FLOPs mà decode
không cần.

Ở 20 thread, throughput rơi còn 37.1 tok/s. CPU này là CPU lai: thread thứ 15–20 phải chạy trên
hyperthread dùng chung core với thread khác, hoặc trên E-core chậm. llama.cpp chia đều mỗi matmul
cho mọi thread rồi chờ ở barrier, nên thread chậm nhất kéo cả bước chậm theo. Ở 40 thread, OS phải
time-slice, và thread spin-wait chiếm CPU của thread đang làm việc, nên chỉ còn 20.3 tok/s.

**Bằng chứng đây đúng là vấn đề băng thông chứ không phải số core**: prefill (pp512, nhân ma trận
với ma trận, bị chặn bởi compute) lại có đỉnh ở **20 thread** (326.2 tok/s), cùng cái máy mà decode
có đỉnh ở 7–10. Hai phase có số thread tối ưu khác nhau. Vì vậy cấu hình đúng cho llama-server trên
máy này là `-t 8 -tb 20`, tức số thread riêng cho decode và cho batch/prefill.

**Điều khác với kỳ vọng:** deck dự đoán đỉnh ở số physical core (14). Thực tế knee ở khoảng 4 và
plateau rất rộng. Lý do là model 0.8B chỉ có 0.5 GB weight, nên băng thông bão hoà rất sớm.

---

## 6. Bonus  *(optional — tối đa 10 điểm)*

**Đã làm:**

- **B2**: `make sweep-ctx` (`benchmarks/bonus-ctx-len-sweep.md`), `make sweep-batch`
  (`bonus-batch-size-sweep.md`) và `make sweep-quant` (`bonus-quant-sweep.md`)
- **B3**: before/after từ sweep-quant, ở dưới
- **B4**: challenge **C2**, KV cache quantization (`bonus/challenges/c2_kv_cache_quant.py` →
  `benchmarks/bonus-c2-kv-cache.md`)
- **B5**: challenge **C8**, semantic cache với embedding server thật (`make serve-embed` +
  `semantic-cache-demo.py`, cùng ma trận similarity `bonus/challenges/c8_similarity_matrix.py` →
  `benchmarks/bonus-c8-semantic-cache.md`)
- Không làm B1: máy không có cmake/MSVC, và mạng quá chậm để cài Build Tools.

**Numbers (B3, sweep-quant, decode tg128, 14 thread):**

```
before:  37.95 tok/s   UD-Q6_K_XL (0.771 GB)
after:   55.38 tok/s   UD-Q2_K_XL (0.418 GB)
speedup: 1.46×         (file nhỏ hơn 1.85×; Q4 -> Q2 chỉ 1.14×)
```

**Điều này nói lên gì mà deck chưa nói:**

- **Quant sweep:** speedup luôn nhỏ hơn mức giảm kích thước. Tôi fit
  thời gian mỗi token = bytes/BW + c và được BW ≈ 42.6 GB/s cùng **c ≈ 8.3 ms cố định mỗi token**.
  Mô hình dự đoán Q4 đạt 46.8 tok/s, đo thật được 48.75. Ở Q2, phần cố định đã chiếm khoảng 46%
  thời gian mỗi token. Vì vậy trên model nhỏ, giảm bit gặp lợi ích giảm dần rất nhanh, trong khi
  chất lượng vỡ ở Q2. Tôi chọn bản 4-bit.
- **Ctx sweep:** prefill cong lên rõ từ 2048 token (1.13×, rồi 1.78× ở 8192). Đoạn cong nhẹ hơn
  transformer thuần, vì 18/24 layer là recurrent và có chi phí tuyến tính.
- **Batch sweep:** đường phẳng (6%), nằm trong biên nhiễu nhiệt (khoảng 20% giữa các lần chạy).
  Tôi không kết luận gì từ sweep này.

- **C2 (KV quant):** KV giảm đúng lý thuyết (384 → 204 → 108 MiB ở ctx 32k). Nhưng Qwen3.5 là
  kiến trúc lai, chỉ 6/24 layer có KV (12 KiB/token), nên tiết kiệm tuyệt đối chỉ 180–276 MB, trong
  khi TTFT 4.8k token tăng 14–41%. Accuracy needle-in-haystack 10/10 ở cả ba cấu hình. Với model này
  và máy này, bật KV quant không đáng.
- **C8 (semantic cache):** Chat model ở chế độ mean pooling cho paraphrase thật "TTFT" ↔ "time to
  first token" chỉ 0.768, trong khi một nửa số cặp không liên quan (25/50) có điểm cao hơn, kể cả
  "capital of France" ↔ "goodput" (0.81). Hai phân phối chồng nhau, nên không có threshold nào vừa
  tránh false hit vừa bắt được paraphrase.

---

## 7. Điều làm bạn ngạc nhiên nhất  *(optional)*

Overhead lớn nhất mà tôi tìm được không nằm trong model mà nằm ở client. Trên Windows, gọi
`localhost` tốn thêm khoảng 2 s mỗi kết nối, vì Windows thử IPv6 `::1` trong khi server chỉ nghe
IPv4. Việc tạo `httpx` client mới còn tốn thêm khoảng 200 ms trong mỗi số đo TTFT. Nếu không đối
chiếu với `timings` mà server tự báo, tôi đã đổ lỗi sai cho model.

---

## 8. Self-check trước khi push

- [x] `hardware.json` committed
- [x] `models/active.json` committed
- [x] `benchmarks/01-quickstart-results.md` committed (`make bench`)
- [x] `benchmarks/01-tuning-tg128.md` committed (`make tune`)
- [x] `benchmarks/02-server-results.md` committed (`make load-report`)
- [x] `benchmarks/02-server-batching-u50.md` hoặc `-metrics-u50.csv` committed (`make metrics`)
- [x] `benchmarks/locust-10_stats.csv` + `locust-50_stats.csv` committed (`make load-10` / `load-50`)
- [x] `benchmarks/03-integration-results.md` committed (`make pipeline`)
- [x] Mọi section **"required — replace this line"** trong các file `benchmarks/*.md`
      đã được thay bằng nhận xét của bạn
- [ ] 5 screenshots trong `submission/screenshots/`
- [ ] `make verify` → **exit 0**
- [ ] Repo tên đúng mẫu `K4-L3-DAY20-HoVaTen-MSSV-ModelServing` (xem `docs/SUBMISSION.md`)
- [ ] Repo GitHub ở chế độ **public**
- [ ] Đã push và paste public URL vào VinUni LMS **trước 23:59 (UTC+7) ngày làm lab**
- [x] **Không** commit `models/*.gguf`, `runtime/` hay `.env` (đã có trong `.gitignore`)

**Quan trọng:** repo phải **public** đến khi điểm được công bố. Private → grader không
xem được → 0 điểm.

---

## 9. Khai báo sử dụng AI  *(xem `docs/RULES.md` §3)*

Tôi dùng **Claude Code (Claude Opus)** như một trợ lý chạy lab trên máy của tôi. AI đã:


- debug setup: tải lại khi download treo, encoding của `lab.ps1` và các file `.md`, và chẩn đoán
  overhead `localhost`/IPv6;
- viết hai script bonus `bonus/challenges/c2_kv_cache_quant.py` và `c8_similarity_matrix.py`;


Mọi số liệu đều do script sinh ra trên máy tôi, và không có số nào được sửa tay. Tôi đã đọc lại và
chịu trách nhiệm về phần lập luận.
