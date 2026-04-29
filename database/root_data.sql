-- root_data.sql — Dữ liệu gốc hệ thống miCareer
-- Thứ tự : schema-> root_data -> seed_data
SET client_encoding TO 'UTF8';

-- ============================================================
-- 0. [NMAIex] REGION + PROVINCE (34 tỉnh sau sáp nhập 2025)
-- ============================================================

INSERT INTO REGION (regId, regName) VALUES
('NORTH',   'Miền Bắc'),
('CENTRAL', 'Miền Trung'),
('SOUTH',   'Miền Nam');

INSERT INTO PROVINCE (provId, provName, regId, mergedFrom) VALUES
('HANOI',     'Thành phố Hà Nội',        'NORTH',   'Giữ nguyên'),
('HUE',       'Thành phố Huế',           'CENTRAL', 'Thừa Thiên - Huế'),
('LAICHAU',   'Tỉnh Lai Châu',           'NORTH',   'Giữ nguyên'),
('DIENBIEN',  'Tỉnh Điện Biên',          'NORTH',   'Giữ nguyên'),
('SONLA',     'Tỉnh Sơn La',             'NORTH',   'Giữ nguyên'),
('LANGSON',   'Tỉnh Lạng Sơn',           'NORTH',   'Giữ nguyên'),
('QUANGNINH', 'Tỉnh Quảng Ninh',         'NORTH',   'Giữ nguyên'),
('THANHHOA',  'Tỉnh Thanh Hóa',          'CENTRAL', 'Giữ nguyên'),
('NGHEAN',    'Tỉnh Nghệ An',            'CENTRAL', 'Giữ nguyên'),
('HATINH',    'Tỉnh Hà Tĩnh',            'CENTRAL', 'Giữ nguyên'),
('CAOBANG',   'Tỉnh Cao Bằng',           'NORTH',   'Giữ nguyên'),
('TUYENQUANG','Tỉnh Tuyên Quang',        'NORTH',   'Tuyên Quang + Hà Giang'),
('LAOCAI',    'Tỉnh Lào Cai',            'NORTH',   'Lào Cai + Yên Bái'),
('THAINGUYEN','Tỉnh Thái Nguyên',        'NORTH',   'Thái Nguyên + Bắc Kạn'),
('PHUTHO',    'Tỉnh Phú Thọ',            'NORTH',   'Phú Thọ + Hòa Bình + Vĩnh Phúc'),
('BACNINH',   'Tỉnh Bắc Ninh',           'NORTH',   'Bắc Ninh + Bắc Giang'),
('HUNGYEN',   'Tỉnh Hưng Yên',           'NORTH',   'Hưng Yên + Thái Bình'),
('HAIPHONG',  'Thành phố Hải Phòng',     'NORTH',   'Hải Phòng + Hải Dương'),
('NINHBINH',  'Tỉnh Ninh Bình',          'CENTRAL', 'Ninh Bình + Hà Nam + Nam Định'),
('QUANGTRI',  'Tỉnh Quảng Trị',          'CENTRAL', 'Quảng Trị + Quảng Bình'),
('DANANG',    'Thành phố Đà Nẵng',       'CENTRAL', 'Đà Nẵng + Quảng Nam'),
('QUANGNGAI', 'Tỉnh Quảng Ngãi',         'CENTRAL', 'Quảng Ngãi + Kon Tum'),
('GIALAI',    'Tỉnh Gia Lai',            'CENTRAL', 'Gia Lai + Bình Định'),
('KHANHHOA',  'Tỉnh Khánh Hòa',          'CENTRAL', 'Khánh Hòa + Ninh Thuận'),
('LAMDONG',   'Tỉnh Lâm Đồng',           'CENTRAL', 'Lâm Đồng + Bình Thuận + Đắk Nông'),
('DAKLAK',    'Tỉnh Đắk Lắk',            'CENTRAL', 'Đắk Lắk + Phú Yên'),
('TPHCM',     'TP. Hồ Chí Minh',         'SOUTH',   'TP.HCM + Bình Dương + Bà Rịa-Vũng Tàu'),
('DONGNAI',   'Tỉnh Đồng Nai',           'SOUTH',   'Đồng Nai + Bình Phước'),
('TAYNINH',   'Tỉnh Tây Ninh',           'SOUTH',   'Tây Ninh + Long An'),
('CANTHO',    'Thành phố Cần Thơ',       'SOUTH',   'Cần Thơ + Hậu Giang + Sóc Trăng'),
('VINHLONG',  'Tỉnh Vĩnh Long',          'SOUTH',   'Vĩnh Long + Bến Tre + Trà Vinh'),
('DONGTHAP',  'Tỉnh Đồng Tháp',          'SOUTH',   'Đồng Tháp + Tiền Giang'),
('CAMAU',     'Tỉnh Cà Mau',             'SOUTH',   'Cà Mau + Bạc Liêu'),
('ANGIANG',   'Tỉnh An Giang',           'SOUTH',   'An Giang + Kiên Giang');

