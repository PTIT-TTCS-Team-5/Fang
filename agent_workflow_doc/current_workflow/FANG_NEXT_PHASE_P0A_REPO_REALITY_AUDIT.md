# P0-A Repo Reality Audit

## Brief

P0-A dùng model tier 1 để dựng lại bức tranh thực tế của FANG từ codebase hiện tại, sau đó giao các phần audit/report đã được spec rõ cho tier 2 nếu cần. Đây là bước chạy đầu tiên trong kế hoạch hiện tại, trước P0-B và P0-C. Output của P0-A phải đủ tin cậy để user/tier 1 resolve conflict và để các workstream sau không tiếp tục dựa vào tài liệu cũ hoặc giả định sai.

## Mục tiêu

1. Xác định FANG hiện làm gì thật trong code.
2. Đối chiếu kiến trúc, API, DB, docs, tests và workflow agent hiện có.
* NOTE FROM USER: đánh dấu những file trong agent_workflow_doc đã xong
3. Tách rõ:
   - current reality,
   - code-doc drift,
   - dead/stale documentation,
   - chỗ cần decision chứ chưa được sửa ngay.
4. Sinh work packages rõ cho tier 2 hoặc thành viên khác.

## Phạm vi

### In scope

- Root README.
- `app/`, `database/`, `tests/`, `smoke_tests/`, `scripts/`.
- `docs/strategy`, `docs/guide`, `docs/system_architecture.md`, `docs/testing_guide.md`.
- `agent_workflow_doc` đang điều phối công việc (FANG_NEXT_PHASE là những thứ mới nhất, đang được triển khai)
- Các điểm giao thoa với NMAIex nếu ảnh hưởng FANG core.
* NOTE FROM USER: Thực tế nmaiex đã được user quyết định là một phần chính thức của FANG rồi, vẫn giữ tên gọi cũ để dễ nhận biết thôi -> Cần cập nhật các tài liệu coi nmaiex tách biệt khỏi FANG

### Out of scope

- Không refactor code trong pha audit.
- Không viết lại toàn bộ docs ngay trong P0-A.
- Không quyết định thay framework agent/LLM provider nếu audit chưa chỉ ra nhu cầu.
- Không đọc mọi research/archive dài nếu không cần xác nhận drift hoặc bối cảnh quyết định.
* NOTE FROM USER: Các research thì không nên đọc, research dài và mang tính nhiễu cao, chỉ một phần trong đó được triển khai thực tế. Research chủ yếu hỗ trợ quyết định của user và là ground-of-truth cho các quyết định cho hệ thống chứ không liên quan gì tới hệ thống thật

## File bắt đầu đọc

1. `README.md`
2. `docs/system_architecture.md`
3. `docs/strategy/README.md`
4. `docs/guide/README.md`
5. `agent_workflow_doc/KINH_NGHIEM.md`
6. `agent_workflow_doc/AI_WORKFLOW_INIT.md`
7. `app/main.py`
8. `app/api/`
9. `app/services/`
10. `tests/unit/`
11. `smoke_tests/`

Tier 1 được phép tỏa ra các file khác khi cần xác nhận nhận xét.

## Output bắt buộc

Tạo một tài liệu audit chính và phụ lục khi cần. Tên file do tier 1 đề xuất nhưng phải đặt trong `agent_workflow_doc` hoặc thư mục docs được chỉ định rõ trong report.
* NOTE FROM USER: Viết bằng tiếng Việt, các thuật ngữ chuyên ngành/đặc thù/rõ nghĩa thì giữ nguyên tiếng Anh

Tài liệu audit chính phải có:

1. Executive summary.
2. Current architecture reality.
3. Feature reality map:
   - implemented,
   - partial,
   - documented-only,
   - stale/legacy.
4. Code-doc drift map có file references.
5. Test/verification reality map.
6. Risk list.
7. Work packages tiếp theo.
8. Những câu hỏi hoặc decision memo cần user chốt.

## Tiêu chí chất lượng

- Nhận xét quan trọng phải dẫn file path cụ thể.
- Khi code và docs mâu thuẫn, ghi conflict; không tự mặc định docs đúng.
- Tách rõ phát hiện thực tế với đề xuất.
- Work package phải đủ hẹp để giao được.
- Nếu tier 2 được giao thực thi một phần audit, tier 1 phải chỉ định rõ checklist, file scope và report format.

## Cách dùng tier 1 và tier 2

1. User chạy tier 1 với prompt dưới đây để có bản audit direction đầu tiên.
2. Nếu tier 1 tách được checklist hẹp, giao tier 2 kiểm tra phần đó:
   - API/docs drift,
   - tests/docs drift,
   - file map của một module.
3. Tier 2 trả report, không tự chốt kiến trúc.
4. Tier 1 hợp nhất và review kết quả.

## Prompt cho GPT-5.5 hoặc Claude Opus 4.6

```text
Đọc repo FANG hiện tại để thực hiện P0-A Repo Reality Audit.

Bối cảnh:
- Repo đã phát triển qua nhiều pha; code, strategy, guide, workflow docs và tests có thể đã drift.
- Mục tiêu của pha này không phải code feature mà là xác định current reality đáng tin cậy để các pha sau làm việc.
- Khi code và docs mâu thuẫn, hãy ghi conflict rõ, dẫn file path và giải thích vì sao conflict quan trọng.

Phạm vi đọc ban đầu:
- README.md
- docs/system_architecture.md
- docs/strategy và docs/guide
- docs/testing_guide.md
- agent_workflow_doc/KINH_NGHIEM.md và AI_WORKFLOW_INIT.md
- app/main.py, app/api, app/services, app/models, app/core
- tests/unit, smoke_tests, scripts, database nếu cần xác nhận behavior

Yêu cầu:
1. Dựng current architecture reality từ code.
2. Lập feature reality map: implemented, partial, documented-only, stale/legacy.
3. Lập code-doc drift map có file references cụ thể.
4. Lập test/verification reality map.
5. Xác định risk và những quyết định chưa nên tự chốt.
6. Sinh work packages đủ rõ để tier-2 model hoặc thành viên nhóm làm theo.

Output:
- Không sửa code.
- Tạo tài liệu audit chính trong agent_workflow_doc, tên file rõ nghĩa.
- Nếu cần phụ lục/checklist cho tier 2, tạo chúng riêng và liên kết từ audit chính.
- Mỗi nhận xét quan trọng phải có file path tham chiếu.
- Mỗi work package phải có goal, why, scope/out-of-scope, files to inspect, output, acceptance criteria, execution owner/model tier và review requirement.
```

## Acceptance criteria

1. Có một audit document mà user đọc được để biết repo hiện tại đang thật sự ở đâu.
2. Có drift map đủ cụ thể để P0-C dùng làm đầu vào chuẩn hóa tài liệu.
3. Có work package không phụ thuộc vào phỏng đoán mơ hồ.
4. Không có code change phát sinh từ audit này trừ khi user mở task riêng.
