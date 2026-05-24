# FANG Next Phase Tier-2 Task: NMAIex Env Template Dedup

## Brief

Dọn duplicate `.env.nmaiex.example`. User đã chốt root `.env.nmaiex.example` là truth source, bỏ `app/core/.env.nmaiex.example`.

## Bối cảnh

P0-A report phát hiện:

- Repo có cả root `.env.nmaiex.example` và `app/core/.env.nmaiex.example`.
- README/docs reference không thống nhất.

User đã chốt:

- Thống nhất dùng root `.env.nmaiex.example`.
- Xóa hoặc archive `app/core/.env.nmaiex.example`.
- Sửa docs/reference theo root file.

## Goal

Chỉ còn một NMAIex env template canonical ở root repo, và docs/onboarding trỏ đúng file đó.

## Scope

Được đọc/sửa:

- `.env.nmaiex.example`
- `app/core/.env.nmaiex.example`
- `README.md`
- `docs/guide/nmaiex_ranking_guide.md`
- `docs/strategy/nmaiex_ranking_strategy.md`
- `agent_workflow_doc/FANG_NEXT_PHASE_P0A_USER_NOTE_TRIAGE.md` chỉ đọc, không sửa
- Các docs khác nếu `rg ".env.nmaiex.example"` tìm thấy reference trực tiếp

## Out of Scope

- Không đổi config loader trong `app/core/nmaiex_config.py` trừ khi code đang hard-code sai path và cần fix cực nhỏ.
- Không đổi env variable names/semantics.
- Không sửa secrets thật hoặc `.env` local.
- Không chỉnh NMAIex scoring/ranking behavior.

## Required Work

1. Chạy search:

```powershell
rg "\.env\.nmaiex\.example|env\.nmaiex" .
```

2. So sánh hai template:
   - Nếu root file đủ nội dung, dùng root làm canonical.
   - Nếu `app/core/.env.nmaiex.example` có key còn thiếu ở root, merge key/comment cần thiết vào root trước.
3. Loại bỏ duplicate `app/core/.env.nmaiex.example` bằng một trong hai cách:
   - ưu tiên delete nếu docs/reference đã được sửa;
   - nếu team muốn giữ lịch sử, move vào archive và ghi rõ deprecated.
4. Cập nhật docs để hướng dẫn copy từ root:

```text
Copy `.env.nmaiex.example` to `.env.nmaiex`
```

5. Không để docs hướng dẫn copy từ `app/core/.env.nmaiex.example`.

## Acceptance Criteria

- Root `.env.nmaiex.example` là template canonical.
- Không còn active docs reference đến `app/core/.env.nmaiex.example`.
- Không mất env keys khi dedup.
- Report ghi rõ đã merge key nào, nếu có.

## Recommended Parallelism

Có thể chạy song song với task unit embedding và synthetic/tuning archive. Nếu cùng lúc có P0-C docs reconciliation, báo cho người làm P0-C biết docs reference đã thay đổi.

## Report Format

```text
Task: NMAIex Env Template Dedup
Files changed/deleted/moved:
- ...

Search command:
- rg "\.env\.nmaiex\.example|env\.nmaiex" .

Template comparison:
- Root-only keys:
- app/core-only keys merged:
- duplicate keys:

Docs references updated:
- ...

Notes for tier 1:
- ...
```

## Guardrails

- Không xóa root `.env.nmaiex.example`.
- Không đưa secret thật vào example file.
- Nếu app code actually loads `app/core/.env.nmaiex.example` as a template path, báo conflict trước khi sửa sâu.