-- ============================================================
-- 0b. [NMAIex] JOBLEVEL (8 cấp — dùng minYears cho Seniority Penalty)
-- ============================================================

INSERT INTO JOBLEVEL (levelName, minYears, maxYears, description) VALUES
('Intern',    0, 0,    'Thực tập sinh, chưa có kinh nghiệm đi làm'),
('Fresher',   0, 1,    'Mới ra trường, dưới 1 năm kinh nghiệm'),
('Junior',    1, 3,    '1-3 năm kinh nghiệm, cần được hướng dẫn'),
('Middle',    3, 5,    '3-5 năm kinh nghiệm, làm việc độc lập'),
('Senior',    5, 8,    '5-8 năm kinh nghiệm, dẫn dắt kỹ thuật'),
('Lead',      7, 12,   '7+ năm, quản lý nhóm kỹ thuật'),
('Manager',   8, NULL, '8+ năm, quản lý bộ phận/dự án lớn'),
('Director',  12, NULL,'12+ năm, hoạch định chiến lược kỹ thuật');

-- ============================================================
-- 0c. [NMAIex] JOBCATEGORY (17 danh mục IT)
-- ============================================================

INSERT INTO JOBCATEGORY (catName, description) VALUES
('Backend Development',   'Phát triển server-side, API, microservices'),
('Frontend Development',  'Phát triển giao diện người dùng'),
('Fullstack Development', 'Phát triển cả frontend và backend'),
('Mobile Development',    'Phát triển ứng dụng iOS/Android'),
('AI / Machine Learning', 'Trí tuệ nhân tạo và học máy'),
('Data Engineering',      'Xây dựng pipeline và hạ tầng dữ liệu'),
('Data Science',          'Phân tích dữ liệu, mô hình thống kê'),
('DevOps / Cloud',        'Quản lý hạ tầng, CI/CD, container'),
('QA / Testing',          'Kiểm thử phần mềm, đảm bảo chất lượng'),
('Security / Pentest',    'Bảo mật thông tin, kiểm thử xâm nhập'),
('Game Development',      'Phát triển trò chơi điện tử'),
('Embedded / IoT',        'Lập trình nhúng và IoT'),
('Blockchain / Web3',     'Công nghệ chuỗi khối và phi tập trung'),
('UI/UX Design',          'Thiết kế giao diện và trải nghiệm người dùng'),
('Project Management',    'Quản lý dự án phần mềm (Agile/Scrum)'),
('IT Support / SysAdmin', 'Hỗ trợ kỹ thuật và quản trị hệ thống'),
('ERP / SAP',             'Triển khai và vận hành hệ thống ERP/SAP');

-- ============================================================
-- 1. SKILL
-- ============================================================

