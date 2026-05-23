# FANG Next Phase Tier-2 Task: Archive Synthetic Data and NMAIex Tuning Checklists

## Brief

Dọn các checklist/task cũ liên quan synthetic data, ground truth và NMAIex tuning. User xác nhận các phần synthetic data + gán nhãn `build_ground_truth` + tuning thực tế đã xong, nên không cố sửa từng checkbox cũ. Task này là workflow doc cleanup, không đụng runtime code.

## Bối cảnh

P0-A report ghi:

- `task_data_set.md` còn unchecked nhưng user xác nhận thực tế đã done.
- `task_nmaiex_tuning_6h.md` done.
- `task_nmaiex_tuning.md` done/historical.
- Các implementation plan tuning/data set có thể giữ historical nếu còn hữu ích, nhưng không dùng làm current truth.

Quyết định user:

- Đưa các checklist cũ vào archive hoặc mark historical.
- Không cố quay lại reconcile từng checkbox.

## Goal

Làm rõ trong `agent_workflow_doc` rằng các checklist synthetic/tuning cũ là historical/archived, tránh để model hoặc thành viên nhóm đọc nhầm là việc còn đang mở.

## Scope

Được đọc/sửa:

- `agent_workflow_doc/task_data_set.md`
- `agent_workflow_doc/task_nmaiex_tuning.md`
- `agent_workflow_doc/task_nmaiex_tuning_6h.md`
- `agent_workflow_doc/implementation_plan_data_set.md`
- `agent_workflow_doc/implementation_plan_nmaiex_tuning.md`
- `agent_workflow_doc/implementation_plan_nmaiex_tuning_6h.md`
- Có thể tạo `agent_workflow_doc/archive/` nếu chưa tồn tại
- Có thể tạo/update một `agent_workflow_doc/archive/README.md`

## Out of Scope

- Không sửa `synthetic_data/`.
- Không sửa `nmaiex_tuning/`.
- Không chạy tuning/generation/build_ground_truth.
- Không sửa checklist backend/frontend NMAIex trong task này.
- Không đổi quyết định P0/P1.

## Required Work

Chọn một trong hai hướng, ưu tiên hướng A nếu không có ràng buộc link nội bộ:

### Hướng A: Move to Archive

1. Tạo `agent_workflow_doc/archive/` nếu chưa có.
2. Di chuyển các file sau vào archive:
   - `task_data_set.md`
   - `task_nmaiex_tuning.md`
   - `task_nmaiex_tuning_6h.md`
3. Với implementation plans liên quan, cân nhắc:
   - nếu rõ là historical, di chuyển vào archive;
   - nếu vẫn cần tham khảo ở root, giữ lại nhưng thêm header `Historical context`.
4. Tạo/update `agent_workflow_doc/archive/README.md` mô tả vì sao archive và không dùng làm current task source.

### Hướng B: Mark Historical In Place

Chỉ dùng nếu move file làm hỏng nhiều reference:

1. Thêm header ngắn ở đầu mỗi file:

```markdown
> Historical/archive note: User confirmed this work is done as of 2026-05-23. This file is kept for context only and is not a current execution checklist.
```

2. Không chỉnh từng checkbox.

## Acceptance Criteria

- Người đọc `agent_workflow_doc` không còn hiểu nhầm các checklist synthetic/tuning là việc còn mở.
- Không mất nội dung lịch sử; chỉ move/archive hoặc mark historical.
- Có report liệt kê file đã move/mark.
- Không đụng runtime code/data.

## Report Format

```text
Task: Synthetic/Tuning Checklist Archive
Approach used:
- Move to archive / Mark historical in place

Files moved/changed:
- ...

References checked:
- ...

Remaining historical docs:
- ...

Notes for tier 1:
- ...
```

## Guardrails

- Không dùng `git reset`, không xóa hẳn file lịch sử.
- Nếu file path đang được reference trong `FANG_NEXT_PHASE_DECISIONS.md` hoặc active P0 docs, update reference hoặc báo tier 1 trước khi move.
