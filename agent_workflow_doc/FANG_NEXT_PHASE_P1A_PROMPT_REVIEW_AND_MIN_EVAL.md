# P1-A Prompt Review and P1-B Minimal Eval

## Brief

Tài liệu này gom P1-A và P1-B cho cùng một owner. Người phụ trách review prompt phải đồng thời dựng eval tối thiểu để rubric review không dừng ở nhận xét lý thuyết và để các prompt quan trọng có case kiểm tra đầu tiên. Cụm này được giao sau P0-B/P0-C và sau khi user bổ sung hướng dẫn triển khai cần thiết.

## Mục tiêu

1. Review toàn bộ prompt production-relevant theo inventory P0-B.
2. Đánh giá prompt theo task boundary, grounding, security, compliance, output contract và observability.
3. Đề xuất prompt redesign theo thứ tự ưu tiên tính năng.
4. Tạo eval tối thiểu cho những prompt/use case quan trọng nhất trước.

## Dependency

Ưu tiên đầu vào:

1. P0-B AI/LLM Inventory.
2. P0-C Documentation Reconciliation.
3. Quyết định đã chốt rằng JobApplication chat sẽ chuyển sang full CV markdown context.
4. Hướng dẫn bổ sung trực tiếp từ user trước khi giao việc cho thành viên.

Nếu P0-B chưa xong, owner được phép tự lập danh sách entry point tạm thời nhưng phải ghi rõ phần nào cần reconcile lại sau.

## Prompt groups phải xét

1. CV parser.
2. JobApplication chat prompt/context policy hiện tại và hướng full-CV.
3. Chat summarization/branch.
4. NMAIex province mapper.
5. NMAIex skill mapper.
6. Language proficiency normalization.
7. Prompt trong synthetic/dev tooling chỉ review sau nếu nó ảnh hưởng dữ liệu test/chất lượng ranking.

## Rubric review

Mỗi prompt phải được đánh giá theo các câu hỏi sau:

1. **Task boundary**
   - Model được phép làm gì.
   - Model không được phép làm gì.
2. **Grounding**
   - Dữ liệu nào là bằng chứng.
   - Khi thiếu dữ liệu có policy rõ không.
   - Có tách evidence và inference không.
3. **Security**
   - CV/JD/ATS text có được coi là untrusted input không.
   - Có nguy cơ prompt injection hoặc data exfiltration không.
4. **HR/compliance risk**
   - Có đẩy model sang quyết định tuyển dụng tuyệt đối, đánh giá thiếu căn cứ hoặc suy đoán nhạy cảm không.
5. **Output contract**
   - Free text/JSON/schema có rõ không.
   - Validation/fallback phía code có khớp prompt không.
6. **Operational quality**
   - Prompt có versioning/observability/test case chưa.
   - Có nằm inline khó quản lý không.

## Deliverables

1. **Prompt review report**
   - Bảng prompt/use case.
   - Điểm rủi ro.
   - Vấn đề cụ thể có file refs.
   - Thứ tự ưu tiên nâng cấp.
2. **Prompt redesign proposals**
   - Không nhất thiết rewrite tất cả ngay.
   - Với prompt priority cao phải có draft mới hoặc spec rewrite rõ.
3. **Minimal eval plan + seed cases**
   - Case format.
   - Rubric/assertions.
   - Case tối thiểu cho prompt priority cao.
4. **Open questions**
   - Những chỗ cần user/tier 1 quyết định.

## Eval tối thiểu trước

Không làm eval platform lớn ngay. Bắt đầu bằng seed cases cho:

1. CV parser:
   - field có trong CV phải extract được,
   - field không có không được bịa,
   - CV mơ hồ/lỗi có warning hoặc failure behavior đúng theo policy.
2. JobApplication chat:
   - trả lời từ full CV/JD/ATS context,
   - nói thiếu dữ liệu khi không có bằng chứng,
   - không làm theo instruction độc hại nằm trong CV/JD text.
3. NMAIex mapper:
   - province mapping cases.
   - skill mapping exact/unmatched cases.
   - language proficiency normalization cases.

## Ghi chú parser quality

Có ý tưởng bổ sung tín hiệu để parser báo mức tự tin/lỗi/warnings nhằm giúp xét leo Pro tier. Owner P1 phải:

1. Ghi rõ phần nào model tự báo, phần nào deterministic validator xác nhận.
2. Không coi self-reported confidence là chân lý duy nhất.
3. Đề xuất policy kết hợp prompt, schema, warning fields, quality gate và escalation.

## Cách giao cho thành viên

Owner của cụm này chịu trách nhiệm từ review đến eval seed. Không tách người review prompt và người làm eval tối thiểu ở pha đầu để tránh lệch rubric.

Owner cụm P1-A/P1-B cũng sẽ hỗ trợ người làm JobApplication Full-CV Chat sau khi người đó hoàn thành prompt engineering mức cơ bản cho luồng chat mới. Trách nhiệm hỗ trợ gồm review prompt, bổ sung guardrail và đề xuất eval tối thiểu cho luồng mới; không tự ý đổi implementation scope của người làm JobApplication nếu chưa có user/tier 1 duyệt.

Owner không được:

- tự đổi kiến trúc LLM layer,
- tự đổi flow JobPosting Agent,
- tự chuyển JobApplication chat sang full CV nếu chưa có guide feature riêng,
- rewrite prompt production mà không chỉ ra test/eval/risk đi kèm.

## Prompt giao việc

```text
Bạn phụ trách cụm P1-A Prompt Review và P1-B Minimal Eval cho FANG.

Đọc trước:
- agent_workflow_doc/FANG_NEXT_PHASE_P1A_PROMPT_REVIEW_AND_MIN_EVAL.md
- P0-B AI/LLM Inventory nếu đã có
- P0-C Documentation Reconciliation nếu đã có
- Các file prompt/use case được inventory chỉ ra
- Hướng dẫn bổ sung trực tiếp từ user cho cụm prompt/eval

Mục tiêu:
1. Review prompt production-relevant theo rubric task boundary, grounding, security, HR/compliance risk, output contract và operational quality.
2. Lập báo cáo prompt review có file references và thứ tự ưu tiên.
3. Đề xuất redesign cho prompt priority cao.
4. Dựng eval tối thiểu đầu tiên cho các prompt/use case quan trọng thay vì chỉ viết nhận xét.

Ràng buộc:
- Không tự đổi kiến trúc provider/agent/framework.
- Quyết định đã chốt: JobApplication chat sẽ chuyển sang full CV markdown context, nhưng feature implementation sẽ có guide riêng.
- Nếu phát hiện prompt cần quyết định sản phẩm/kiến trúc mới, ghi open question thay vì tự khóa hướng.

Output:
- Prompt review report.
- Prompt redesign proposals hoặc rewrite spec cho prompt priority cao.
- Minimal eval plan và seed cases.
- Danh sách open questions/risks cần user hoặc tier 1 review.
```

## Acceptance criteria

1. Không bỏ sót prompt production-relevant đã có trong P0-B.
2. Mỗi nhận xét chính có file reference và rubric reason.
3. Có eval seed thực tế cho prompt priority cao, không chỉ backlog chung chung.
4. Parser quality/warning/confidence idea được phân tích với guardrail rõ.