INSERT INTO SKILL (skillName, description) VALUES
('Java', 'Ngôn ngữ lập trình hướng đối tượng'),
('Python', 'Ngôn ngữ lập trình đa năng, phổ biến trong AI/ML'),
('JavaScript', 'Ngôn ngữ lập trình phía client và server'),
('TypeScript', 'Superset của JavaScript có kiểu dữ liệu tĩnh'),
('C++', 'Ngôn ngữ lập trình hiệu năng cao'),
('C#', 'Ngôn ngữ lập trình của hệ sinh thái .NET'),
('PHP', 'Ngôn ngữ lập trình web phía server'),
('Swift', 'Ngôn ngữ lập trình cho hệ sinh thái Apple'),
('Kotlin', 'Ngôn ngữ lập trình Android hiện đại'),
('ReactJS', 'Thư viện JavaScript xây dựng giao diện'),
('VueJS', 'Framework JavaScript nhẹ cho frontend'),
('Angular', 'Framework frontend của Google'),
('HTML/CSS', 'Ngôn ngữ đánh dấu và tạo kiểu web'),
('Spring Boot', 'Framework Java phát triển ứng dụng web'),
('FastAPI', 'Framework Python xây dựng API hiệu năng cao'),
('NodeJS', 'Runtime JavaScript phía server'),
('Django', 'Framework Python full-stack'),
('MySQL', 'Hệ quản trị cơ sở dữ liệu quan hệ'),
('PostgreSQL', 'Hệ quản trị CSDL quan hệ mã nguồn mở'),
('MongoDB', 'Cơ sở dữ liệu NoSQL hướng tài liệu'),
('Redis', 'Hệ thống lưu trữ dữ liệu in-memory'),
('Docker', 'Nền tảng container hóa ứng dụng'),
('Git', 'Hệ thống quản lý phiên bản mã nguồn'),
('Linux', 'Hệ điều hành mã nguồn mở'),
('AWS', 'Dịch vụ điện toán đám mây Amazon'),
('TOEIC', 'Chứng chỉ tiếng Anh giao tiếp quốc tế'),
('IELTS', 'Chứng chỉ tiếng Anh học thuật quốc tế'),
('Làm việc nhóm', 'Kỹ năng phối hợp và cộng tác'),
('Giao tiếp', 'Kỹ năng truyền đạt và lắng nghe'),
('Quản lý thời gian', 'Kỹ năng sắp xếp và ưu tiên công việc');

INSERT INTO SKILL (skillName, description) VALUES
('ExpressJS', 'Framework web tối giản cho Node.js'),
('NestJS', 'Framework Node.js xây dựng ứng dụng server-side có cấu trúc'),
('Nginx', 'Web server và reverse proxy hiệu năng cao'),
('PM2', 'Process manager cho ứng dụng Node.js'),
('RESTful API', 'Kiến trúc thiết kế API theo nguyên tắc REST'),
('GraphQL', 'Ngôn ngữ truy vấn API do Facebook phát triển'),
('WebSocket', 'Giao thức truyền dữ liệu hai chiều thời gian thực'),
('Flutter', 'Framework phát triển ứng dụng đa nền tảng của Google'),
('Svelte', 'Framework frontend biên dịch tại thời điểm build'),
('Tailwind CSS', 'Utility-first CSS framework'),
('Redux', 'Thư viện quản lý state cho ứng dụng JavaScript'),
('Webpack', 'Module bundler cho ứng dụng JavaScript'),
('Vite', 'Build tool frontend thế hệ mới, tốc độ cao'),
('Machine Learning', 'Học máy - xây dựng mô hình từ dữ liệu'),
('Deep Learning', 'Học sâu - mạng nơ-ron nhiều tầng'),
('NLP', 'Xử lý ngôn ngữ tự nhiên'),
('TensorFlow', 'Framework mã nguồn mở cho Machine Learning của Google'),
('PyTorch', 'Framework Deep Learning của Meta'),
('SQL', 'Ngôn ngữ truy vấn cơ sở dữ liệu quan hệ'),
('Azure ML', 'Dịch vụ Machine Learning trên nền tảng đám mây Microsoft'),
('GitHub', 'Nền tảng lưu trữ và quản lý mã nguồn dựa trên Git');

--2. HRPOSITION
INSERT INTO HRPOSITION (posName, description) VALUES
('Recruiter', 'Chuyên viên tuyển dụng, phụ trách sàng lọc và liên hệ ứng viên'),
('Senior Recruiter', 'Chuyên viên tuyển dụng cao cấp, phụ trách vị trí khó'),
('HR Manager', 'Trưởng phòng nhân sự, quản lý đội ngũ HR'),
('HR Director', 'Giám đốc nhân sự, hoạch định chiến lược nhân sự'),
('Talent Acquisition Lead', 'Trưởng nhóm thu hút nhân tài'),
('HR Intern', 'Thực tập sinh nhân sự');

