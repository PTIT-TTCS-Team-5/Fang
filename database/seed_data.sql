-- seed_data.sql — miCareer Lite
-- Thứ tự : schema-> root_data -> seed_data

SET client_encoding TO 'UTF8';

-- 1. COMPANY (5)
INSERT INTO COMPANY (compName, taxCode, webUrl, logoUrl, contactEmail, prov, ward, street) VALUES
('FPT Demo',    '0101248141', 'https://fpt-demo.com',    '/logos/fpt.png',    'hr@fpt-demo.com',           'Hà Nội', 'Phường Dịch Vọng Hậu', 'Số 10 Phạm Văn Bạch'),
('VNG Demo',    '0302553763', 'https://vng-demo.com',    '/logos/vng.png',    'careers@vng-demo.com',       'Hà Nội', 'Phường Mai Dịch',      'Tầng 10 Tòa Keangnam Phạm Hùng'),
('Viettel Demo','0100109106', 'https://viettel-demo.com','/logos/viettel.png','tuyendung@viettel-demo.com', 'Hà Nội', 'Phường Yên Hòa',       'Số 1 Trần Hữu Dực'),
('Tiki Demo',   '0309532909', 'https://tiki-demo.com',   '/logos/tiki.png',   'hr@tiki-demo.com',           'Hà Nội', 'Phường Quang Trung',   '18 Tây Sơn'),
('Momo Demo',   '0313525427', 'https://momo-demo.com',   '/logos/momo.png',   'hr@momo-demo.com',           'Hà Nội', 'Phường Liễu Giai',     '28 Liễu Giai');

-- 2. USER (24: 18 Candidate + 5 HR + 1 Admin)
-- ★ nguyenvanan = MAIN CANDIDATE cho demo (apply 3 job: Backend, Frontend, AI)
INSERT INTO "user" (userName, pwd, fName, lName, email, phone, prov, ward, street, stat, "role") VALUES
('nguyenvanan',    '123456', 'An',      'Nguyễn Văn',  'nguyenvanan@gmail.com',    '0901000001', 'Hà Nội', 'Phường Bách Khoa',        '1 Đại Cồ Việt',          'ACTIVE', 'CANDIDATE'),
('tranthibinh',    '123456', 'Bình',    'Trần Thị',    'tranthibinh@gmail.com',    '0901000002', 'Hà Nội', 'Phường Nhân Chính',       '15 Lê Văn Lương',        'ACTIVE', 'CANDIDATE'),
('levancuong',     '123456', 'Cường',   'Lê Văn',      'levancuong@gmail.com',     '0901000003', 'Hà Nội', 'Phường Quan Hoa',         '22 Nguyễn Khánh Toàn',   'ACTIVE', 'CANDIDATE'),
('phamthidung',    '123456', 'Dung',    'Phạm Thị',    'phamthidung@gmail.com',    '0901000004', 'Hà Nội', 'Phường Trung Hòa',        '30 Trung Kính',          'ACTIVE', 'CANDIDATE'),
('hoangvanduc',    '123456', 'Đức',     'Hoàng Văn',   'hoangvanduc@gmail.com',    '0901000005', 'Hà Nội', 'Phường Thanh Xuân Trung', '50 Nguyễn Trãi',         'ACTIVE', 'CANDIDATE'),
('vuthiphuong',    '123456', 'Phương',  'Vũ Thị',      'vuthiphuong@gmail.com',    '0901000006', 'Hà Nội', 'Phường Thịnh Quang',      '3 Tây Sơn',              'ACTIVE', 'CANDIDATE'),
('dangvangiang',   '123456', 'Giang',   'Đặng Văn',    'dangvangiang@gmail.com',   '0901000007', 'Hà Nội', 'Phường Dịch Vọng',        '100 Xuân Thủy',          'ACTIVE', 'CANDIDATE'),
('buithihuong',    '123456', 'Hương',   'Bùi Thị',     'buithihuong@gmail.com',    '0901000008', 'Hà Nội', 'Phường Thanh Xuân Bắc',   '12 Lê Trọng Tấn',        'ACTIVE', 'CANDIDATE'),
('lyvankhoi',      '123456', 'Khôi',    'Lý Văn',      'lyvankhoi@gmail.com',      '0901000009', 'Hà Nội', 'Phường Nam Đồng',         '8 Hồ Đắc Di',            'ACTIVE', 'CANDIDATE'),
('maithilinh',     '123456', 'Linh',    'Mai Thị',     'maithilinh@gmail.com',     '0901000010', 'Hà Nội', 'Phường Khương Thượng',    '45 Tôn Thất Tùng',       'ACTIVE', 'CANDIDATE'),
('truongvanminh',  '123456', 'Minh',    'Trương Văn',  'truongvanminh@gmail.com',  '0901000011', 'Hà Nội', 'Phường Láng Hạ',          '20 Láng Hạ',             'ACTIVE', 'CANDIDATE'),
('ngothingoc',     '123456', 'Ngọc',    'Ngô Thị',     'ngothingoc@gmail.com',     '0901000012', 'Hà Nội', 'Phường Trung Liệt',       '7 Thái Hà',              'ACTIVE', 'CANDIDATE'),
('dinhvanphong',   '123456', 'Phong',   'Đinh Văn',    'dinhvanphong@gmail.com',   '0901000013', 'Hà Nội', 'Phường Kim Liên',         '55 Phạm Ngọc Thạch',     'ACTIVE', 'CANDIDATE'),
('phamvanquan',    '123456', 'Quân',    'Phạm Văn',    'phamvanquan@gmail.com',    '0901000014', 'Hà Nội', 'Phường Phương Liên',      '18 Đào Duy Anh',          'ACTIVE', 'CANDIDATE'),
('hoangthiquynh',  '123456', 'Quỳnh',   'Hoàng Thị',   'hoangthiquynh@gmail.com',  '0901000015', 'Hà Nội', 'Phường Ô Chợ Dừa',       '10 Hoàng Cầu',            'ACTIVE', 'CANDIDATE'),
('lethithanh',     '123456', 'Thanh',   'Lê Thị',      'lethithanh@gmail.com',     '0901000016', 'Hà Nội', 'Phường Hà Cầu',           '5 Quang Trung',           'ACTIVE', 'CANDIDATE'),
('vuvanthang',     '123456', 'Thắng',   'Vũ Văn',      'vuvanthang@gmail.com',     '0901000017', 'Hà Nội', 'Phường Khương Mai',       '22 Vĩnh Hồ',             'ACTIVE', 'CANDIDATE'),
('dangthiuyen',    '123456', 'Uyên',    'Đặng Thị',    'dangthiuyen@gmail.com',    '0901000018', 'Hà Nội', 'Phường Ngã Tư Sở',        '33 Trường Chinh',         'ACTIVE', 'CANDIDATE'),
('hr_fpt',         '123456', 'Lan',     'Ngô Thị',     'lan.ngo@fpt-demo.com',     '0902000001', 'Hà Nội', 'Phường Dịch Vọng Hậu',   'Tòa nhà FPT',            'ACTIVE', 'HR'),
('hr_vng',         '123456', 'Hùng',    'Đỗ Văn',      'hung.do@vng-demo.com',     '0902000002', 'Hà Nội', 'Phường Mai Dịch',         'Tòa Keangnam',            'ACTIVE', 'HR'),
('hr_viettel',     '123456', 'Mai',     'Bùi Thị',     'mai.bui@viettel-demo.com', '0902000003', 'Hà Nội', 'Phường Yên Hòa',          'Số 1 Trần Hữu Dực',      'ACTIVE', 'HR'),
('hr_tiki',        '123456', 'Tuấn',    'Vũ Minh',     'tuan.vu@tiki-demo.com',    '0902000004', 'Hà Nội', 'Phường Quang Trung',      '18 Tây Sơn',              'ACTIVE', 'HR'),
('hr_momo',        '123456', 'Hà',      'Lý Thu',      'ha.ly@momo-demo.com',      '0902000005', 'Hà Nội', 'Phường Liễu Giai',        '28 Liễu Giai',            'ACTIVE', 'HR'),
('admin_mod',      '123456', 'Trung',   'Trần Đức',    'mod@micareer.vn',          '0903000002', 'Hà Nội', 'Phường Thanh Xuân Trung', '18 Phạm Hùng',            'ACTIVE', 'ADMIN');

-- 3. CANDIDATE (18)
-- ★ MAIN CANDIDATE: nguyenvanan — bio chi tiết
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'nguyenvanan'),
 'Backend Developer với 3 năm kinh nghiệm phát triển ứng dụng web bằng Java/Spring Boot. Tốt nghiệp Cử nhân CNTT tại Học viện Công nghệ Bưu chính Viễn thông (PTIT), loại Giỏi.

Kinh nghiệm:
- 2 năm tại ABC Tech: Phát triển RESTful API cho hệ thống quản lý đơn hàng e-commerce phục vụ 50K+ người dùng. Stack: Java 17, Spring Boot 3, PostgreSQL, Redis, Docker.
- 1 năm tại startup XYZ: Xây dựng microservices cho hệ thống thanh toán. Tích hợp VNPay, Momo. Unit testing với JUnit, Mockito.

Dự án cá nhân:
- Chatbot hỗ trợ khách hàng sử dụng Python, TensorFlow, NLP (xử lý tiếng Việt).
- Portfolio website cá nhân bằng ReactJS + TypeScript.

Kỹ năng mềm: Làm việc nhóm tốt (team 5-8 người), kinh nghiệm code review, mentoring junior. Tiếng Anh đọc hiểu tài liệu kỹ thuật tốt (TOEIC 750).',
 '/cv/nguyenvanan_cv.pdf', '2000-03-15', 3);

INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'tranthibinh'),
 'Frontend Developer 1 năm kinh nghiệm ReactJS, TypeScript. Tốt nghiệp PTIT.', '/cv/tranthibinh_cv.pdf', '2001-07-22', 1);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'levancuong'),
 'Fullstack Developer 3 năm, thành thạo NodeJS + VueJS. Kinh nghiệm PostgreSQL, MongoDB.', '/cv/levancuong_cv.pdf', '1999-11-05', 3);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'phamthidung'),
 'Data Engineer 2 năm, sử dụng Python + PostgreSQL + Docker + AWS.', '/cv/phamthidung_cv.pdf', '2000-09-18', 2);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'hoangvanduc'),
 'Junior Developer 1 năm kinh nghiệm Java/Python.', '/cv/hoangvanduc_cv.pdf', '2002-01-10', 1);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'vuthiphuong'),
 'Sinh viên năm cuối PTIT, đang tìm vị trí thực tập Java.', '/cv/vuthiphuong_cv.pdf', '2003-05-20', 0);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'dangvangiang'),
 'Frontend Developer 2 năm, thành thạo ReactJS + VueJS.', '/cv/dangvangiang_cv.pdf', '2001-02-14', 2);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'buithihuong'),
 'Sinh viên năm cuối, đam mê Python và Data Science.', '/cv/buithihuong_cv.pdf', '2003-08-30', 0);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'lyvankhoi'),
 'Mobile Developer 1 năm kinh nghiệm Kotlin/Android.', '/cv/lyvankhoi_cv.pdf', '2002-04-12', 1);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'maithilinh'),
 'Backend Developer 2 năm, chuyên Python + FastAPI.', '/cv/maithilinh_cv.pdf', '2001-06-25', 2);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'truongvanminh'),
 'Fullstack Developer 3 năm NodeJS + ReactJS.', '/cv/truongvanminh_cv.pdf', '1999-09-08', 3);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'ngothingoc'),
 'Junior Fullstack 1 năm kinh nghiệm NodeJS.', '/cv/ngothingoc_cv.pdf', '2002-11-15', 1);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'dinhvanphong'),
 'Senior Fullstack 4 năm NodeJS + VueJS. Kinh nghiệm Docker, AWS, PostgreSQL.', '/cv/dinhvanphong_cv.pdf', '1998-03-22', 4);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'phamvanquan'),
 'Sinh viên năm cuối, biết JavaScript cơ bản.', '/cv/phamvanquan_cv.pdf', '2003-07-01', 0);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'hoangthiquynh'),
 'Data Engineer 3 năm Python + AWS. Kinh nghiệm Docker, PostgreSQL, Linux.', '/cv/hoangthiquynh_cv.pdf', '1999-12-10', 3);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'lethithanh'),
 'Junior Data Analyst 1 năm, sử dụng Python + MySQL.', '/cv/lethithanh_cv.pdf', '2002-02-28', 1);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'vuvanthang'),
 'Sinh viên năm cuối, mới học Python.', '/cv/vuvanthang_cv.pdf', '2003-10-05', 0);
INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'dangthiuyen'),
 'Backend Developer 2 năm Python + FastAPI + MongoDB + Redis.', '/cv/dangthiuyen_cv.pdf', '2001-04-18', 2);

-- 4. HR (5)
INSERT INTO HR (userId, emailSign, posId, compId) VALUES
((SELECT userId FROM "user" WHERE userName = 'hr_fpt'),
 'Ngô Thị Lan - Recruiter | FPT Demo',
 (SELECT posId FROM HRPOSITION WHERE posName = 'Recruiter'),
 (SELECT compId FROM COMPANY WHERE compName = 'FPT Demo'));
INSERT INTO HR (userId, emailSign, posId, compId) VALUES
((SELECT userId FROM "user" WHERE userName = 'hr_vng'),
 'Đỗ Văn Hùng - Senior Recruiter | VNG Demo',
 (SELECT posId FROM HRPOSITION WHERE posName = 'Senior Recruiter'),
 (SELECT compId FROM COMPANY WHERE compName = 'VNG Demo'));
INSERT INTO HR (userId, emailSign, posId, compId) VALUES
((SELECT userId FROM "user" WHERE userName = 'hr_viettel'),
 'Bùi Thị Mai - HR Manager | Viettel Demo',
 (SELECT posId FROM HRPOSITION WHERE posName = 'HR Manager'),
 (SELECT compId FROM COMPANY WHERE compName = 'Viettel Demo'));
INSERT INTO HR (userId, emailSign, posId, compId) VALUES
((SELECT userId FROM "user" WHERE userName = 'hr_tiki'),
 'Vũ Minh Tuấn - Recruiter | Tiki Demo',
 (SELECT posId FROM HRPOSITION WHERE posName = 'Recruiter'),
 (SELECT compId FROM COMPANY WHERE compName = 'Tiki Demo'));
INSERT INTO HR (userId, emailSign, posId, compId) VALUES
((SELECT userId FROM "user" WHERE userName = 'hr_momo'),
 'Lý Thu Hà - Talent Acquisition Lead | Momo Demo',
 (SELECT posId FROM HRPOSITION WHERE posName = 'Talent Acquisition Lead'),
 (SELECT compId FROM COMPANY WHERE compName = 'Momo Demo'));

-- 5. ADMIN (1 — Super Admin đã ở root_data)
INSERT INTO "admin" (userId, lastIp, roleId) VALUES
((SELECT userId FROM "user" WHERE userName = 'admin_mod'),
 '192.168.1.2',
 (SELECT roleId FROM ADMINROLE WHERE roleName = 'Moderator'));

-- 6. JOBPOSTING (8)
-- J1, J2: tại FPT Demo | J3, J4: tại VNG Demo | J5, J6: tại Viettel Demo | J7: Tiki | J8: Momo
-- J1 (Backend), J2 (Frontend), J4 (AI) = 3 job chính cho demo, mô tả chi tiết

-- J1: Backend Developer (Java/Spring Boot) — FPT Demo
INSERT INTO JOBPOSTING (title, description, minSalary, maxSalary, workLoc, workMode, expAt, compId)
VALUES ('Backend Developer (Java/Spring Boot)',
'CHI TIẾT CÔNG VIỆC
Phát triển hệ thống Backend cho các dự án sản phẩm sử dụng Java và Spring Boot.
Thiết kế và xây dựng RESTful API, microservices architecture.
Đọc và hiểu tài liệu thiết kế, đặc tả kỹ thuật.
Thực hiện unit testing, integration testing đảm bảo chất lượng code.
Code review và hỗ trợ kỹ thuật cho các thành viên trong team.
Tối ưu hiệu suất hệ thống, xử lý bottleneck và performance tuning.
Làm việc với PostgreSQL, Redis, Docker, CI/CD pipeline.
Báo cáo tiến độ cho Team Lead.

YÊU CẦU CÔNG VIỆC
Tốt nghiệp Cao đẳng trở lên ngành CNTT hoặc liên quan.
Tối thiểu 1 năm kinh nghiệm làm việc với Java và Spring Boot.
Có kiến thức về RESTful API, microservices architecture.
Kinh nghiệm làm việc với PostgreSQL hoặc MySQL.
Hiểu biết về Docker, Git, CI/CD pipeline.
Có khả năng viết unit test (JUnit, Mockito).
Ưu tiên: kinh nghiệm với Redis, RabbitMQ, Kafka.
Ưu tiên: kinh nghiệm với AWS hoặc cloud platform.

QUYỀN LỢI
Gói thu nhập năm tương đương 14-17 tháng lương (thưởng lương tháng 13, KPI, tiền mừng tuổi).
Đầy đủ BHXH, BHYT theo luật lao động.
Gói bảo hiểm sức khỏe FPT Care - khám chữa bệnh miễn phí tại tất cả bệnh viện.
Môi trường làm việc thân thiện, cởi mở. Cơ sở vật chất hiện đại.
Nhiều cơ hội phát triển và thăng tiến.
Văn hóa Doanh nghiệp đặc sắc: teambuilding, hội diễn Sao Chổi, sinh nhật FPT Demo.',
15000000, 25000000, 'Số 10 Phạm Văn Bạch, Cầu Giấy, Hà Nội', 'ONSITE', '2026-06-30 23:59:59',
(SELECT compId FROM COMPANY WHERE compName = 'FPT Demo'));

-- J2: Frontend Developer (ReactJS) — FPT Demo
INSERT INTO JOBPOSTING (title, description, minSalary, maxSalary, workLoc, workMode, expAt, compId)
VALUES ('Frontend Developer (ReactJS)',
'CHI TIẾT CÔNG VIỆC
Phối hợp cùng Product Owner và Team Lead để tìm hiểu yêu cầu nghiệp vụ và chuyển hóa thành giải pháp kỹ thuật.
Phát triển và bảo trì các ứng dụng web phức tạp sử dụng ReactJS, TypeScript và Tailwind CSS.
Xây dựng các UI components hiện đại, dễ tiếp cận.
Quản lý application state hiệu quả bằng Redux, Zustand hoặc các thư viện tương tự.
Tối ưu hóa hiệu suất frontend, đảm bảo độ phản hồi cao trên nhiều thiết bị và trình duyệt.
Dẫn dắt code review và hướng dẫn kỹ thuật cho junior.
Viết và bảo trì tài liệu kỹ thuật khi cần thiết.

YÊU CẦU CÔNG VIỆC
Ít nhất 2.5 năm kinh nghiệm xây dựng ứng dụng web production-grade.
Thành thạo HTML5, CSS3, JavaScript, TypeScript và ReactJS.
Kinh nghiệm thực tế với Tailwind CSS, Shadcn, Radix hoặc Headless UI.
Kinh nghiệm state management bằng Redux, Zustand hoặc tương tự.
Nắm vững RESTful APIs và phương pháp tích hợp.
Kiến thức tốt về Webpack, Vite hoặc tương đương.
Kinh nghiệm với Git, Docker và CI/CD pipelines.
Kỹ năng giải quyết vấn đề, giao tiếp tốt. Đọc viết tài liệu tiếng Anh.

QUYỀN LỢI
Mức lương cạnh tranh, trả theo năng lực.
BHXH, BHYT đầy đủ theo luật lao động.
Gói chăm sóc sức khỏe FPT Care.
Môi trường làm việc sáng tạo, cởi mở. Cơ hội hợp tác với chuyên gia công nghệ.
Tài trợ chi phí khóa học và chứng chỉ liên quan.',
12000000, 22000000, 'Số 10 Phạm Văn Bạch, Cầu Giấy, Hà Nội', 'HYBRID', '2026-07-15 23:59:59',
(SELECT compId FROM COMPANY WHERE compName = 'FPT Demo'));

-- J3: Fullstack Developer (NodeJS) — VNG Demo
INSERT INTO JOBPOSTING (title, description, minSalary, maxSalary, workLoc, workMode, expAt, compId)
VALUES ('Fullstack Developer (NodeJS)',
'Phát triển ứng dụng web fullstack với NodeJS + VueJS. Yêu cầu tối thiểu 2 năm kinh nghiệm NodeJS, PostgreSQL. Ưu tiên có kinh nghiệm Docker, AWS.',
20000000, 35000000, 'Tòa Keangnam, Phạm Hùng, Hà Nội', 'ONSITE', '2026-07-31 23:59:59',
(SELECT compId FROM COMPANY WHERE compName = 'VNG Demo'));

