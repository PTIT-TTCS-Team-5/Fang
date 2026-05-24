# FANG Next Phase Tier-2 Task: NMAIex Language Docs Reconciliation

## Brief

Cập nhật docs về NMAIex language system theo code reality hiện tại. Task này là docs-only reconciliation hẹp, không implement endpoint mới.

## Bối cảnh

P0-A report phát hiện:

- NMAIex language system là partial:
  - DB và scoring tồn tại.
  - Language scoring được dùng trong ranking.
  - Docs có chỗ nói master language endpoint chưa implemented.
- User note: "NMAIex language system": sửa docs theo code.
- User cũng note `/v2/nmaiex/master/languages` sẽ sửa trong P0-C.

Task này có thể làm trước P0-C nếu giữ phạm vi hẹp: chỉ reconcile docs theo code, không đổi API behavior.

## Goal

Làm docs NMAIex language không mâu thuẫn với code hiện tại: phần nào đã có thì nói đã có, phần nào chưa có endpoint thì nói rõ chưa có hoặc planned.

## Scope

Được đọc:

- `app/api/nmaiex_routes_ranking.py`
- `app/api/nmaiex_routes_management.py`
- `app/services/nmaiex_ranking_service.py`
- `app/services/nmaiex_mapper_service.py`
- `database/schema_web_core.sql`
- `docs/guide/nmaiex_ranking_guide.md`
- `docs/strategy/nmaiex_ranking_strategy.md`
- `README.md` nếu có nhắc master data/language

Được sửa:

- `docs/guide/nmaiex_ranking_guide.md`
- `docs/strategy/nmaiex_ranking_strategy.md`
- `README.md` chỉ nếu có câu sai trực tiếp về NMAIex language/master data

## Out of Scope

- Không implement `/v2/nmaiex/master/languages` nếu code chưa có.
- Không sửa scoring formula.
- Không sửa mapper prompt/model routing.
- Không sửa DB schema.
- Không sửa frontend checklist trong task này.

## Required Work

1. Xác nhận trong code:
   - table language hiện có trong schema;
   - ranking có dùng language score không;
   - API master language endpoint hiện có hay chưa;
   - mapper có normalize language proficiency không.
2. Cập nhật docs theo mẫu semantic rõ:
   - "Implemented": DB/scoring/mapping phần nào có thật.
   - "Not implemented / planned": endpoint hoặc API surface nào chưa có.
   - "Do not call": nếu route không tồn tại.
3. Nếu docs đang nói language hoàn toàn chưa có nhưng code có scoring, sửa lại.
4. Nếu docs đang nói endpoint đã có nhưng code chưa có, sửa lại.

## Acceptance Criteria

- Docs không còn mâu thuẫn hiển nhiên với code về NMAIex language.
- Không có docs claim endpoint `/v2/nmaiex/master/languages` là available nếu code chưa mount route đó.
- Nếu endpoint chưa có, docs phải nói rõ đây là gap/planned.
- Có file path/code reference trong report cho kết luận chính.

## Report Format

```text
Task: NMAIex Language Docs Reconciliation
Files changed:
- ...

Code reality confirmed:
- DB:
- Ranking:
- Mapper:
- API endpoint:

Docs updates:
- ...

Remaining gaps:
- ...

Notes for tier 1:
- ...
```

## Guardrails

- Nếu phát hiện code đã có endpoint language nhưng docs nói chưa có, sửa docs theo code và báo rõ.
- Nếu phát hiện code không nhất quán giữa route/ranking/schema, không tự sửa code; ghi conflict cho tier 1.
