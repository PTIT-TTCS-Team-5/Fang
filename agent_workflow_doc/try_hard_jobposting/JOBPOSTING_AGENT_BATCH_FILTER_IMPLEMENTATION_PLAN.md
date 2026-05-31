# JobPosting Agent Batch Filter Implementation Plan

## Summary

This phase upgrades the JobPosting Agent from broad text search and ranking-only workflows into structured batch filtering for HR. Single-candidate questions continue to use summary/full-CV tools. Multi-candidate questions now use deterministic tools for language certificates, skills, seniority, work location, salary expectation, education level, and ranking explainability.

## Implemented Changes

- Added Vietnamese ranking labels:
  - `Ứng viên nổi trội`: `match_score >= 0.70`
  - `Mức độ phù hợp cao`: `0.55 <= match_score < 0.70`
  - `Mức độ phù hợp tốt`: `0.35 <= match_score < 0.55`
  - `Cần đánh giá thêm`: `0.15 <= match_score < 0.35`
  - `Tín hiệu phù hợp thấp`: `match_score < 0.15`
- Kept raw ranking scores un-clipped when `nmaiex_enable_score_clip=false`.
- Added ranking explanation fields using score breakdown, seniority signal, language bonus/penalty, and evidence.
- Added language bonus/penalty to J-to-C ranking score breakdown.
- Added structured batch tools:
  - `find_candidates_by_language_certificate`
  - `filter_candidates_by_skills`
  - `filter_candidates_by_seniority`
  - `filter_candidates_by_work_location`
  - `filter_candidates_by_salary_expectation`
  - `filter_candidates_by_education_level`
- Added sanitized `resultPreview` to tool calls so the frontend can show useful command output without raw PII or full CV text.

## Tool Contracts

- `find_candidates_by_language_certificate`: uses `CANDIDATELANGUAGECERTIFICATE`, `CANDIDATELANGUAGE`, and `LANGUAGECERTIFICATE`; supports certificate, language, score range, proficiency, and limit.
- `filter_candidates_by_skills`: uses catalog skills and raw skill text; returns matched/missing skills, exact overlap, fuzzy overlap, skill score, and evidence.
- `filter_candidates_by_seniority`: uses `JOB_LEVEL_MAP`, `JOBLEVEL`, and `CANDIDATE.expyears`; returns underqualified/fit/overqualified and year gap.
- `filter_candidates_by_work_location`: uses `PROVINCE`, candidate `user.provId`, job province, and `workMode`; remote jobs do not exclude candidates by province.
- `filter_candidates_by_salary_expectation`: compares job salary range with candidate expectation estimated from offer history, CV expected salary, or experience/location fallback.
- `filter_candidates_by_education_level`: parses `CVPARSED.parsedJson.education` and normalizes high school, college/vocational, bachelor, master, and phd levels.

## Runtime And UI

- Agent prompt now routes certificate/range, skill, seniority, location, salary, education, top/compare, and single-candidate questions to the correct tool family.
- Top/compare answers must use ranking `explanation`, `match_label`, and `score_breakdown` as the primary evidence.
- Tool results now include `resultPreview` and are persisted in tool result metadata and tool call logs.
- `miCareer-mini` renders `resultPreview` or persisted `content.preview` in a scrollable JSON block under "Kết quả lệnh".

## Test Coverage

- Ranking label and explanation are covered in JobPosting Agent tool tests.
- Language certificate filtering covers TOEIC score threshold behavior.
- Work location filtering covers remote-inclusive matching.
- Education filtering covers bachelor normalization.
- Runtime tests cover `resultPreview` presence on tool calls.

## Future Work

Do not add professional certification filtering until the core schema has a normalized certification catalog similar to `LANGUAGECERTIFICATE`, plus candidate-certification mapping and enrichment/backfill logic.