-- J4: AI Engineer (Python/NLP) — VNG Demo
INSERT INTO JOBPOSTING (title, description, minSalary, maxSalary, workLoc, workMode, expAt, compId)
VALUES ('AI Engineer (Python/NLP)',
'CHI TIẾT CÔNG VIỆC
1. Phân tích yêu cầu nghiệp vụ và dữ liệu:
- Làm việc với chuyên gia, BA, Data Scientist để hiểu cấu trúc và ngữ nghĩa dữ liệu.
- Xác định yêu cầu AI/NLP phục vụ tìm kiếm, phân loại, gợi ý, liên kết dữ liệu.
2. Xây dựng & huấn luyện mô hình AI/NLP:
- Phát triển mô hình xử lý tiếng Việt chuyên sâu: tokenization, NER, phân loại chủ đề.
- Ứng dụng Deep Learning (BERT, PhoBERT, LLM) để trích xuất thông tin và phân tích ngữ nghĩa.
- Xây dựng hệ thống gợi ý thông minh (recommendation engine).
3. Xử lý dữ liệu & pipeline:
- Làm sạch và chuẩn hóa dữ liệu từ nhiều định dạng (PDF, DOC, HTML).
- Xây dựng pipeline xử lý dữ liệu tự động.
4. Triển khai & tích hợp:
- Đóng gói mô hình AI thành API/microservice.
- Đảm bảo hiệu năng, bảo mật và tính khả dụng cao.

YÊU CẦU CÔNG VIỆC
Tốt nghiệp ĐH/ThS chuyên ngành CNTT, AI, Khoa học dữ liệu hoặc liên quan.
2+ năm phát triển ứng dụng AI/NLP.
Thành thạo Python và thư viện AI/ML (TensorFlow, PyTorch, Hugging Face, spaCy).
Kinh nghiệm xử lý tiếng Việt và NLP.
Hiểu biết về PostgreSQL, Elasticsearch, MongoDB.
Kinh nghiệm triển khai API bằng FastAPI, container hóa bằng Docker.
Tiếng Anh đọc hiểu tốt tài liệu AI/NLP.

QUYỀN LỢI
Thu nhập cạnh tranh theo năng lực. Lương tháng 13 và thưởng KPI.
Tham gia đào tạo nâng cao chuyên môn. Tài trợ chứng chỉ quốc tế.
15 ngày phép/năm. Bảo hiểm sức khỏe cho bản thân.
Khám sức khỏe định kỳ hàng năm. Môi trường trẻ trung, năng động.',
18000000, 30000000, 'Tòa Keangnam, Phạm Hùng, Hà Nội', 'HYBRID', '2026-08-15 23:59:59',
(SELECT compId FROM COMPANY WHERE compName = 'VNG Demo'));

-- J5: DevOps Engineer — Viettel Demo
INSERT INTO JOBPOSTING (title, description, minSalary, maxSalary, workLoc, workMode, expAt, compId)
VALUES ('DevOps Engineer',
'Quản lý hạ tầng cloud, CI/CD pipeline. Yêu cầu Docker, AWS, Linux. Tối thiểu 2 năm kinh nghiệm.',
20000000, 35000000, 'Số 1 Trần Hữu Dực, Cầu Giấy, Hà Nội', 'HYBRID', '2026-08-31 23:59:59',
(SELECT compId FROM COMPANY WHERE compName = 'Viettel Demo'));

-- J6: Mobile Developer (Kotlin) — Viettel Demo
INSERT INTO JOBPOSTING (title, description, minSalary, maxSalary, workLoc, workMode, expAt, compId)
VALUES ('Mobile Developer (Kotlin)',
'Phát triển ứng dụng Android với Kotlin. Tích hợp API RESTful. Yêu cầu tối thiểu 1 năm kinh nghiệm.',
15000000, 28000000, 'Số 1 Trần Hữu Dực, Cầu Giấy, Hà Nội', 'ONSITE', '2026-07-31 23:59:59',
(SELECT compId FROM COMPANY WHERE compName = 'Viettel Demo'));

-- J7: Backend Developer (Python/FastAPI) — Tiki Demo
INSERT INTO JOBPOSTING (title, description, minSalary, maxSalary, workLoc, workMode, expAt, compId)
VALUES ('Backend Developer (Python/FastAPI)',
'Xây dựng API backend với FastAPI, PostgreSQL. Tích hợp AI/ML. Yêu cầu tối thiểu 1 năm Python.',
18000000, 32000000, '18 Tây Sơn, Đống Đa, Hà Nội', 'HYBRID', '2026-08-15 23:59:59',
(SELECT compId FROM COMPANY WHERE compName = 'Tiki Demo'));

-- J8: Frontend Developer (VueJS) — Momo Demo
INSERT INTO JOBPOSTING (title, description, minSalary, maxSalary, workLoc, workMode, expAt, compId)
VALUES ('Frontend Developer (VueJS)',
'Phát triển giao diện ứng dụng fintech với VueJS. Yêu cầu tối thiểu 1 năm kinh nghiệm VueJS/JavaScript.',
16000000, 28000000, '28 Liễu Giai, Ba Đình, Hà Nội', 'ONSITE', '2026-08-31 23:59:59',
(SELECT compId FROM COMPANY WHERE compName = 'Momo Demo'));

-- 7. JOBREQUIREMENT
-- Dùng INSERT...SELECT để map skillName → skillId, jobTitle → jobPostId

-- J1 Backend: Java, Spring Boot, PostgreSQL, Git, Docker
INSERT INTO JOBREQUIREMENT (jobPostId, skillId)
SELECT jp.jobPostId, s.skillId FROM JOBPOSTING jp CROSS JOIN SKILL s
WHERE jp.title = 'Backend Developer (Java/Spring Boot)' AND s.skillName IN ('Java','Spring Boot','PostgreSQL','Git','Docker');

-- J2 Frontend: ReactJS, TypeScript, HTML/CSS, Git, Tailwind CSS, Redux
INSERT INTO JOBREQUIREMENT (jobPostId, skillId)
SELECT jp.jobPostId, s.skillId FROM JOBPOSTING jp CROSS JOIN SKILL s
WHERE jp.title = 'Frontend Developer (ReactJS)' AND s.skillName IN ('ReactJS','TypeScript','HTML/CSS','Git','Tailwind CSS','Redux');

-- J3 Fullstack: NodeJS, VueJS, JavaScript, PostgreSQL, Git
INSERT INTO JOBREQUIREMENT (jobPostId, skillId)
SELECT jp.jobPostId, s.skillId FROM JOBPOSTING jp CROSS JOIN SKILL s
WHERE jp.title = 'Fullstack Developer (NodeJS)' AND s.skillName IN ('NodeJS','VueJS','JavaScript','PostgreSQL','Git');

-- J4 AI: Python, NLP, TensorFlow, PyTorch, PostgreSQL, FastAPI, Docker, IELTS
INSERT INTO JOBREQUIREMENT (jobPostId, skillId)
SELECT jp.jobPostId, s.skillId FROM JOBPOSTING jp CROSS JOIN SKILL s
WHERE jp.title = 'AI Engineer (Python/NLP)' AND s.skillName IN ('Python','NLP','TensorFlow','PyTorch','PostgreSQL','FastAPI','Docker','IELTS');

-- J5 DevOps: Docker, AWS, Linux, Git, Python
INSERT INTO JOBREQUIREMENT (jobPostId, skillId)
SELECT jp.jobPostId, s.skillId FROM JOBPOSTING jp CROSS JOIN SKILL s
WHERE jp.title = 'DevOps Engineer' AND s.skillName IN ('Docker','AWS','Linux','Git','Python');

-- J6 Mobile: Kotlin, Java, Git
INSERT INTO JOBREQUIREMENT (jobPostId, skillId)
SELECT jp.jobPostId, s.skillId FROM JOBPOSTING jp CROSS JOIN SKILL s
WHERE jp.title = 'Mobile Developer (Kotlin)' AND s.skillName IN ('Kotlin','Java','Git');

-- J7 Backend Python: Python, FastAPI, PostgreSQL, Docker, Git
INSERT INTO JOBREQUIREMENT (jobPostId, skillId)
SELECT jp.jobPostId, s.skillId FROM JOBPOSTING jp CROSS JOIN SKILL s
WHERE jp.title = 'Backend Developer (Python/FastAPI)' AND s.skillName IN ('Python','FastAPI','PostgreSQL','Docker','Git');

-- J8 Frontend VueJS: VueJS, JavaScript, HTML/CSS, TypeScript
INSERT INTO JOBREQUIREMENT (jobPostId, skillId)
SELECT jp.jobPostId, s.skillId FROM JOBPOSTING jp CROSS JOIN SKILL s
WHERE jp.title = 'Frontend Developer (VueJS)' AND s.skillName IN ('VueJS','JavaScript','HTML/CSS','TypeScript');

-- 8. CANDIDATESKILL
-- nguyenvanan (MAIN): backend core + frontend basic + ML interest
INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'nguyenvanan' AND s.skillName IN ('Java','Spring Boot','PostgreSQL','Docker','Git','Làm việc nhóm','JavaScript','HTML/CSS','ReactJS','Python','Machine Learning','RESTful API');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'tranthibinh' AND s.skillName IN ('ReactJS','TypeScript','HTML/CSS','Git','Giao tiếp');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'levancuong' AND s.skillName IN ('NodeJS','VueJS','JavaScript','PostgreSQL','MongoDB','Git');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'phamthidung' AND s.skillName IN ('Python','PostgreSQL','Docker','AWS','Linux');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'hoangvanduc' AND s.skillName IN ('Java','Python','Git','HTML/CSS');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'vuthiphuong' AND s.skillName IN ('Java','Git','HTML/CSS');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'dangvangiang' AND s.skillName IN ('ReactJS','VueJS','JavaScript','HTML/CSS','Git');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'buithihuong' AND s.skillName IN ('Python','Git');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'lyvankhoi' AND s.skillName IN ('Kotlin','Java','Git');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'maithilinh' AND s.skillName IN ('Python','FastAPI','PostgreSQL','Docker','Linux');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'truongvanminh' AND s.skillName IN ('NodeJS','ReactJS','JavaScript','MongoDB','Git');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'ngothingoc' AND s.skillName IN ('NodeJS','JavaScript','HTML/CSS','Git');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'dinhvanphong' AND s.skillName IN ('NodeJS','VueJS','PostgreSQL','Docker','AWS','Git');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'phamvanquan' AND s.skillName IN ('JavaScript','HTML/CSS','Git');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'hoangthiquynh' AND s.skillName IN ('Python','PostgreSQL','AWS','Docker','Linux');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'lethithanh' AND s.skillName IN ('Python','MySQL','Git','Linux');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'vuvanthang' AND s.skillName IN ('Python','Git');

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'dangthiuyen' AND s.skillName IN ('Python','FastAPI','MongoDB','Redis','Docker');