--3. ADMINROLE (3)
INSERT INTO ADMINROLE (roleName, description) VALUES
('Super Admin', 'Toàn quyền quản trị hệ thống'),
('Moderator', 'Kiểm duyệt nội dung, quản lý tin tuyển dụng'),
('Support', 'Hỗ trợ người dùng, xử lý khiếu nại');

-- ==================== 4. PERMISSION (15) ====================
INSERT INTO "permission" (permCode, description) VALUES
('MANAGE_USER', 'Quản lý tài khoản người dùng (CRUD)'),
('BAN_USER', 'Khóa/mở khóa tài khoản người dùng'),
('VIEW_USER', 'Xem danh sách và thông tin người dùng'),
('MANAGE_COMPANY', 'Quản lý thông tin công ty'),
('APPROVE_COMPANY', 'Duyệt công ty đăng ký mới'),
('MANAGE_JOB', 'Quản lý tin tuyển dụng (CRUD)'),
('APPROVE_JOB', 'Duyệt tin tuyển dụng trước khi đăng'),
('DELETE_JOB', 'Xóa tin tuyển dụng vi phạm'),
('MANAGE_SKILL', 'Quản lý danh mục kỹ năng'),
('VIEW_REPORT', 'Xem báo cáo và thống kê hệ thống'),
('MANAGE_EMAIL_TEMPLATE', 'Quản lý mẫu email'),
('MANAGE_ROLE', 'Quản lý vai trò và phân quyền'),
('VIEW_AI_LOG', 'Xem log truy vấn AI'),
('MANAGE_SYSTEM', 'Cấu hình hệ thống'),
('VIEW_AUDIT_LOG', 'Xem nhật ký hoạt động');

-- 5. ADMIN USER
INSERT INTO "user" (userName, pwd, fName, lName, email, phone, provId, ward, street, stat, "role")
VALUES ('admin', '123456', 'Admin', 'System', 'admin@micareer.vn', '0912345678', 'HANOI', 'Văn Quán', '119 Yên Lãng', 'ACTIVE', 'ADMIN');

-- Gán admin vào bảng ADMIN với role Super Admin (subquery)
INSERT INTO "admin" (userId, lastIp, roleId)
VALUES (
  (SELECT userId FROM "user" WHERE userName = 'admin'),
  '127.0.0.1',
  (SELECT roleId FROM ADMINROLE WHERE roleName = 'Super Admin')
);

-- 6. HASPERM (subquery)
-- Super Admin: tất cả quyền
INSERT INTO HASPERM (roleId, permId)
SELECT (SELECT roleId FROM ADMINROLE WHERE roleName = 'Super Admin'), permId
FROM "permission";

-- Moderator: VIEW_USER, APPROVE_COMPANY, MANAGE_JOB, APPROVE_JOB, DELETE_JOB, VIEW_REPORT
INSERT INTO HASPERM (roleId, permId)
SELECT (SELECT roleId FROM ADMINROLE WHERE roleName = 'Moderator'), permId
FROM "permission"
WHERE permCode IN ('VIEW_USER', 'APPROVE_COMPANY', 'MANAGE_JOB', 'APPROVE_JOB', 'DELETE_JOB', 'VIEW_REPORT');

-- Support: BAN_USER, VIEW_USER, VIEW_REPORT, VIEW_AUDIT_LOG
INSERT INTO HASPERM (roleId, permId)
SELECT (SELECT roleId FROM ADMINROLE WHERE roleName = 'Support'), permId
FROM "permission"
WHERE permCode IN ('BAN_USER', 'VIEW_USER', 'VIEW_REPORT', 'VIEW_AUDIT_LOG');

-- 7. EMAILTYPE (6)
INSERT INTO EMAILTYPE (typeName, description) VALUES
('INTERVIEW_INVITE', 'Thư mời phỏng vấn'),
('OFFER_LETTER', 'Thư đề nghị công việc'),
('REJECTION', 'Thư từ chối ứng viên'),
('APPLICATION_RECEIVED', 'Xác nhận đã nhận đơn ứng tuyển'),
('WELCOME', 'Chào mừng ứng viên đăng ký tài khoản'),
('STATUS_UPDATE', 'Thông báo cập nhật trạng thái đơn ứng tuyển');

