# FANG Next Phase Tier-2 Task: Unit Embedding Test Repair

## Brief

Sửa unit test embedding đang stale vì code runtime đã chuyển sang Google Gemini SDK, trong khi test cũ vẫn patch OpenAI `AsyncOpenAI`. Đây là task tier 2 hẹp, có thể làm trước P0-B vì embedding truth source đã được user chốt: dùng Gemini `gemini-embedding-001`, mặc định 1536 dimensions.

## Bối cảnh

Từ P0-A report:

- Runtime embedding hiện ở `app/services/embedding.py`.
- Config hiện ở `app/core/config.py`.
- Default hiện tại là Gemini `gemini-embedding-001`, `embedding_dim=1536`.
- `tests/unit/unit_test_embedding.py` đang lỗi vì patch `app.services.embedding.AsyncOpenAI`, nhưng module hiện không còn dùng OpenAI client.

Quyết định user đã chốt:

- Sửa code/test/docs theo Gemini embedding hiện tại.
- Không quay lại OpenAI `text-embedding-3-small` 1024 dims.

## Goal

Làm unit test embedding phản ánh đúng runtime hiện tại và làm unit test baseline xanh nếu lỗi hiện tại chỉ đến từ embedding test stale.

## Scope

Được đọc/sửa:

- `tests/unit/unit_test_embedding.py`
- `app/services/embedding.py`
- `app/core/config.py`
- `requirements.txt` hoặc file dependency tương đương nếu test import thiếu dependency đã có trong runtime

Chỉ được sửa production code trong `app/services/embedding.py` nếu test phát hiện bug thật hoặc cần thêm seam nhỏ đã có style rõ trong repo. Không refactor embedding architecture.

## Out of Scope

- Không đổi embedding provider/model/dim.
- Không thêm OpenAI fallback.
- Không sửa RAG/chat behavior.
- Không sửa docs trong task này, trừ khi phát hiện comment ngay trong test sai nghiêm trọng.
- Không đụng `smoke_tests` trong task này, vì smoke e2e dim stale là task ưu tiên thấp riêng.

## Files to Inspect

1. `tests/unit/unit_test_embedding.py`
2. `app/services/embedding.py`
3. `app/core/config.py`
4. `tests/unit/unit_test_chunking.py` để học style test hiện có nếu cần.

## Required Work

1. Đọc `embedding.py` để xác định chính xác cách code gọi Google Gemini SDK.
2. Sửa `unit_test_embedding.py` để fake/mock đúng client/API hiện tại.
3. Test phải verify các behavior cốt lõi:
   - dùng configured embedding model;
   - trả vector có dimension theo config/test setup;
   - batching/chunk ordering không bị đảo;
   - error handling hiện tại vẫn được cover nếu test cũ đã cover.
4. Chạy unit test bằng venv:

```powershell
venv\Scripts\python -m unittest discover -s tests/unit -p "unit_test_*.py"
```

5. Nếu toàn bộ unit suite vẫn fail vì lỗi ngoài embedding, ghi rõ trong report và không tự mở rộng scope.

## Acceptance Criteria

- `unit_test_embedding.py` không còn patch symbol OpenAI đã stale.
- Embedding unit test pass.
- Nếu chỉ có lỗi stale embedding, toàn bộ command unit test ở trên pass.
- Không có thay đổi provider/model/dim production.
- Không có thay đổi vào prompt/model routing/RAG files.

## Report Format

Sau khi làm, tạo report ngắn trong câu trả lời hoặc file report nếu user yêu cầu:

```text
Task: Unit Embedding Test Repair
Files changed:
- ...

Commands run:
- venv\Scripts\python -m unittest discover -s tests/unit -p "unit_test_*.py"

Result:
- ...

Remaining issues:
- None / ...

Notes for tier 1:
- ...
```

## Guardrails

- Nếu cần sửa production embedding code nhiều hơn 20-30 dòng, dừng lại và báo vì có thể không còn là task tier 2 hẹp.
- Nếu phát hiện config thực tế không phải Gemini 1536, báo conflict thay vì tự đổi quyết định.