-- 9. JOBAPPLICATION (39)
-- Gồm 37 đơn gốc (từ seed_data_false) + 2 đơn mới cho main candidate (J2, J4)
-- Mỗi đơn dùng INSERT...SELECT để lấy candidateId và jobPostId

-- J1: Backend at FPT Demo (10 đơn)
INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-01 08:00:00'::timestamp, 'HIRED', '/snapshots/an_backend_fpt.pdf',
'Tôi là Nguyễn Văn An, Backend Developer 3 năm kinh nghiệm Java/Spring Boot. Đã phát triển hệ thống e-commerce 50K+ users và microservices thanh toán. Tự tin đóng góp vào đội ngũ backend của FPT Demo.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='nguyenvanan' AND jp.title='Backend Developer (Java/Spring Boot)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-01 09:15:00'::timestamp, 'REJECTED', '/snapshots/binh_backend_fpt.pdf',
'Tôi chủ yếu làm ReactJS nhưng muốn thử sức với Backend Java.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='tranthibinh' AND jp.title='Backend Developer (Java/Spring Boot)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-01 10:30:00'::timestamp, 'REJECTED', '/snapshots/cuong_backend_fpt.pdf',
'Fullstack 3 năm NodeJS, có kiến thức Java cơ bản.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='levancuong' AND jp.title='Backend Developer (Java/Spring Boot)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-01 11:00:00'::timestamp, 'REJECTED', '/snapshots/dung_backend_fpt.pdf',
'Data Engineer 2 năm, có Docker/PostgreSQL.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='phamthidung' AND jp.title='Backend Developer (Java/Spring Boot)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-01 14:00:00'::timestamp, 'REJECTED', '/snapshots/duc_backend_fpt.pdf',
'Junior 1 năm kinh nghiệm Java.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='hoangvanduc' AND jp.title='Backend Developer (Java/Spring Boot)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-01 15:20:00'::timestamp, 'REJECTED', '/snapshots/phuong_backend_fpt.pdf',
'Sinh viên năm cuối PTIT, tìm cơ hội thực tập Java.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='vuthiphuong' AND jp.title='Backend Developer (Java/Spring Boot)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-02 08:30:00'::timestamp, 'REJECTED', '/snapshots/giang_backend_fpt.pdf',
'Frontend 2 năm ReactJS/VueJS.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='dangvangiang' AND jp.title='Backend Developer (Java/Spring Boot)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-02 09:00:00'::timestamp, 'REJECTED', '/snapshots/huong_backend_fpt.pdf',
'Sinh viên đam mê Python.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='buithihuong' AND jp.title='Backend Developer (Java/Spring Boot)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-02 10:00:00'::timestamp, 'REJECTED', '/snapshots/khoi_backend_fpt.pdf',
'Mobile Developer Kotlin.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='lyvankhoi' AND jp.title='Backend Developer (Java/Spring Boot)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-02 11:30:00'::timestamp, 'REVIEWING', '/snapshots/linh_backend_fpt.pdf',
'Backend Python 2 năm, có Docker/PostgreSQL, sẵn sàng học Java.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='maithilinh' AND jp.title='Backend Developer (Java/Spring Boot)';

-- J2: Frontend at FPT Demo (3 đơn: 2 gốc + 1 main candidate )
INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-10 08:00:00'::timestamp, 'INTERVIEW', '/snapshots/binh_frontend_fpt.pdf',
'ReactJS 1 năm, TypeScript, HTML/CSS.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='tranthibinh' AND jp.title='Frontend Developer (ReactJS)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-10 09:30:00'::timestamp, 'INTERVIEW', '/snapshots/an_frontend_fpt.pdf',
'Tôi là Nguyễn Văn An, hiện đang làm Backend nhưng có kinh nghiệm cá nhân với ReactJS/TypeScript. Đã xây dựng portfolio bằng ReactJS. Nền tảng backend vững giúp tôi hiểu sâu kiến trúc frontend-backend.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='nguyenvanan' AND jp.title='Frontend Developer (ReactJS)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-18 09:00:00'::timestamp, 'REVIEWING', '/snapshots/giang_frontend_fpt.pdf',
'Frontend 2 năm ReactJS/VueJS.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='dangvangiang' AND jp.title='Frontend Developer (ReactJS)';

-- J3: Fullstack at VNG Demo (8 đơn)
INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-05 08:00:00'::timestamp, 'REJECTED', '/snapshots/binh_fullstack_vng.pdf',
'Frontend React 1 năm, muốn mở rộng sang Fullstack.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='tranthibinh' AND jp.title='Fullstack Developer (NodeJS)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-05 09:30:00'::timestamp, 'REJECTED', '/snapshots/cuong_fullstack_vng.pdf',
'Fullstack 3 năm NodeJS/VueJS.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='levancuong' AND jp.title='Fullstack Developer (NodeJS)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-05 10:00:00'::timestamp, 'REJECTED', '/snapshots/duc_fullstack_vng.pdf',
'Junior 1 năm, muốn học thêm NodeJS.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='hoangvanduc' AND jp.title='Fullstack Developer (NodeJS)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-05 11:00:00'::timestamp, 'REJECTED', '/snapshots/giang_fullstack_vng.pdf',
'Frontend 2 năm VueJS.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='dangvangiang' AND jp.title='Fullstack Developer (NodeJS)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-05 13:00:00'::timestamp, 'REJECTED', '/snapshots/minh_fullstack_vng.pdf',
'Fullstack 3 năm NodeJS/ReactJS.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='truongvanminh' AND jp.title='Fullstack Developer (NodeJS)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-05 14:30:00'::timestamp, 'REVIEWING', '/snapshots/ngoc_fullstack_vng.pdf',
'Junior Fullstack 1 năm NodeJS.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='ngothingoc' AND jp.title='Fullstack Developer (NodeJS)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-06 08:00:00'::timestamp, 'HIRED', '/snapshots/phong_fullstack_vng.pdf',
'Senior Fullstack 4 năm NodeJS/VueJS.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='dinhvanphong' AND jp.title='Fullstack Developer (NodeJS)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-06 09:00:00'::timestamp, 'REJECTED', '/snapshots/quan_fullstack_vng.pdf',
'Sinh viên năm cuối, biết JavaScript cơ bản.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='phamvanquan' AND jp.title='Fullstack Developer (NodeJS)';

-- J4: AI Engineer at VNG Demo (9 đơn: 8 gốc + 1 main candidate )
INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-08 08:00:00'::timestamp, 'HIRED', '/snapshots/dung_ai_vng.pdf',
'Data Engineer 2 năm, thành thạo Python + PostgreSQL + Docker + AWS. Có kinh nghiệm xử lý dữ liệu lớn.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='phamthidung' AND jp.title='AI Engineer (Python/NLP)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-08 09:00:00'::timestamp, 'REJECTED', '/snapshots/duc_ai_vng.pdf',
'Junior 1 năm, có Python cơ bản.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='hoangvanduc' AND jp.title='AI Engineer (Python/NLP)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-08 10:30:00'::timestamp, 'REJECTED', '/snapshots/huong_ai_vng.pdf',
'Sinh viên đam mê Data Science.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='buithihuong' AND jp.title='AI Engineer (Python/NLP)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-08 11:00:00'::timestamp, 'REJECTED', '/snapshots/linh_ai_vng.pdf',
'Backend Python 2 năm FastAPI.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='maithilinh' AND jp.title='AI Engineer (Python/NLP)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-08 12:30:00'::timestamp, 'OFFERED', '/snapshots/an_ai_vng.pdf',
'Tôi là Nguyễn Văn An, Backend Developer với kiến thức ML và NLP. Đã xây dựng chatbot xử lý tiếng Việt bằng Python/TensorFlow. Rất hứng thú với vị trí AI Engineer và mong phát triển sâu hơn trong lĩnh vực này.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='nguyenvanan' AND jp.title='AI Engineer (Python/NLP)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-09 08:00:00'::timestamp, 'REJECTED', '/snapshots/quynh_ai_vng.pdf',
'Data Engineer 3 năm Python + AWS.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='hoangthiquynh' AND jp.title='AI Engineer (Python/NLP)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-09 09:30:00'::timestamp, 'REVIEWING', '/snapshots/thanh_ai_vng.pdf',
'Junior Data Analyst 1 năm Python + MySQL.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='lethithanh' AND jp.title='AI Engineer (Python/NLP)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-09 10:00:00'::timestamp, 'REJECTED', '/snapshots/thang_ai_vng.pdf',
'Sinh viên năm cuối mới học Python.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='vuvanthang' AND jp.title='AI Engineer (Python/NLP)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-09 11:00:00'::timestamp, 'REJECTED', '/snapshots/uyen_ai_vng.pdf',
'Backend Python 2 năm FastAPI + MongoDB + Redis.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='dangthiuyen' AND jp.title='AI Engineer (Python/NLP)';

-- J5: DevOps at Viettel Demo (2 đơn)
INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-25 08:00:00'::timestamp, 'SUBMITTED', '/snapshots/linh_devops_viettel.pdf',
'Backend Python 2 năm, có Docker/Linux.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='maithilinh' AND jp.title='DevOps Engineer';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-30 09:00:00'::timestamp, 'REVIEWING', '/snapshots/quynh_devops_viettel.pdf',
'Data Engineer 3 năm, thành thạo Docker/AWS/Linux.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='hoangthiquynh' AND jp.title='DevOps Engineer';

-- J6: Mobile Kotlin at Viettel Demo (2 đơn)
INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-08 10:00:00'::timestamp, 'INTERVIEW', '/snapshots/khoi_mobile_viettel.pdf',
'Mobile Developer 1 năm Kotlin/Android.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='lyvankhoi' AND jp.title='Mobile Developer (Kotlin)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-08 11:00:00'::timestamp, 'SUBMITTED', '/snapshots/phuong_mobile_viettel.pdf',
'Sinh viên năm cuối, có Java cơ bản, muốn học Kotlin.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='vuthiphuong' AND jp.title='Mobile Developer (Kotlin)';

-- J7: Backend Python at Tiki Demo (3 đơn)
INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-12 08:00:00'::timestamp, 'WITHDRAWN', '/snapshots/dung_python_tiki.pdf',
'Data Engineer 2 năm Python/PostgreSQL.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='phamthidung' AND jp.title='Backend Developer (Python/FastAPI)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-28 09:00:00'::timestamp, 'SUBMITTED', '/snapshots/linh_python_tiki.pdf',
'Backend Python 2 năm FastAPI.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='maithilinh' AND jp.title='Backend Developer (Python/FastAPI)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-28 10:00:00'::timestamp, 'REVIEWING', '/snapshots/uyen_python_tiki.pdf',
'Backend Python 2 năm FastAPI/MongoDB/Redis.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='dangthiuyen' AND jp.title='Backend Developer (Python/FastAPI)';

