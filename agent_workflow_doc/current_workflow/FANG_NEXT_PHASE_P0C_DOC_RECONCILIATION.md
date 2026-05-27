# P0-C Documentation Reconciliation

## Brief

P0-C được làm sau P0-A và P0-B trong kế hoạch hiện tại. Mục tiêu là chuẩn hóa quan hệ giữa code hiện tại và tài liệu hiện tại sau khi đã có current reality, AI/LLM inventory và các quyết định resolve conflict cần thiết. User dùng model tier 1 để quyết định truth source, plan cập nhật và review; model tier 2 thực thi các sửa đổi đã được chỉ định rõ.

## Mục tiêu

1. Xác định tài liệu nào đang là canonical cho từng chủ đề.
2. Phân loại drift để biết sửa docs theo code, sửa code theo quyết định đã chốt, archive tài liệu cũ hay cần decision memo.
3. Tạo kế hoạch cập nhật tài liệu chi tiết cho tier 2 dựa trên P0-A, P0-B và quyết định của user/tier 1.
4. Sau khi tier 2 sửa, có report và review để tránh tạo drift mới.

## Nguyên tắc

1. Không cập nhật tài liệu hàng loạt theo cảm giác.
2. Không coi docs hoặc code luôn đúng tuyệt đối; dùng quyết định hiện tại của user để xử lý conflict.
3. Không để tài liệu strategy và guide mô tả behavior đã bị quyết định thay đổi mà không gắn trạng thái rõ.
4. Tài liệu mới phải có ownership và mục đích rõ:
   - strategy trả lời "tại sao",
   - guide trả lời "làm thế nào",
   - workflow doc trả lời "ai/agent làm gì tiếp".
5. Khi thay đổi hoặc thay thế tài liệu strategy/guide cũ, đặc biệt các phần như RAG chat cũ, cần cân nhắc đưa bản cũ vào `docs/archive` thay vì ghi đè làm mất lịch sử quyết định.

## Drift classes

| Class | Ý nghĩa | Hướng xử lý |
|---|---|---|
| D1 | Code là reality, docs cũ | Sửa docs theo code hoặc đánh dấu legacy. |
| D2 | Docs là quyết định đã chốt nhưng code chưa kịp theo | Giữ docs, tạo implementation work package. |
| D3 | Docs và code đều cũ vì user vừa đổi quyết định | Viết decision/update plan trước. |
| D4 | Hai docs mâu thuẫn nhau | Chọn truth source hoặc archive/merge. |
| D5 | Docs nói có test/file/flow nhưng repo không có | Sửa docs và/hoặc tạo test gap work package. |

## File bắt đầu đọc

0. Output của P0-A và P0-B nếu đã có.
1. `README.md`
2. `docs/system_architecture.md`
3. `docs/testing_guide.md`
4. `docs/strategy/`
5. `docs/guide/`
6. `agent_workflow_doc/AI_WORKFLOW_INIT.md`
7. `agent_workflow_doc/AI_MANUAL_UPDATE.md`
8. `agent_workflow_doc/KINH_NGHIEM.md`
9. `app/`, `tests/`, `smoke_tests/` để xác nhận docs quan trọng.

## Output pha tier 1

Tier 1 phải tạo:

1. **Documentation truth-source map**
   - Chủ đề nào dùng file nào làm nguồn chuẩn.
2. **Drift register**
   - Mỗi drift có class D1-D5, impact, file refs và hướng xử lý.
3. **Tier-2 execution checklist**
   - Tài liệu nào sửa.
   - Sửa theo hướng nào.
   - Chỗ nào không được đụng.
   - Acceptance criteria.
4. **Review checklist**
   - Dùng để tier 1 kiểm tra report và diff sau khi tier 2 làm.

## Prompt cho tier 1

```text
Thực hiện P0-C Documentation Reconciliation cho FANG. Pha này được làm sau P0-A Repo Reality Audit và P0-B AI/LLM Inventory.

Bối cảnh:
- Repo đã có strategy, guide, testing docs và agent workflow docs phát triển qua nhiều pha.
- Code và docs có thể drift.
- P0-A và P0-B đã hoặc sẽ cung cấp current reality, drift map và AI/LLM inventory. Nếu output đó tồn tại, hãy đọc trước và dùng làm input chính.
- Có quyết định mới đã chốt: JobApplication chat sẽ bỏ fixed chunk-RAG và chuyển sang full CV markdown context, nhưng việc implementation sẽ có work package riêng.

Mục tiêu:
1. Xác định truth source map cho tài liệu hiện tại.
2. Lập drift register giữa code và docs.
3. Phân loại từng drift theo:
   D1 code reality/docs cũ,
   D2 docs là quyết định/code chưa theo,
   D3 docs và code đều cần cập nhật vì quyết định mới,
   D4 docs mâu thuẫn docs,
   D5 docs nói có file/test/flow nhưng repo không có.
4. Tạo checklist thực thi cực rõ cho model tier 2 cập nhật tài liệu.

Phạm vi đọc ban đầu:
- README.md
- docs/system_architecture.md
- docs/testing_guide.md
- docs/strategy, docs/guide
- agent_workflow_doc/AI_WORKFLOW_INIT.md, AI_MANUAL_UPDATE.md, KINH_NGHIEM.md
- app/tests/smoke_tests ở mức cần để xác nhận docs

Output:
- Không sửa code feature.
- Tạo tài liệu plan trong agent_workflow_doc gồm truth-source map, drift register, tier-2 checklist và review checklist.
- Dẫn file path cụ thể.
- Khi một conflict cần user quyết định thì dừng ở register, không tự chế truth source.
```

## Prompt cho tier 2 sau khi có plan

Tier 1 phải thay placeholder trong prompt này bằng checklist cụ thể:

```text
Đọc tài liệu P0-C plan đã được tier 1 tạo và chỉ thực thi các mục nằm trong Tier-2 execution checklist.

Ràng buộc:
- Không đổi kiến trúc hoặc behavior code.
- Không sửa file ngoài checklist nếu chưa ghi rõ lý do trong report.
- Khi gặp conflict mới chưa có trong drift register, ghi lại và dừng mục đó thay vì tự quyết.
- Giữ strategy, guide và workflow docs đúng vai trò của chúng.

Output:
1. Cập nhật docs theo checklist.
2. Tạo report ngắn:
   - mục nào đã sửa,
   - file nào đã sửa,
   - mục nào bị block/conflict,
   - tài liệu nào cần tier 1 review kỹ.
3. Chạy kiểm tra markdown/link/file reference cơ bản nếu repo có cách phù hợp; nếu không có thì ghi rõ chưa chạy được.
```

## Acceptance criteria

1. Có plan tier 1 trước khi tier 2 sửa tài liệu.
2. Mọi docs change lớn truy được về drift register hoặc quyết định mới.
3. Sau P0-C, README/strategy/guide/workflow không mâu thuẫn hiển nhiên ở các chủ đề đang làm tiếp.
4. Drift liên quan behavior chưa implement được ghi rõ thay vì bị docs che mất.
