# P0-B AI/LLM Inventory

## Brief

P0-B dùng model tier 1 để lập inventory đầy đủ cho mọi điểm FANG dùng AI/LLM/embedding hiện tại. Trong kế hoạch hiện tại, P0-B chạy sau P0-A để tận dụng current reality và drift map đã có. Inventory này là đầu vào cho prompt review, eval tối thiểu, model/fallback reconciliation và mọi quyết định refactor LLM layer sau này.

## Mục tiêu

1. Liệt kê mọi AI use case đang tồn tại trong code.
2. Xác định prompt, model routing, structured output, fallback, validation, persistence và failure handling của từng use case.
3. Chỉ ra phần nào là inference/embedding/retrieval/generation/mapping/summarization.
4. Tạo nguồn tham chiếu để P1-A không bỏ sót prompt và để future refactor không bỏ sót caller.

## Phạm vi ưu tiên

### Các điểm đã biết phải kiểm tra

1. CV parsing và parser fallback.
2. Embedding/chunking/ingestion.
3. JobApplication chat generation hiện tại.
4. Chat summarization và branch conversation.
5. RAG/model adapters/orchestrator.
6. NMAIex province mapper.
7. NMAIex skill mapper.
8. Language proficiency normalization.
9. Ranking flow chỗ nào dùng embedding hoặc kết quả parse/mapping.
10. Scripts/synthetic data có prompt hoặc model call nếu chúng ảnh hưởng vận hành hiện tại.

### File bắt đầu đọc

1. `app/services/cv_parser.py`
2. `app/services/cv_parser_adapters.py`
3. `app/services/embedding.py`
4. `app/services/chunking.py`
5. `app/services/rag_model_adapters.py`
6. `app/services/rag_orchestrator.py`
7. `app/services/rag_query.py`
8. `app/api/routes_chat.py`
9. `app/services/nmaiex_mapper_service.py`
10. `app/services/nmaiex_ranking_service.py`
11. `app/core/config.py`
12. `app/core/nmaiex_config.py`
13. `synthetic_data/` nếu có model call/prompt liên quan.

## Output bắt buộc

Tạo một inventory document chính với bảng tối thiểu:

| Use case | Code entry point | Prompt/template location | Input data | Output contract | Models/modes | Validation/fallback | Risks | Tests/evals |
|---|---|---|---|---|---|---|---|---|

Phụ lục nên có:

1. Model/fallback map.
2. Prompt location index.
3. Structured output/schema index.
4. Failure handling gaps.
5. Observability/versioning gaps.

## Điều cần bóc rõ cho mỗi use case

1. Business purpose.
2. Trigger/caller.
3. Prompt nằm inline hay template riêng.
4. Data nào là trusted/untrusted.
5. Có system/user/context separation không.
6. Model mode và fallback chain.
7. Có schema/Pydantic/deterministic validation không.
8. Nếu model fail hoặc output xấu thì hệ thống làm gì.
9. Có log/audit/test/eval nào hiện hữu.
10. Những prompt nào P1-A phải review trước.

## Tiêu chí chất lượng

- Inventory bám code, không chỉ bám README/docs.
- Không gộp nhiều prompt có nhiệm vụ khác nhau vào một dòng mơ hồ.
- Ghi rõ nơi hiện không có prompt nhưng có AI dependency, ví dụ embedding hoặc retrieval.
- Ghi rõ use case nào sẽ đổi behavior khi `JobApplication chat` chuyển sang full CV markdown.
- Ghi rõ use case nào chỉ thuộc synthetic/dev tooling để tránh lẫn với production path.

## Prompt cho GPT-5.5 hoặc Claude Opus 4.6

```text
Thực hiện P0-B AI/LLM Inventory cho repo FANG.

Mục tiêu:
- Lập inventory đầy đủ cho mọi điểm dùng AI/LLM/embedding/retrieval trong code hiện tại.
- Đây là đầu vào cho prompt review, eval tối thiểu, model/fallback reconciliation và quyết định refactor sau này.

Yêu cầu đọc code trước docs:
- app/services/cv_parser.py
- app/services/cv_parser_adapters.py
- app/services/embedding.py
- app/services/chunking.py
- app/services/rag_model_adapters.py
- app/services/rag_orchestrator.py
- app/services/rag_query.py
- app/api/routes_chat.py
- app/services/nmaiex_mapper_service.py
- app/services/nmaiex_ranking_service.py
- app/core/config.py và app/core/nmaiex_config.py
- Tỏa ra app/models, scripts, synthetic_data và docs nếu cần xác nhận.

Output:
1. Tạo một inventory document trong agent_workflow_doc.
2. Có bảng cho từng use case với:
   - business purpose
   - code entry point
   - prompt/template location
   - input data
   - output contract
   - model/mode/fallback
   - validation/failure handling
   - security/compliance/grounding risks
   - current tests/evals
3. Có phụ lục prompt location index, model/fallback map, schema/structured-output index, observability gaps.
4. Dẫn file path cụ thể cho mọi điểm quan trọng.

Ràng buộc:
- Không sửa code.
- Không chỉ dựa vào README/docs.
- Phân biệt production path với dev/synthetic tooling.
- Ghi rõ ảnh hưởng dự kiến của quyết định JobApplication chat chuyển sang full CV markdown.
```

## Acceptance criteria

1. P1-A có thể lấy inventory để review prompt mà không phải tự tìm lại toàn bộ entry point.
2. Future LLM refactor có caller map và fallback map đủ rõ.
3. User nhìn inventory biết đâu là AI use case lõi, đâu là helper, đâu là dev tooling.