-- J8: Frontend VueJS at Momo Demo (2 đơn)
INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-25 08:00:00'::timestamp, 'OFFERED', '/snapshots/cuong_vue_momo.pdf',
'Fullstack 3 năm, VueJS là thế mạnh chính.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='levancuong' AND jp.title='Frontend Developer (VueJS)';

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-20 09:00:00'::timestamp, 'SUBMITTED', '/snapshots/giang_vue_momo.pdf',
'Frontend 2 năm ReactJS/VueJS.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='dangvangiang' AND jp.title='Frontend Developer (VueJS)';

-- 10. APPSTATUSHISTORY
-- Dùng DO block để khai báo biến, tránh subquery lặp lại
DO $$
DECLARE
  v_hr_fpt INT; v_hr_vng INT; v_hr_viettel INT; v_hr_tiki INT; v_hr_momo INT;
  v_app INT;
BEGIN
  SELECT userId INTO v_hr_fpt FROM "user" WHERE userName = 'hr_fpt';
  SELECT userId INTO v_hr_vng FROM "user" WHERE userName = 'hr_vng';
  SELECT userId INTO v_hr_viettel FROM "user" WHERE userName = 'hr_viettel';
  SELECT userId INTO v_hr_tiki FROM "user" WHERE userName = 'hr_tiki';
  SELECT userId INTO v_hr_momo FROM "user" WHERE userName = 'hr_momo';

  -- ===== J1: Backend at FPT Demo (HR: hr_fpt) =====

  -- ★ nguyenvanan: SUBMITTED → REVIEWING → INTERVIEW → OFFERED → HIRED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'SUBMITTED','REVIEWING','2026-04-03 09:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'REVIEWING','INTERVIEW','2026-04-05 10:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'INTERVIEW','OFFERED','2026-04-16 09:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'OFFERED','HIRED','2026-04-20 14:00:00');

  -- tranthibinh: SUBMITTED → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='tranthibinh' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'SUBMITTED','REJECTED','2026-04-03 09:30:00');

  -- levancuong: SUBMITTED → REVIEWING → INTERVIEW → REJECTED (sau vòng 2)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'SUBMITTED','REVIEWING','2026-04-03 10:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'REVIEWING','INTERVIEW','2026-04-05 10:30:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'INTERVIEW','REJECTED','2026-04-15 11:00:00');

  -- phamthidung: SUBMITTED → REVIEWING → INTERVIEW → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='phamthidung' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'SUBMITTED','REVIEWING','2026-04-03 10:30:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'REVIEWING','INTERVIEW','2026-04-05 11:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'INTERVIEW','REJECTED','2026-04-09 09:00:00');

  -- hoangvanduc: SUBMITTED → REVIEWING → INTERVIEW → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='hoangvanduc' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'SUBMITTED','REVIEWING','2026-04-03 11:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'REVIEWING','INTERVIEW','2026-04-05 11:30:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'INTERVIEW','REJECTED','2026-04-09 10:00:00');

  -- vuthiphuong: SUBMITTED → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='vuthiphuong' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'SUBMITTED','REJECTED','2026-04-03 11:30:00');

  -- dangvangiang: SUBMITTED → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dangvangiang' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'SUBMITTED','REJECTED','2026-04-03 12:00:00');

  -- buithihuong: SUBMITTED → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='buithihuong' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'SUBMITTED','REJECTED','2026-04-03 12:30:00');

  -- lyvankhoi: SUBMITTED → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='lyvankhoi' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'SUBMITTED','REJECTED','2026-04-03 13:00:00');

  -- maithilinh: SUBMITTED → REVIEWING
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='maithilinh' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'SUBMITTED','REVIEWING','2026-04-03 14:00:00');

  -- J2: Frontend at FPT Demo (HR: hr_fpt)

  -- tranthibinh: SUBMITTED → REVIEWING → INTERVIEW
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='tranthibinh' AND jp.title='Frontend Developer (ReactJS)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'SUBMITTED','REVIEWING','2026-04-12 09:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'REVIEWING','INTERVIEW','2026-04-15 09:00:00');

  -- nguyenvanan: SUBMITTED → REVIEWING → INTERVIEW
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='Frontend Developer (ReactJS)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'SUBMITTED','REVIEWING','2026-04-12 10:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'REVIEWING','INTERVIEW','2026-04-15 10:00:00');

  -- dangvangiang: SUBMITTED → REVIEWING
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dangvangiang' AND jp.title='Frontend Developer (ReactJS)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_fpt,'SUBMITTED','REVIEWING','2026-04-20 09:00:00');

  -- J3: Fullstack at VNG Demo (HR: hr_vng)

  -- tranthibinh: SUBMITTED → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='tranthibinh' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REJECTED','2026-04-08 09:00:00');

  -- levancuong: SUBMITTED → REVIEWING → INTERVIEW → REJECTED (sau vòng 2)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REVIEWING','2026-04-08 09:30:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'REVIEWING','INTERVIEW','2026-04-10 09:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'INTERVIEW','REJECTED','2026-04-23 10:00:00');

  -- hoangvanduc: SUBMITTED → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='hoangvanduc' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REJECTED','2026-04-08 10:00:00');

  -- dangvangiang: SUBMITTED → REVIEWING → INTERVIEW → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dangvangiang' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REVIEWING','2026-04-08 10:30:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'REVIEWING','INTERVIEW','2026-04-10 09:30:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'INTERVIEW','REJECTED','2026-04-16 14:00:00');

  -- truongvanminh: SUBMITTED → REVIEWING → INTERVIEW → REJECTED (sau vòng 2)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='truongvanminh' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REVIEWING','2026-04-08 11:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'REVIEWING','INTERVIEW','2026-04-10 10:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'INTERVIEW','REJECTED','2026-04-23 11:00:00');

  -- ngothingoc: SUBMITTED → REVIEWING
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='ngothingoc' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REVIEWING','2026-04-08 11:30:00');

  -- dinhvanphong: SUBMITTED → REVIEWING → INTERVIEW → OFFERED → HIRED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dinhvanphong' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REVIEWING','2026-04-08 12:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'REVIEWING','INTERVIEW','2026-04-10 10:30:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'INTERVIEW','OFFERED','2026-04-24 09:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'OFFERED','HIRED','2026-04-28 14:00:00');

  -- phamvanquan: SUBMITTED → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='phamvanquan' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REJECTED','2026-04-08 12:30:00');

  -- J4: AI Engineer at VNG Demo (HR: hr_vng)

  -- phamthidung: SUBMITTED → REVIEWING → INTERVIEW → OFFERED → HIRED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='phamthidung' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REVIEWING','2026-04-11 09:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'REVIEWING','INTERVIEW','2026-04-14 09:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'INTERVIEW','OFFERED','2026-04-29 09:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'OFFERED','HIRED','2026-05-05 14:00:00');

  -- hoangvanduc: SUBMITTED → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='hoangvanduc' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REJECTED','2026-04-11 09:30:00');

  -- buithihuong: SUBMITTED → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='buithihuong' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REJECTED','2026-04-11 10:00:00');

  -- maithilinh: SUBMITTED → REVIEWING → INTERVIEW → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='maithilinh' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REVIEWING','2026-04-11 10:30:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'REVIEWING','INTERVIEW','2026-04-14 09:30:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'INTERVIEW','REJECTED','2026-04-22 09:00:00');

  -- nguyenvanan: SUBMITTED → REVIEWING → INTERVIEW → OFFERED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REVIEWING','2026-04-11 11:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'REVIEWING','INTERVIEW','2026-04-14 11:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'INTERVIEW','OFFERED','2026-04-29 10:00:00');

  -- hoangthiquynh: SUBMITTED → REVIEWING → INTERVIEW → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='hoangthiquynh' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REVIEWING','2026-04-11 11:30:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'REVIEWING','INTERVIEW','2026-04-14 10:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'INTERVIEW','REJECTED','2026-04-28 10:00:00');

  -- lethithanh: SUBMITTED → REVIEWING
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='lethithanh' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REVIEWING','2026-04-11 12:00:00');

  -- vuvanthang: SUBMITTED → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='vuvanthang' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REJECTED','2026-04-11 12:30:00');

  -- dangthiuyen: SUBMITTED → REVIEWING → INTERVIEW → REJECTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dangthiuyen' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'SUBMITTED','REVIEWING','2026-04-11 13:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'REVIEWING','INTERVIEW','2026-04-14 10:30:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_vng,'INTERVIEW','REJECTED','2026-04-22 10:00:00');

  -- J5: DevOps at Viettel Demo (HR: hr_viettel)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='hoangthiquynh' AND jp.title='DevOps Engineer';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_viettel,'SUBMITTED','REVIEWING','2026-05-02 09:00:00');

  -- J6: Mobile at Viettel Demo (HR: hr_viettel)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='lyvankhoi' AND jp.title='Mobile Developer (Kotlin)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_viettel,'SUBMITTED','REVIEWING','2026-04-11 09:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_viettel,'REVIEWING','INTERVIEW','2026-04-14 09:00:00');

  -- J7: Backend Python at Tiki Demo (HR: hr_tiki)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='phamthidung' AND jp.title='Backend Developer (Python/FastAPI)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_tiki,'SUBMITTED','WITHDRAWN','2026-05-06 09:00:00');

  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dangthiuyen' AND jp.title='Backend Developer (Python/FastAPI)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_tiki,'SUBMITTED','REVIEWING','2026-04-30 10:00:00');

  -- J8: Frontend VueJS at Momo Demo (HR: hr_momo)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Frontend Developer (VueJS)';
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_momo,'SUBMITTED','REVIEWING','2026-04-27 09:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_momo,'REVIEWING','INTERVIEW','2026-04-29 09:00:00');
  INSERT INTO APPSTATUSHISTORY (jobAppId,hrId,oldStat,newStat,changedAt) VALUES (v_app,v_hr_momo,'INTERVIEW','OFFERED','2026-05-05 09:00:00');

END $$;

