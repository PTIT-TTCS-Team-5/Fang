# agent_workflow_doc README

Thư mục này chứa tài liệu điều phối agent/thành viên cho FANG. Đây không phải source code runtime; mục tiêu là giúp người mới biết đọc gì trước, tài liệu nào là active, tài liệu nào chỉ còn giá trị lịch sử.

## Đọc trước khi nhận task

Mọi thành viên/agent nên đọc theo thứ tự:

1. `README.md` ở root repo FANG.
2. `agent_workflow_doc/README.md` - file này.
3. `agent_workflow_doc/KINH_NGHIEM.md`.
4. `docs/system_architecture.md`.
5. `agent_workflow_doc/FANG_NEXT_PHASE_DECISIONS.md`.
6. File assignment cụ thể của mình.
7. Các strategy/guide được assignment yêu cầu.
8. Nếu task đụng frontend, đọc thêm `../miCareer-mini/README.md`.

Không dùng `docs/research/` hoặc `agent_workflow_doc/archive/` làm current runtime truth trừ khi assignment yêu cầu đọc như historical background.

## Active decision docs

| File | Vai trò |
|---|---|
| `FANG_NEXT_PHASE_DECISIONS.md` | Decision source cho giai đoạn next phase. |
| `FANG_NEXT_PHASE_P0D_HANDOFF_AND_ASSIGNMENT.md` | Tổng hợp P0-D, trạng thái P0-A/B/C và option cho thành viên thứ ba. |
| `FANG_NEXT_PHASE_9ROUTER_DEEP_RESEARCH_PROMPT.md` | Prompt nghiên cứu 9Router/framework, chưa phải implementation plan. |
| `AI_WORKFLOW_INIT.md` | Hướng dẫn khởi động context cho agent. |
| `AI_MANUAL_UPDATE.md` | Ghi chú cập nhật thủ công khi có thay đổi lớn. |
| `KINH_NGHIEM.md` | Kinh nghiệm làm việc với agent/model trong repo. |
| `GIT_WORKFLOW_GUIDE.md` | Quy ước git/worktree. |

## Active assignment docs

| File | Owner/scope |
|---|---|
| `FANG_NEXT_PHASE_P1A_PROMPT_REVIEW_AND_MIN_EVAL.md` | `P1_A_B_inc`: Prompt Review + Minimal Eval. |
| `FANG_NEXT_PHASE_CHAT_FULL_CV_ASSIGNMENT.md` | `CHAT_FULL_CV`: JobApplication Full-CV Chat. |

Mọi assignment lớn phải yêu cầu:

1. report bằng tiếng Việt,
2. tài liệu strategy-level nếu thay đổi behavior/architecture,
3. tests hoặc checklist verify tương ứng,
4. open questions rõ nếu gặp quyết định ngoài scope.

## P0 input/output docs

| File | Trạng thái |
|---|---|
| `FANG_NEXT_PHASE_P0A_REPO_REALITY_AUDIT.md` | Spec/prompt đầu vào P0-A. |
| `FANG_NEXT_PHASE_P0A_REPO_REALITY_AUDIT_REPORT.md` | Report P0-A. Dùng để truy vết reality tại thời điểm audit và note của user. |
| `FANG_NEXT_PHASE_P0A_USER_NOTE_TRIAGE.md` | Triage note user, phân nhóm `P1_A_B_inc`, `CHAT_FULL_CV`, tier 1, tier 2. |
| `FANG_NEXT_PHASE_P0B_AI_LLM_INVENTORY.md` | Spec/prompt đầu vào P0-B. |
| `P0B_AI_LLM_INVENTORY_REPORT.md` | Report P0-B, nguồn chuẩn cho prompt/use case/model/fallback inventory. |
| `FANG_NEXT_PHASE_P0C_DOC_RECONCILIATION.md` | Spec/prompt đầu vào P0-C. |
| `P0C_DOC_RECONCILIATION_PLAN.md` | Plan/report P0-C, nguồn đối chiếu docs drift. |

P0-A/B/C đã đủ để handoff. Khi thấy mâu thuẫn giữa report cũ và code mới, code hiện tại là truth source và phải ghi conflict trong report.

## Active reference data

| File | Vai trò |
|---|---|
| `[NMAIex]_PROVINCE_MERGER_GUIDE.md` | Reference về mapping tỉnh thành NMAIex. |

## Archive

`archive/` chứa tài liệu historical, checklist cũ, walkthrough và prompt tier 2 đã hoàn tất. Không sửa nội dung archive trừ khi cần cập nhật index/README.

Các file trong `archive/tier2_completed_tasks/` là prompt giao việc đã dùng xong, không phải task mở.

## Quy tắc khi thêm tài liệu mới

1. Tên file nên nêu rõ phase/scope, ví dụ `FANG_NEXT_PHASE_*`.
2. Nếu là assignment, ghi rõ owner, scope, deliverables, acceptance criteria và out-of-scope.
3. Nếu là report, ghi rõ ngày, input, lệnh đã chạy, findings, evidence và residual risks.
4. Nếu là strategy-level doc, nên đặt trong `docs/strategy/` trừ khi nó chỉ phục vụ điều phối agent.
5. Nếu thay thế tài liệu strategy/guide lớn, archive bản cũ trước khi rewrite.
