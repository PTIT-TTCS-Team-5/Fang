# FANG Next Phase Tier-2 Task: Testing Guide Reconciliation

## Brief

Cập nhật `docs/testing_guide.md` để không mô tả sai test files/coverage hiện tại. Task này nên chạy sau hoặc ít nhất sau khi biết kết quả của task `FANG_NEXT_PHASE_T2_UNIT_EMBEDDING_TEST_REPAIR.md`.

## Bối cảnh

P0-A report phát hiện:

- `docs/testing_guide.md` đang nhắc các unit tests RAG/chat manager không tồn tại.
- Unit test hiện tại gồm:
  - `tests/unit/unit_test_chunking.py`
  - `tests/unit/unit_test_embedding.py`
  - `tests/unit/unit_test_ingestion_flow.py`
  - `tests/unit/unit_test_parser_policy.py`
  - `tests/unit/unit_test_persistence.py`
- Unit suite từng fail vì `unit_test_embedding.py` stale theo OpenAI, nhưng lỗi đó được xử lý ở task khác.

Mục tiêu task này là docs reconciliation, không phải viết test mới lớn.

## Goal

Làm testing guide phản ánh đúng test suite hiện tại và các gap thật, không tạo false confidence.

## Scope

Được đọc/sửa:

- `docs/testing_guide.md`
- `tests/unit/`
- `smoke_tests/`
- `requirements.txt` hoặc test runner docs nếu testing guide đang hướng dẫn sai command
- Report từ task `FANG_NEXT_PHASE_T2_UNIT_EMBEDDING_TEST_REPAIR.md` nếu có

## Out of Scope

- Không viết RAG/chat unit tests mới trong task này.
- Không sửa production code.
- Không sửa prompt/LLM/RAG behavior.
- Không cố chạy smoke tests nếu cần DB/server/API keys mà môi trường chưa sẵn.
- Không chỉnh docs strategy/guide ngoài `docs/testing_guide.md` trừ khi chỉ sửa một link hiển nhiên.

## Files to Inspect

1. `docs/testing_guide.md`
2. `tests/unit/`
3. `smoke_tests/`
4. `agent_workflow_doc/FANG_NEXT_PHASE_P0A_REPO_REALITY_AUDIT_REPORT.md`
5. `agent_workflow_doc/FANG_NEXT_PHASE_P0A_USER_NOTE_TRIAGE.md`

## Required Work

1. Liệt kê test files thực tế trong `tests/unit` và `smoke_tests`.
2. Đối chiếu `docs/testing_guide.md` với file thực tế.
3. Cập nhật guide theo hướng:
   - chỉ liệt kê test thật đang tồn tại;
   - nếu test còn thiếu, đưa vào mục "Known gaps" hoặc "Planned tests", không mô tả như đã có;
   - command unit test dùng venv:

```powershell
venv\Scripts\python -m unittest discover -s tests/unit -p "unit_test_*.py"
```

4. Nếu task embedding test đã chạy xong, ghi status unit baseline đúng theo report mới.
5. Nếu chưa có report embedding test, ghi rõ guide đang giả định task đó sẽ sửa baseline, hoặc giữ wording trung tính.

## Acceptance Criteria

- `docs/testing_guide.md` không còn nói `unit_test_rag_orchestrator.py` hoặc `unit_test_chat_manager.py` là test hiện hữu nếu file không tồn tại.
- Guide phân biệt rõ:
  - unit tests hiện có;
  - smoke/integration tests hiện có;
  - test gaps cần bổ sung sau.
- Command chạy test đúng với repo hiện tại.
- Không có docs claim sai về embedding provider/dim nếu guide có nhắc đến embedding test.

## Recommended Dependency Order

Chạy sau `FANG_NEXT_PHASE_T2_UNIT_EMBEDDING_TEST_REPAIR.md`.

Nếu bắt buộc chạy song song, người làm task này phải không chốt unit baseline xanh/đỏ cho đến khi có kết quả từ task embedding.

## Report Format

```text
Task: Testing Guide Reconciliation
Files changed:
- docs/testing_guide.md

Commands run:
- ...

Guide updates:
- ...

Remaining test gaps:
- ...

Notes for tier 1:
- ...
```

## Guardrails

- Khi phát hiện test gap mới, chỉ document gap; không tự mở thêm implementation task.
- Không archive hoặc rewrite toàn bộ testing guide nếu chỉ cần sửa vài section.
