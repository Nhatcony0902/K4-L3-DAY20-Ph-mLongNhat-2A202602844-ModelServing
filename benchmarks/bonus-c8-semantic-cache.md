# Bonus C8 - Semantic cache: similarity diagnosis

Embedder: `llama-server --embedding --pooling mean` on `models/Qwen3.5-0.8B-Q4_K_M.gguf` (a chat model, not an embedding model) · llama.cpp `b10488`

## Prompts

| # | topic | prompt |
|--:|:--|:--|
| 1 | A | What is goodput at SLO? |
| 2 | B | Explain TTFT and TPOT. |
| 3 | A | Can you define goodput@SLO? |
| 4 | B | What does time to first token mean? |
| 5 | C | How does PagedAttention work? |
| 6 | A | Tell me what goodput@SLO is. |
| 7 | D | What is prefix caching? |
| 8 | C | Describe how PagedAttention works. |
| 9 | E | What is the capital of France? |
| 10 | F | Give me a recipe for banana pancakes. |
| 11 | G | How do I renew my passport? |

## Cosine similarity matrix

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **1** | 1.00 | 0.86 | 0.90 | 0.85 | 0.85 | 0.89 | 0.86 | 0.86 | 0.81 | 0.71 | 0.78 |
| **2** | 0.86 | 1.00 | 0.85 | 0.77 | 0.83 | 0.84 | 0.77 | 0.87 | 0.68 | 0.67 | 0.70 |
| **3** | 0.90 | 0.85 | 1.00 | 0.81 | 0.83 | 0.91 | 0.80 | 0.84 | 0.67 | 0.71 | 0.75 |
| **4** | 0.85 | 0.77 | 0.81 | 1.00 | 0.78 | 0.77 | 0.86 | 0.77 | 0.77 | 0.66 | 0.77 |
| **5** | 0.85 | 0.83 | 0.83 | 0.78 | 1.00 | 0.79 | 0.81 | 0.95 | 0.70 | 0.61 | 0.75 |
| **6** | 0.89 | 0.84 | 0.91 | 0.77 | 0.79 | 1.00 | 0.75 | 0.83 | 0.68 | 0.78 | 0.70 |
| **7** | 0.86 | 0.77 | 0.80 | 0.86 | 0.81 | 0.75 | 1.00 | 0.81 | 0.82 | 0.66 | 0.75 |
| **8** | 0.86 | 0.87 | 0.84 | 0.77 | 0.95 | 0.83 | 0.81 | 1.00 | 0.70 | 0.66 | 0.72 |
| **9** | 0.81 | 0.68 | 0.67 | 0.77 | 0.70 | 0.68 | 0.82 | 0.70 | 1.00 | 0.68 | 0.79 |
| **10** | 0.71 | 0.67 | 0.71 | 0.66 | 0.61 | 0.78 | 0.66 | 0.66 | 0.68 | 1.00 | 0.69 |
| **11** | 0.78 | 0.70 | 0.75 | 0.77 | 0.75 | 0.70 | 0.75 | 0.72 | 0.79 | 0.69 | 1.00 |

## The two distributions

- True paraphrase pairs (5): 2-4 = 0.768, 1-6 = 0.886, 1-3 = 0.898, 3-6 = 0.905, 5-8 = 0.953
- Lowest-scoring true paraphrase: **2-4 = 0.768**
- Highest-scoring unrelated pairs: 2-8 = 0.871, 1-7 = 0.863, 1-2 = 0.860, 1-8 = 0.855, 4-7 = 0.855
- Highest-scoring unrelated pair: **2-8 = 0.871**

## Threshold sweep over all pairs

| threshold | false hits (unrelated pairs >= t) | false misses (paraphrase pairs < t) |
|--:|--:|--:|
| 0.80 | 18 / 50 | 1 / 5 |
| 0.85 | 8 / 50 | 1 / 5 |
| 0.88 | 0 / 50 | 1 / 5 |
| 0.90 | 0 / 50 | 3 / 5 |
| 0.92 | 0 / 50 | 4 / 5 |
| 0.95 | 0 / 50 | 4 / 5 |

## Chẩn đoán của tôi

Chạy `semantic-cache-demo.py` trên 8 prompt ở ba threshold cho hit rate 7/8 (0.80), 2/8 (0.90) và
1/8 (0.95). Hit rate ở đây **không** có ý nghĩa chất lượng. Bảng ở trên cho thấy lý do.

**False hit.** Ở threshold 0.80, prompt #7 "What is prefix caching?" là chủ đề mới nhưng vẫn
**HIT** với similarity 0.86 (giống nhất với #1 "What is goodput at SLO?"), và cache trả về câu trả
lời về goodput. Còn tệ hơn: #9 "What is the capital of France?" có similarity 0.81 với #1.

**False miss.** #4 "What does time to first token mean?" là paraphrase thật của #2 "Explain TTFT and
TPOT.", nhưng hai câu chỉ đạt **0.768**. Một nửa số cặp không liên quan (25/50) có điểm cao hơn
con số này, kể cả cặp France ↔ goodput (0.81).

**Không có threshold nào sửa được cả hai.** Cặp không liên quan cao nhất là 2-8 = 0.871, còn
paraphrase thấp nhất là 2-4 = 0.768. Hai phân phối **chồng lên nhau**. Bảng sweep cho thấy rõ:

- Ở 0.88 không còn false hit nào, nhưng 2-4 vẫn miss.
- Muốn bắt 2-4 thì threshold phải ≤ 0.768. Khi đó 25/50 cặp không liên quan bị hit.
- Ở 0.90, paraphrase hợp lệ 1-6 (0.886) cũng bắt đầu miss.

**Vì sao.** Đây là chat model (decoder) chạy ở chế độ mean pooling. Nó được train để dự đoán token
tiếp theo, chứ không phải để đặt hai câu cùng nghĩa gần nhau. Mean-pooled hidden state bị khung câu
chi phối: "What is X?" và "What is Y?" trùng phần lớn token và vị trí, nên chúng gần nhau bất kể X
và Y là gì. Còn "TTFT" và "time to first token" không trùng token nào. Embedding model chuyên dụng
(Qwen3-Embedding, BGE-M3, EmbeddingGemma) được fine-tune bằng contrastive loss trên các cặp
paraphrase/negative, và thường lấy embedding từ token cuối hoặc dùng bidirectional attention. Vì vậy
khoảng cách giữa paraphrase và câu lạ rộng hơn nhiều, và threshold mới có nghĩa.

**Rủi ro bảo mật.** Semantic cache và prefix cache dùng chung giữa các user tạo ra một timing side
channel. Một HIT trả về trong 0 ms, còn một miss mất khoảng 2.3 s (thấy trong output demo). Kẻ tấn
công có thể dò xem người khác đã hỏi câu gần giống hay chưa. Cách giảm rủi ro là salt key cache
theo từng tenant, tức không chia sẻ cache giữa các tenant.