-- 8. EMAILTEMPLATE
INSERT INTO EMAILTEMPLATE (typeId, subj, body, description) VALUES
(
  (SELECT typeId FROM EMAILTYPE WHERE typeName = 'INTERVIEW_INVITE'),
  'Thư mời phỏng vấn - {{companyName}} - Vị trí {{jobTitle}}',
  'Kính gửi {{candidateName}},
Sau khi xem xét kỹ lưỡng hồ sơ của bạn, chúng tôi xin mời bạn tham gia phỏng vấn cho vị trí {{jobTitle}} tại {{companyName}}.

Thời gian: {{interviewTime}}
Hình thức: {{interviewMode}}
Địa điểm: {{interviewLocation}}
Để buổi phỏng vấn thuận lợi vui lòng chuẩn bị kỹ và có mặt đúng giờ.

Trân trọng,
{{hrName}}',
  'Mẫu mời phỏng vấn mặc định'
),
(
  (SELECT typeId FROM EMAILTYPE WHERE typeName = 'OFFER_LETTER'),
  'Thư đề nghị công việc - {{companyName}}',
  'Kính gửi {{candidateName}},

Chúc mừng! Chúng tôi vui mừng thông báo bạn đã được chọn cho vị trí {{jobTitle}} tại {{companyName}}.

Mức lương: {{salary}}
Ngày bắt đầu dự kiến: {{startDate}}

Vui lòng phản hồi trong vòng 7 ngày.

Trân trọng,
{{hrName}}',
  'Mẫu offer mặc định'
),
(
  (SELECT typeId FROM EMAILTYPE WHERE typeName = 'REJECTION'),
  'Thông báo kết quả ứng tuyển - {{companyName}}',
  'Kính gửi {{candidateName}},

Cảm ơn bạn đã quan tâm đến vị trí {{jobTitle}} tại {{companyName}}.

Sau khi xem xét kỹ lưỡng, chúng tôi rất tiếc phải thông báo rằng chúng tôi đã chọn ứng viên khác phù hợp hơn.

Chúng tôi mong được hợp tác cùng bạn trong những cơ hội tiếp theo.
Chúc bạn thành công.

Trân trọng,
{{hrName}}',
  'Mẫu từ chối mặc định'
),
(
  (SELECT typeId FROM EMAILTYPE WHERE typeName = 'APPLICATION_RECEIVED'),
  'Xác nhận đơn ứng tuyển - {{companyName}}',
  'Kính gửi {{candidateName}},

Chúng tôi đã nhận được đơn ứng tuyển của bạn cho vị trí {{jobTitle}}.
Đơn của bạn đang trong quá trình xem xét. Chúng tôi sẽ thông báo kết quả trong thời gian sớm nhất.

Trân trọng,
Đội ngũ tuyển dụng {{companyName}}',
  'Mẫu xác nhận nhận đơn'
),
(
  (SELECT typeId FROM EMAILTYPE WHERE typeName = 'WELCOME'),
  'Chào mừng bạn đến với miCareer!',
  'Kính gửi {{candidateName}},

Chào mừng bạn đã đăng ký tài khoản tại miCareer!

Hãy hoàn thiện hồ sơ và upload CV để bắt đầu tìm kiếm cơ hội việc làm phù hợp nhé.

Chúc bạn Mã đáo thành công!
Đội ngũ miCareer',
  'Mẫu chào mừng đăng ký'
),
(
  (SELECT typeId FROM EMAILTYPE WHERE typeName = 'STATUS_UPDATE'),
  'Cập nhật trạng thái đơn ứng tuyển - {{companyName}}',
  'Kính gửi {{candidateName}},

Đơn ứng tuyển của bạn cho vị trí {{jobTitle}} tại {{companyName}} đã được cập nhật. Vui lòng kiểm tra trên website.

Trạng thái mới: {{newStatus}}

Trân trọng,
{{hrName}}',
  'Mẫu thông báo đổi trạng thái'
);