-- 11. INTERVIEW (24)
DO $$
DECLARE v_app INT;
BEGIN
  -- J1 vòng 1 (4 interviews)
  -- nguyenvanan v1
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-07 09:00:00','2026-04-07 10:00:00','ONLINE','https://meet.google.com/fpt-j1-an',NULL);
  -- nguyenvanan v2
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-14 09:00:00','2026-04-14 10:30:00','OFFLINE',NULL,'FPT Tower, Tầng 8, Phòng Director');

  -- levancuong v1
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-07 10:30:00','2026-04-07 11:30:00','ONLINE','https://meet.google.com/fpt-j1-cuong',NULL);
  -- levancuong v2
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-14 14:00:00','2026-04-14 15:30:00','ONLINE','https://meet.google.com/fpt-j1-cuong-v2',NULL);

  -- phamthidung v1
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='phamthidung' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-07 14:00:00','2026-04-07 15:00:00','OFFLINE',NULL,'FPT Tower, Tầng 5, Phòng Meeting A');

  -- hoangvanduc v1
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='hoangvanduc' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-08 09:00:00','2026-04-08 10:00:00','OFFLINE',NULL,'FPT Tower, Tầng 5, Phòng Meeting B');

  -- J2: Frontend interviews
  -- tranthibinh
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='tranthibinh' AND jp.title='Frontend Developer (ReactJS)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-18 09:00:00','2026-04-18 10:00:00','ONLINE','https://meet.google.com/fpt-j2-binh',NULL);

  -- nguyenvanan
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='Frontend Developer (ReactJS)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-18 10:30:00','2026-04-18 11:30:00','ONLINE','https://meet.google.com/fpt-j2-an',NULL);

  -- J3 vòng 1 (4 interviews)
  -- dinhvanphong v1
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dinhvanphong' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-14 09:00:00','2026-04-14 10:00:00','ONLINE','https://meet.google.com/vng-j3-phong',NULL);
  -- dinhvanphong v2
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-21 09:00:00','2026-04-21 10:30:00','OFFLINE',NULL,'Tòa Keangnam, Tầng 5, Phòng Director');

  -- truongvanminh v1
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='truongvanminh' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-14 10:30:00','2026-04-14 11:30:00','ONLINE','https://meet.google.com/vng-j3-minh',NULL);
  -- truongvanminh v2
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-21 14:00:00','2026-04-21 15:30:00','ONLINE','https://meet.google.com/vng-j3-minh-v2',NULL);

  -- levancuong (J3) v1
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-14 14:00:00','2026-04-14 15:00:00','OFFLINE',NULL,'Tòa Keangnam, Tầng 3, Phòng Interview A');
  -- levancuong (J3) v2
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-22 09:00:00','2026-04-22 10:30:00','ONLINE','https://meet.google.com/vng-j3-cuong-v2',NULL);

  -- dangvangiang (J3) v1
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dangvangiang' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-15 09:00:00','2026-04-15 10:00:00','ONLINE','https://meet.google.com/vng-j3-giang',NULL);

  -- J4: AI Engineer interviews
  -- phamthidung v1
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='phamthidung' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-18 10:30:00','2026-04-18 11:30:00','ONLINE','https://meet.google.com/vng-j4-dung',NULL);
  -- phamthidung v2
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-25 09:00:00','2026-04-25 10:30:00','OFFLINE',NULL,'Tòa Keangnam, Tầng 5, Phòng Director');

  -- maithilinh (J4)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='maithilinh' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-18 14:00:00','2026-04-18 15:00:00','OFFLINE',NULL,'Tòa Keangnam, Tầng 3, Phòng Interview B');

  -- nguyenvanan (J4)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-19 09:00:00','2026-04-19 10:00:00','ONLINE','https://meet.google.com/vng-j4-an',NULL);

  -- hoangthiquynh (J4) v1
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='hoangthiquynh' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-18 09:00:00','2026-04-18 10:00:00','ONLINE','https://meet.google.com/vng-j4-quynh',NULL);
  -- hoangthiquynh v2
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-25 14:00:00','2026-04-25 15:30:00','ONLINE','https://meet.google.com/vng-j4-quynh-v2',NULL);

  -- dangthiuyen (J4)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dangthiuyen' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-19 10:30:00','2026-04-19 11:30:00','ONLINE','https://meet.google.com/vng-j4-uyen',NULL);

  -- J6: Mobile at Viettel
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='lyvankhoi' AND jp.title='Mobile Developer (Kotlin)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-04-17 14:00:00','2026-04-17 15:00:00','OFFLINE',NULL,'Viettel Tower, Tầng 3, Phòng Meeting A');

  -- J8: Frontend VueJS at Momo
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Frontend Developer (VueJS)';
  INSERT INTO INTERVIEW (jobAppId,startAt,endAt,"mode",linkMeet,loc) VALUES (v_app,'2026-05-02 10:00:00','2026-05-02 11:00:00','ONLINE','https://meet.google.com/momo-j8-cuong',NULL);

END $$;

-- 12. INTERVIEWFEEDBACK (23)
DO $$
DECLARE
  v_hr_fpt INT; v_hr_vng INT; v_hr_viettel INT; v_hr_momo INT;
  v_app INT; v_interv INT;
BEGIN
  SELECT userId INTO v_hr_fpt FROM "user" WHERE userName = 'hr_fpt';
  SELECT userId INTO v_hr_vng FROM "user" WHERE userName = 'hr_vng';
  SELECT userId INTO v_hr_viettel FROM "user" WHERE userName = 'hr_viettel';
  SELECT userId INTO v_hr_momo FROM "user" WHERE userName = 'hr_momo';

  -- J1 vòng 1
  -- nguyenvanan v1: 9 điểm
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='Backend Developer (Java/Spring Boot)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-07 09:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_fpt,9,'Java senior xuất sắc. Kiến thức Spring Boot rất sâu, hiểu rõ microservices. Đề xuất lên vòng 2.','2026-04-07 10:30:00');

  -- levancuong v1: 7 điểm
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Backend Developer (Java/Spring Boot)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-07 10:30:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_fpt,7,'Fullstack tốt, Java cơ bản ổn nhưng chưa chuyên sâu. Cho lên vòng 2.','2026-04-07 12:00:00');

  -- phamthidung: 5 điểm
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='phamthidung' AND jp.title='Backend Developer (Java/Spring Boot)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-07 14:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_fpt,5,'Data Engineer, Java yếu. Không đủ cho Backend Java thuần.','2026-04-07 15:30:00');

  -- hoangvanduc: 4 điểm
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='hoangvanduc' AND jp.title='Backend Developer (Java/Spring Boot)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-08 09:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_fpt,4,'Junior, kiến thức Java còn mỏng. Cần thêm 1-2 năm KN.','2026-04-08 10:30:00');

  -- J1 vòng 2
  -- nguyenvanan v2: 9 điểm
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='Backend Developer (Java/Spring Boot)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-14 09:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_fpt,9,'Giải bài coding xuất sắc. System design tốt. Hiểu rõ trade-off giữa monolith và microservices. Đề xuất offer.','2026-04-14 11:00:00');

  -- levancuong v2: 7 điểm
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Backend Developer (Java/Spring Boot)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-14 14:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_fpt,7,'Coding ổn nhưng thiếu KN microservices quy mô lớn. Không đủ so với ứng viên khác.','2026-04-14 16:00:00');

  -- J2: Frontend
  -- tranthibinh: 8 điểm
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='tranthibinh' AND jp.title='Frontend Developer (ReactJS)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-18 09:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_fpt,8,'ReactJS/TypeScript tốt. Có tiềm năng phát triển. Cần đánh giá thêm.','2026-04-18 10:30:00');

  -- nguyenvanan J2: 7 điểm
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='Frontend Developer (ReactJS)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-18 10:30:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_fpt,7,'Nền tảng backend vững, ReactJS ở mức cơ bản nhưng tư duy logic tốt. Có tiềm năng nhưng cần bổ sung kinh nghiệm frontend thực tế. Đang đánh giá.','2026-04-18 12:00:00');

  -- J3 vòng 1
  -- dinhvanphong v1: 9
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dinhvanphong' AND jp.title='Fullstack Developer (NodeJS)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-14 09:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_vng,9,'Senior xuất sắc. Hiểu sâu NodeJS event loop và PostgreSQL optimization.','2026-04-14 10:30:00');

  -- truongvanminh v1: 7
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='truongvanminh' AND jp.title='Fullstack Developer (NodeJS)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-14 10:30:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_vng,7,'NodeJS tốt nhưng thiếu VueJS. ReactJS mạnh, có tiềm năng.','2026-04-14 12:00:00');

  -- levancuong (J3) v1: 7
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Fullstack Developer (NodeJS)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-14 14:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_vng,7,'Fullstack ổn, NodeJS + VueJS đều có. Thiếu KN hệ thống lớn.','2026-04-14 15:30:00');

  -- dangvangiang (J3): 4
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dangvangiang' AND jp.title='Fullstack Developer (NodeJS)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-15 09:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_vng,4,'Frontend tốt nhưng Backend yếu. Không nắm NodeJS async patterns.','2026-04-15 10:30:00');

  -- J3 vòng 2
  -- dinhvanphong v2: 9
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dinhvanphong' AND jp.title='Fullstack Developer (NodeJS)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-21 09:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_vng,9,'Live coding xuất sắc. Hiểu Docker/AWS sâu. Đề xuất offer.','2026-04-21 11:00:00');

  -- truongvanminh v2: 7
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='truongvanminh' AND jp.title='Fullstack Developer (NodeJS)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-21 14:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_vng,7,'Coding tốt nhưng thiếu PostgreSQL query optimization.','2026-04-21 16:00:00');

  -- levancuong (J3) v2: 6
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Fullstack Developer (NodeJS)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-22 09:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_vng,6,'NodeJS tốt nhưng system design chưa đủ quy mô VNG Demo.','2026-04-22 11:00:00');

  -- J4 vòng 1
  -- hoangthiquynh: 8
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='hoangthiquynh' AND jp.title='AI Engineer (Python/NLP)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-18 09:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_vng,8,'Data pipeline vững, AWS architecture tốt. Đề xuất lên vòng 2.','2026-04-18 10:30:00');

  -- phamthidung v1: 8
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='phamthidung' AND jp.title='AI Engineer (Python/NLP)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-18 10:30:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_vng,8,'Docker/PostgreSQL xuất sắc, tư duy hệ thống tốt. Đề xuất lên vòng 2.','2026-04-18 12:00:00');

  -- maithilinh (J4): 6
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='maithilinh' AND jp.title='AI Engineer (Python/NLP)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-18 14:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_vng,6,'FastAPI tốt nhưng AI/NLP chưa sâu. Thiếu kinh nghiệm ML.','2026-04-18 15:30:00');

  -- ★ nguyenvanan (J4): 8
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='AI Engineer (Python/NLP)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-19 09:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_vng,8,'Kiến thức Machine Learning tốt cho level 3 năm. Dự án chatbot NLP tiếng Việt ấn tượng. Python vững. Thiếu deep learning chuyên sâu nhưng foundation tốt, đánh giá onboard nhanh. Đề xuất offer.','2026-04-19 10:30:00');

  -- dangthiuyen (J4): 5
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dangthiuyen' AND jp.title='AI Engineer (Python/NLP)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-19 10:30:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_vng,5,'Python tốt nhưng thiếu kinh nghiệm NLP và PostgreSQL.','2026-04-19 12:00:00');

  -- J4 vòng 2
  -- phamthidung v2: 9
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='phamthidung' AND jp.title='AI Engineer (Python/NLP)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-25 09:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_vng,9,'Bài take-home xuất sắc. Teamwork tốt. Đề xuất offer.','2026-04-25 11:00:00');

  -- hoangthiquynh v2: 7
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='hoangthiquynh' AND jp.title='AI Engineer (Python/NLP)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-04-25 14:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_vng,7,'Technical tốt nhưng bài team exercise chưa nổi bật.','2026-04-25 16:00:00');

  -- J8: Frontend VueJS
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Frontend Developer (VueJS)';
  SELECT intervId INTO v_interv FROM INTERVIEW WHERE jobAppId=v_app AND startAt='2026-05-02 10:00:00';
  INSERT INTO INTERVIEWFEEDBACK (intervId,hrId,score,cmt,subAt) VALUES (v_interv,v_hr_momo,8,'VueJS rất tốt, 3 năm KN thực tế. Phù hợp culture Momo Demo. Đề xuất offer.','2026-05-02 11:30:00');

END $$;

-- 13. OFFER (6)
DO $$
DECLARE
  v_hr_fpt INT; v_hr_vng INT; v_hr_momo INT;
  v_app INT;
BEGIN
  SELECT userId INTO v_hr_fpt FROM "user" WHERE userName = 'hr_fpt';
  SELECT userId INTO v_hr_vng FROM "user" WHERE userName = 'hr_vng';
  SELECT userId INTO v_hr_momo FROM "user" WHERE userName = 'hr_momo';

  -- nguyenvanan → J1 Backend: ACCEPTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO OFFER (jobAppId,salary,description,stat,subAt,ver,hrId) VALUES (v_app,22000000,'Backend Developer Java/Spring Boot tại FPT Demo. Thử việc 2 tháng. BHXH, 13 tháng lương.','ACCEPTED','2026-04-16 10:00:00',1,v_hr_fpt);

  -- dinhvanphong → J3 Fullstack: ACCEPTED
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dinhvanphong' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO OFFER (jobAppId,salary,description,stat,subAt,ver,hrId) VALUES (v_app,32000000,'Fullstack Developer NodeJS tại VNG Demo. Thử việc 2 tháng. BHXH, 14 tháng lương, stock option.','ACCEPTED','2026-04-24 10:00:00',1,v_hr_vng);

  -- phamthidung → J4 AI: REJECTED v1, rồi ACCEPTED v2
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='phamthidung' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO OFFER (jobAppId,salary,description,stat,subAt,ver,hrId) VALUES (v_app,25000000,'AI Engineer Python/NLP tại VNG Demo. Thử việc 2 tháng. BHXH, 14 tháng lương, Remote.','REJECTED','2026-04-29 10:00:00',1,v_hr_vng);
  INSERT INTO OFFER (jobAppId,salary,description,stat,subAt,ver,hrId) VALUES (v_app,28000000,'AI Engineer Python/NLP tại VNG Demo. Thử việc 2 tháng. BHXH, 14 tháng lương, Remote, project bonus.','ACCEPTED','2026-05-02 10:00:00',2,v_hr_vng);

  -- ★ nguyenvanan → J4 AI: PENDING
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO OFFER (jobAppId,salary,description,stat,subAt,ver,hrId) VALUES (v_app,24000000,'AI Engineer Python/NLP tại VNG Demo. Thử việc 2 tháng. BHXH, 14 tháng lương.','PENDING','2026-04-29 11:00:00',1,v_hr_vng);

  -- levancuong → J8 VueJS: PENDING
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Frontend Developer (VueJS)';
  INSERT INTO OFFER (jobAppId,salary,description,stat,subAt,ver,hrId) VALUES (v_app,26000000,'Frontend Developer VueJS tại Momo Demo. Thử việc 2 tháng. BHXH, 13 tháng lương.','PENDING','2026-05-05 10:00:00',1,v_hr_momo);

END $$;

-- 14. EMAILLOG (38)
-- tmplId qua subquery: INTERVIEW_INVITE, OFFER_LETTER, REJECTION, APPLICATION_RECEIVED
DO $$
DECLARE
  v_tmpl_invite INT; v_tmpl_offer INT; v_tmpl_reject INT;
  v_hr_fpt INT; v_hr_vng INT; v_hr_viettel INT; v_hr_momo INT;
  v_app INT;
BEGIN
  SELECT et.tmplId INTO v_tmpl_invite FROM EMAILTEMPLATE et JOIN EMAILTYPE ety ON et.typeId=ety.typeId WHERE ety.typeName='INTERVIEW_INVITE';
  SELECT et.tmplId INTO v_tmpl_offer FROM EMAILTEMPLATE et JOIN EMAILTYPE ety ON et.typeId=ety.typeId WHERE ety.typeName='OFFER_LETTER';
  SELECT et.tmplId INTO v_tmpl_reject FROM EMAILTEMPLATE et JOIN EMAILTYPE ety ON et.typeId=ety.typeId WHERE ety.typeName='REJECTION';
  SELECT userId INTO v_hr_fpt FROM "user" WHERE userName='hr_fpt';
  SELECT userId INTO v_hr_vng FROM "user" WHERE userName='hr_vng';
  SELECT userId INTO v_hr_viettel FROM "user" WHERE userName='hr_viettel';
  SELECT userId INTO v_hr_momo FROM "user" WHERE userName='hr_momo';

  -- J1: Backend at FPT Demo (10 emails)

  -- Mời PV v1: nguyenvanan (chi tiết)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_fpt,
'Kính gửi Nguyễn Văn An,
Sau khi xem xét kỹ lưỡng hồ sơ của bạn, chúng tôi xin mời bạn tham gia phỏng vấn cho vị trí Backend Developer (Java/Spring Boot) tại FPT Demo.

Thời gian: 07/04/2026 09:00 (dự kiến kéo dài 1 giờ)
Hình thức: Online
Link: https://meet.google.com/fpt-j1-an

Trân trọng,
Ngô Thị Lan - Recruiter | FPT Demo','2026-04-05 15:00:00','nguyenvanan@gmail.com');

  -- Mời PV v1: levancuong
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_fpt,'Mời phỏng vấn Backend Java - FPT Demo. Thời gian: 07/04/2026 10:30. Online.','2026-04-05 15:10:00','levancuong@gmail.com');

  -- Mời PV v1: phamthidung
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='phamthidung' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_fpt,'Mời phỏng vấn Backend Java - FPT Demo. Thời gian: 07/04/2026 14:00. Offline: FPT Tower Tầng 5.','2026-04-05 15:20:00','phamthidung@gmail.com');

  -- Mời PV v1: hoangvanduc
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='hoangvanduc' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_fpt,'Mời phỏng vấn Backend Java - FPT Demo. Thời gian: 08/04/2026 09:00. Offline: FPT Tower Tầng 5.','2026-04-05 15:30:00','hoangvanduc@gmail.com');

  -- Mời PV v2: nguyenvanan (chi tiết)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_fpt,
'Kính gửi Nguyễn Văn An,
Chúc mừng bạn đã vượt qua vòng phỏng vấn 1! Chúng tôi xin mời bạn tham gia phỏng vấn vòng 2 cho vị trí Backend Developer tại FPT Demo.

Thời gian: 14/04/2026 09:00
Hình thức: Trực tiếp
Địa điểm: FPT Tower, Tầng 8, Phòng Director

Trân trọng,
Ngô Thị Lan - Recruiter | FPT Demo','2026-04-09 14:00:00','nguyenvanan@gmail.com');

  -- Mời PV v2: levancuong
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_fpt,'Mời phỏng vấn vòng 2 Backend Java - FPT Demo. Thời gian: 14/04/2026 14:00. Online.','2026-04-09 14:10:00','levancuong@gmail.com');

  -- Từ chối: phamthidung
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='phamthidung' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_reject,v_app,v_hr_fpt,'Từ chối sau phỏng vấn Backend Java - FPT Demo. Chúng tôi đã chọn ứng viên khác phù hợp hơn.','2026-04-09 16:00:00','phamthidung@gmail.com');

  -- Từ chối: hoangvanduc
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='hoangvanduc' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_reject,v_app,v_hr_fpt,'Từ chối sau phỏng vấn Backend Java - FPT Demo. Chúng tôi đã chọn ứng viên khác phù hợp hơn.','2026-04-09 16:10:00','hoangvanduc@gmail.com');

  -- Từ chối v2: levancuong
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_reject,v_app,v_hr_fpt,'Từ chối sau vòng 2 Backend Java - FPT Demo. Bạn có kiến thức Fullstack tốt nhưng Java chưa đủ chuyên sâu.','2026-04-15 16:00:00','levancuong@gmail.com');

  -- Offer: nguyenvanan (chi tiết)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='Backend Developer (Java/Spring Boot)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_offer,v_app,v_hr_fpt,
'Kính gửi Nguyễn Văn An,

Chúc mừng! Chúng tôi vui mừng thông báo bạn đã được chọn cho vị trí Backend Developer (Java/Spring Boot) tại FPT Demo.

Mức lương: 22.000.000 VNĐ/tháng
Ngày bắt đầu dự kiến: 04/05/2026
Thử việc: 2 tháng, lương thử việc 85%

Vui lòng phản hồi trong vòng 7 ngày.

Trân trọng,
Ngô Thị Lan - Recruiter | FPT Demo','2026-04-16 10:00:00','nguyenvanan@gmail.com');

  -- J2: Frontend at FPT Demo (2 emails)

  -- Mời PV: tranthibinh
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='tranthibinh' AND jp.title='Frontend Developer (ReactJS)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_fpt,'Mời phỏng vấn Frontend ReactJS - FPT Demo. Thời gian: 18/04/2026 09:00. Online.','2026-04-15 15:00:00','tranthibinh@gmail.com');

  -- Mời PV: nguyenvanan (chi tiết)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='Frontend Developer (ReactJS)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_fpt,
'Kính gửi Nguyễn Văn An,
Sau khi xem xét hồ sơ của bạn, chúng tôi xin mời bạn tham gia phỏng vấn cho vị trí Frontend Developer (ReactJS) tại FPT Demo.

Thời gian: 18/04/2026 10:30 (dự kiến kéo dài 1 giờ)
Hình thức: Online
Link: https://meet.google.com/fpt-j2-an

Trân trọng,
Ngô Thị Lan - Recruiter | FPT Demo','2026-04-15 15:10:00','nguyenvanan@gmail.com');

  -- J3: Fullstack at VNG Demo (11 emails)

  -- Mời PV v1: dinhvanphong, truongvanminh, levancuong, dangvangiang
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dinhvanphong' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_vng,'Mời phỏng vấn Fullstack NodeJS - VNG Demo. Thời gian: 14/04/2026 09:00. Online.','2026-04-10 15:00:00','dinhvanphong@gmail.com');

  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='truongvanminh' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_vng,'Mời phỏng vấn Fullstack NodeJS - VNG Demo. Thời gian: 14/04/2026 10:30. Online.','2026-04-10 15:10:00','truongvanminh@gmail.com');

  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_vng,'Mời phỏng vấn Fullstack NodeJS - VNG Demo. Thời gian: 14/04/2026 14:00. Offline: Tòa Keangnam Tầng 3.','2026-04-10 15:20:00','levancuong@gmail.com');

  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dangvangiang' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_vng,'Mời phỏng vấn Fullstack NodeJS - VNG Demo. Thời gian: 15/04/2026 09:00. Online.','2026-04-10 15:30:00','dangvangiang@gmail.com');

  -- Từ chối v1: dangvangiang
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_reject,v_app,v_hr_vng,'Từ chối sau PV Fullstack NodeJS - VNG Demo. Backend chưa đáp ứng yêu cầu.','2026-04-16 15:00:00','dangvangiang@gmail.com');

  -- Mời PV v2: dinhvanphong, truongvanminh, levancuong
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dinhvanphong' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_vng,'Mời phỏng vấn vòng 2 Fullstack NodeJS - VNG Demo. Thời gian: 21/04/2026 09:00. Offline: Tòa Keangnam Tầng 5.','2026-04-16 16:00:00','dinhvanphong@gmail.com');

  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='truongvanminh' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_vng,'Mời phỏng vấn vòng 2 Fullstack NodeJS - VNG Demo. Thời gian: 21/04/2026 14:00. Online.','2026-04-16 16:10:00','truongvanminh@gmail.com');

  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_vng,'Mời phỏng vấn vòng 2 Fullstack NodeJS - VNG Demo. Thời gian: 22/04/2026 09:00. Online.','2026-04-16 16:20:00','levancuong@gmail.com');

  -- Từ chối v2: truongvanminh, levancuong
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='truongvanminh' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_reject,v_app,v_hr_vng,'Từ chối sau vòng 2 Fullstack NodeJS - VNG Demo. Thiếu KN PostgreSQL.','2026-04-23 15:00:00','truongvanminh@gmail.com');

  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_reject,v_app,v_hr_vng,'Từ chối sau vòng 2 Fullstack NodeJS - VNG Demo. System design chưa đủ quy mô.','2026-04-23 15:10:00','levancuong@gmail.com');

  -- Offer: dinhvanphong
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dinhvanphong' AND jp.title='Fullstack Developer (NodeJS)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_offer,v_app,v_hr_vng,'Offer Fullstack Developer NodeJS - VNG Demo. Lương: 32.000.000 VNĐ/tháng.','2026-04-24 10:00:00','dinhvanphong@gmail.com');

  -- J4: AI Engineer at VNG Demo (12 emails)

  -- Mời PV v1: hoangthiquynh, phamthidung, maithilinh, dangthiuyen, nguyenvanan
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='hoangthiquynh' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_vng,'Mời phỏng vấn AI Engineer - VNG Demo. Thời gian: 18/04/2026 09:00. Online.','2026-04-14 15:00:00','hoangthiquynh@gmail.com');

  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='phamthidung' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_vng,'Mời phỏng vấn AI Engineer - VNG Demo. Thời gian: 18/04/2026 10:30. Online.','2026-04-14 15:10:00','phamthidung@gmail.com');

  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='maithilinh' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_vng,'Mời phỏng vấn AI Engineer - VNG Demo. Thời gian: 18/04/2026 14:00. Offline: Tòa Keangnam Tầng 3.','2026-04-14 15:20:00','maithilinh@gmail.com');

  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dangthiuyen' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_vng,'Mời phỏng vấn AI Engineer - VNG Demo. Thời gian: 19/04/2026 10:30. Online.','2026-04-14 15:30:00','dangthiuyen@gmail.com');

  -- Mời PV: nguyenvanan (chi tiết)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_vng,
'Kính gửi Nguyễn Văn An,
Sau khi xem xét hồ sơ của bạn, chúng tôi xin mời bạn tham gia phỏng vấn cho vị trí AI Engineer (Python/NLP) tại VNG Demo.

Thời gian: 19/04/2026 09:00 (dự kiến kéo dài 1 giờ)
Hình thức: Online
Link: https://meet.google.com/vng-j4-an

Trân trọng,
Đỗ Văn Hùng - Senior Recruiter | VNG Demo','2026-04-14 15:40:00','nguyenvanan@gmail.com');

  -- Từ chối v1: maithilinh, dangthiuyen
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='maithilinh' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_reject,v_app,v_hr_vng,'Từ chối sau PV AI Engineer - VNG Demo. FastAPI tốt nhưng AI/NLP chưa sâu.','2026-04-22 15:00:00','maithilinh@gmail.com');

  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='dangthiuyen' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_reject,v_app,v_hr_vng,'Từ chối sau PV AI Engineer - VNG Demo. Thiếu kinh nghiệm NLP và PostgreSQL.','2026-04-22 15:10:00','dangthiuyen@gmail.com');

  -- Mời PV v2: phamthidung, hoangthiquynh
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='phamthidung' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_vng,'Mời phỏng vấn vòng 2 AI Engineer - VNG Demo. Thời gian: 25/04/2026 09:00. Offline: Tòa Keangnam Tầng 5.','2026-04-22 16:00:00','phamthidung@gmail.com');

  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='hoangthiquynh' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_vng,'Mời phỏng vấn vòng 2 AI Engineer - VNG Demo. Thời gian: 25/04/2026 14:00. Online.','2026-04-22 16:10:00','hoangthiquynh@gmail.com');

  -- Từ chối v2: hoangthiquynh
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='hoangthiquynh' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_reject,v_app,v_hr_vng,'Từ chối sau vòng 2 AI Engineer - VNG Demo. Technical tốt nhưng culture fit kém hơn.','2026-04-28 15:00:00','hoangthiquynh@gmail.com');

  -- Offer: phamthidung
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='phamthidung' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_offer,v_app,v_hr_vng,'Offer AI Engineer Python/NLP - VNG Demo. Lương: 28.000.000 VNĐ/tháng (sau đàm phán).','2026-05-02 10:00:00','phamthidung@gmail.com');

  -- Offer: nguyenvanan (chi tiết)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='nguyenvanan' AND jp.title='AI Engineer (Python/NLP)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_offer,v_app,v_hr_vng,
'Kính gửi Nguyễn Văn An,

Chúc mừng! Chúng tôi vui mừng thông báo bạn đã được chọn cho vị trí AI Engineer (Python/NLP) tại VNG Demo.

Mức lương: 24.000.000 VNĐ/tháng
Ngày bắt đầu dự kiến: 15/05/2026
Thử việc: 2 tháng, lương thử việc 85%

Vui lòng phản hồi trong vòng 7 ngày.

Trân trọng,
Đỗ Văn Hùng - Senior Recruiter | VNG Demo','2026-04-29 11:00:00','nguyenvanan@gmail.com');

  -- J6: Mobile at Viettel (1 email)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='lyvankhoi' AND jp.title='Mobile Developer (Kotlin)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_viettel,'Mời phỏng vấn Mobile Kotlin - Viettel Demo. Thời gian: 17/04/2026 14:00. Offline: Viettel Tower Tầng 3.','2026-04-14 15:00:00','lyvankhoi@gmail.com');

  -- J8: Frontend VueJS at Momo (2 emails)
  SELECT ja.jobAppId INTO v_app FROM JOBAPPLICATION ja JOIN "user" u ON ja.candidateId=u.userId JOIN JOBPOSTING jp ON ja.jobPostId=jp.jobPostId WHERE u.userName='levancuong' AND jp.title='Frontend Developer (VueJS)';
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_invite,v_app,v_hr_momo,'Mời phỏng vấn Frontend VueJS - Momo Demo. Thời gian: 02/05/2026 10:00. Online.','2026-04-29 15:00:00','levancuong@gmail.com');
  INSERT INTO EMAILLOG (tmplId,jobAppId,hrId,"content",sentAt,rcvEmail) VALUES (v_tmpl_offer,v_app,v_hr_momo,'Offer Frontend Developer VueJS - Momo Demo. Lương: 26.000.000 VNĐ/tháng.','2026-05-05 10:00:00','levancuong@gmail.com');

END $$;

-- ==========================================
-- 13. THÍ SINH ĐẶC BIỆT: NGUYỄN HẢI HƯNG
-- Data mock riêng cho bài test AI Engineer
-- ==========================================
INSERT INTO "user" (userName, pwd, fName, lName, email, phone, prov, ward, street, stat, "role") VALUES
('nguyenhaihung',  '123456', 'Hưng',    'Nguyễn Hải',  'nguyenhaihung@gmail.com',  '0909000001', 'Hà Nội', 'Phường Đại Kim',          'KĐT Đại Kim',            'ACTIVE', 'CANDIDATE') ON CONFLICT DO NOTHING;

INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears) VALUES
((SELECT userId FROM "user" WHERE userName = 'nguyenhaihung'),
 'Đam mê AI và xử lý dữ liệu lớn. Từng đạt nhiều giải thưởng nghiên cứu khoa học tại PTIT.', '/cv/nguyenhaihung_cv.pdf', '2001-12-12', 1) ON CONFLICT DO NOTHING;

INSERT INTO CANDIDATESKILL (userId, skillId)
SELECT u.userId, s.skillId FROM "user" u CROSS JOIN SKILL s
WHERE u.userName = 'nguyenhaihung' AND s.skillName IN ('Python','NLP','Machine Learning','Git','Làm việc nhóm') ON CONFLICT DO NOTHING;

INSERT INTO JOBAPPLICATION (candidateId, jobPostId, appliedAt, stat, cvSnapUrl, coverLetter)
SELECT u.userId, jp.jobPostId, '2026-04-12 08:00:00'::timestamp, 'SUBMITTED', '/snapshots/nguyenhaihung_ai.pdf',
'Tôi là Nguyễn Hải Hưng. Tôi rất mong muốn gia nhập vị trí AI Engineer tại quý công ty. Có kiến thức vững chắc về NLP và Python.'
FROM "user" u, JOBPOSTING jp WHERE u.userName='nguyenhaihung' AND jp.title='AI Engineer (Python/NLP)' ON CONFLICT DO NOTHING;
