-- seed_synth.sql — Infrastructure seed cho Synthetic Data Pipeline
-- Thay thế seed_data.sql (18 candidates cũ, 5 companies cũ)
-- Chỉ chứa: Companies (15) + HR Users (15) + Admin phụ (1)
-- Candidate/JobPosting/JobApplication -> Pipeline tự sinh
-- Thứ tự: schema_web_core.sql -> schema_ai_core.sql -> root_data.sql -> seed_synth.sql
SET client_encoding TO 'UTF8';

-- ============================================================
-- 1. COMPANIES (15) — Đa dạng: startup/enterprise/outsourcing
--    Phân bố: 5 Hà Nội, 5 TP.HCM, 3 Đà Nẵng, 2 tỉnh khác
-- ============================================================

INSERT INTO COMPANY (compName, taxCode, webUrl, logoUrl, contactEmail, provId, ward, street) VALUES
-- [HÀ NỘI - 5 công ty]
('Helios Software',      '0101248141', 'https://helios.vn',         NULL, 'hr@helios.vn',         'HANOI',    'Dịch Vọng Hậu',   '10 Phạm Văn Bạch'),
('NovaTech Corporation', '0101356789', 'https://novatech.com.vn',   NULL, 'hr@novatech.com.vn',   'HANOI',    'Yên Hòa',         '1 Trần Hữu Dực'),
('DataStream Systems',   '0101445523', 'https://datastream.vn',     NULL, 'hr@datastream.vn',     'HANOI',    'Mỹ Đình',         '72 Phạm Hùng'),
('CyberShield Security', '0101567834', 'https://cybershield.com.vn',NULL, 'hr@cybershield.com.vn','HANOI',    'Trung Hòa',       '25 Lê Văn Lương'),
('CloudBase VN',         '0101678945', 'https://cloudbase.vn',      NULL, 'hr@cloudbase.vn',      'HANOI',    'Nhân Chính',      '89 Nguyễn Trãi'),

-- [TP.HCM - 5 công ty]
('MicroShop Corp',       '0302553763', 'https://microshop.com.vn',  NULL, 'hr@microshop.com.vn',  'TPHCM',    'Tân Phú',         '182 Lê Đại Hành'),
('Saigon AI Lab',        '0302678901', 'https://saigonai.vn',       NULL, 'hr@saigonai.vn',       'TPHCM',    'Bình Thạnh',      '53 Đinh Tiên Hoàng'),
('FinTech Solutions',    '0302789012', 'https://fintechvn.com',     NULL, 'hr@fintechvn.com',     'TPHCM',    'Quận 1',          '110 Nguyễn Huệ'),
('MobileFirst Studio',   '0302890123', 'https://mobilefirst.vn',    NULL, 'hr@mobilefirst.vn',    'TPHCM',    'Phú Nhuận',       '30 Hoàng Văn Thụ'),
('DevOps Pro',           '0302901234', 'https://devopspro.vn',      NULL, 'hr@devopspro.vn',      'TPHCM',    'Quận 7',          '15 Nguyễn Lương Bằng'),

-- [ĐÀ NẴNG - 3 công ty]
('DaNang Digital Hub',   '0401112233', 'https://dndh.vn',           NULL, 'hr@dndh.vn',           'DANANG',   'Hải Châu',        '35 Bạch Đằng'),
('Central Code',         '0401223344', 'https://centralcode.vn',    NULL, 'hr@centralcode.vn',    'DANANG',   'Sơn Trà',         '8 Lê Văn Hiến'),
('Sunrise Outsourcing',  '0401334455', 'https://sunriseoutsrc.vn',  NULL, 'hr@sunriseoutsrc.vn',  'DANANG',   'Cẩm Lệ',          '120 Ông Ích Khiêm'),

-- [TỈNH KHÁC - 2 công ty]
('Mekong ERP',           '1501112233', 'https://mekong-erp.vn',     NULL, 'hr@mekong-erp.vn',     'CANTHO',   'Ninh Kiều',       '10 Đại lộ Hòa Bình'),
('Quang Ninh IT Park',   '2201112233', 'https://qnit.vn',           NULL, 'hr@qnit.vn',           'QUANGNINH','Hạ Long',         '200 Trần Quốc Nghiễn');

-- ============================================================
-- 2. HR USERS (15) — 1 HR per company
--    Format userName: hr_<slug_cty>
-- ============================================================

-- [HR Users — 15 users với role=HR]
INSERT INTO "user" (userName, pwd, fName, lName, email, phone, provId, ward, street, stat, role) VALUES
('hr_helios',       '123456', 'Nguyễn', 'Thu Hà',     'thu.ha@helios.vn',         '0901000001', 'HANOI',    'Dịch Vọng Hậu', '10 Phạm Văn Bạch', 'ACTIVE', 'HR'),
('hr_novatech',     '123456', 'Trần',   'Minh Khoa',  'minh.khoa@novatech.com.vn','0901000002', 'HANOI',    'Yên Hòa',       '1 Trần Hữu Dực',   'ACTIVE', 'HR'),
('hr_datastream',   '123456', 'Lê',     'Hoàng Yến',  'hoang.yen@datastream.vn',  '0901000003', 'HANOI',    'Mỹ Đình',       '72 Phạm Hùng',     'ACTIVE', 'HR'),
('hr_cybershield',  '123456', 'Phạm',   'Đức Thịnh',  'duc.thinh@cybershield.vn', '0901000004', 'HANOI',    'Trung Hòa',     '25 Lê Văn Lương',  'ACTIVE', 'HR'),
('hr_cloudbase',    '123456', 'Hoàng',  'Lan Anh',    'lan.anh@cloudbase.vn',     '0901000005', 'HANOI',    'Nhân Chính',    '89 Nguyễn Trãi',   'ACTIVE', 'HR'),
('hr_microshop',    '123456', 'Vũ',     'Thanh Tùng', 'thanh.tung@microshop.vn',  '0901000006', 'TPHCM',    'Tân Phú',       '182 Lê Đại Hành',  'ACTIVE', 'HR'),
('hr_saigonai',     '123456', 'Đặng',   'Phương Linh','phuong.linh@saigonai.vn',  '0901000007', 'TPHCM',    'Bình Thạnh',    '53 Đinh Tiên Hoàng','ACTIVE', 'HR'),
('hr_fintech',      '123456', 'Bùi',    'Trọng Đạt',  'trong.dat@fintechvn.com',  '0901000008', 'TPHCM',    'Quận 1',        '110 Nguyễn Huệ',   'ACTIVE', 'HR'),
('hr_mobilefirst',  '123456', 'Ngô',    'Thị Mai',    'thi.mai@mobilefirst.vn',   '0901000009', 'TPHCM',    'Phú Nhuận',     '30 Hoàng Văn Thụ', 'ACTIVE', 'HR'),
('hr_devopspro',    '123456', 'Đinh',   'Quang Huy',  'quang.huy@devopspro.vn',   '0901000010', 'TPHCM',    'Quận 7',        '15 Nguyễn Lương Bằng','ACTIVE','HR'),
('hr_dndh',         '123456', 'Lý',     'Xuân Dũng',  'xuan.dung@dndh.vn',        '0901000011', 'DANANG',   'Hải Châu',      '35 Bạch Đằng',     'ACTIVE', 'HR'),
('hr_centralcode',  '123456', 'Trương', 'Bảo Châu',   'bao.chau@centralcode.vn',  '0901000012', 'DANANG',   'Sơn Trà',       '8 Lê Văn Hiến',    'ACTIVE', 'HR'),
('hr_sunrise',      '123456', 'Đỗ',     'Khánh An',   'khanh.an@sunriseoutsrc.vn','0901000013', 'DANANG',   'Cẩm Lệ',        '120 Ông Ích Khiêm', 'ACTIVE','HR'),
('hr_mekong',       '123456', 'Hồ',     'Văn Phúc',   'van.phuc@mekong-erp.vn',   '0901000014', 'CANTHO',   'Ninh Kiều',     '10 Đại lộ Hòa Bình','ACTIVE','HR'),
('hr_qnit',         '123456', 'Mai',    'Thanh Sơn',  'thanh.son@qnit.vn',        '0901000015', 'QUANGNINH','Hạ Long',       '200 Trần Quốc Nghiễn','ACTIVE','HR');

-- [HR Records — gắn HR users với company + vị trí Recruiter]
INSERT INTO HR (userId, emailSign, posId, compId) VALUES
((SELECT userId FROM "user" WHERE userName='hr_helios'),      'Trân trọng,\nThu Hà - HR Helios',       (SELECT posId FROM HRPOSITION WHERE posName='Recruiter'),        (SELECT compId FROM COMPANY WHERE compName='Helios Software')),
((SELECT userId FROM "user" WHERE userName='hr_novatech'),    'Trân trọng,\nMinh Khoa - HR NovaTech',  (SELECT posId FROM HRPOSITION WHERE posName='Senior Recruiter'),  (SELECT compId FROM COMPANY WHERE compName='NovaTech Corporation')),
((SELECT userId FROM "user" WHERE userName='hr_datastream'),  'Trân trọng,\nHoàng Yến - HR DataStream',(SELECT posId FROM HRPOSITION WHERE posName='Recruiter'),        (SELECT compId FROM COMPANY WHERE compName='DataStream Systems')),
((SELECT userId FROM "user" WHERE userName='hr_cybershield'), 'Trân trọng,\nĐức Thịnh - HR CyberShield',(SELECT posId FROM HRPOSITION WHERE posName='HR Manager'),      (SELECT compId FROM COMPANY WHERE compName='CyberShield Security')),
((SELECT userId FROM "user" WHERE userName='hr_cloudbase'),   'Trân trọng,\nLan Anh - HR CloudBase',   (SELECT posId FROM HRPOSITION WHERE posName='Recruiter'),        (SELECT compId FROM COMPANY WHERE compName='CloudBase VN')),
((SELECT userId FROM "user" WHERE userName='hr_microshop'),   'Trân trọng,\nThanh Tùng - HR MicroShop',(SELECT posId FROM HRPOSITION WHERE posName='Recruiter'),        (SELECT compId FROM COMPANY WHERE compName='MicroShop Corp')),
((SELECT userId FROM "user" WHERE userName='hr_saigonai'),    'Trân trọng,\nPhương Linh - HR SaigonAI',(SELECT posId FROM HRPOSITION WHERE posName='Senior Recruiter'),  (SELECT compId FROM COMPANY WHERE compName='Saigon AI Lab')),
((SELECT userId FROM "user" WHERE userName='hr_fintech'),     'Trân trọng,\nTrọng Đạt - HR FinTech',  (SELECT posId FROM HRPOSITION WHERE posName='HR Manager'),       (SELECT compId FROM COMPANY WHERE compName='FinTech Solutions')),
((SELECT userId FROM "user" WHERE userName='hr_mobilefirst'), 'Trân trọng,\nThị Mai - HR MobileFirst', (SELECT posId FROM HRPOSITION WHERE posName='Recruiter'),        (SELECT compId FROM COMPANY WHERE compName='MobileFirst Studio')),
((SELECT userId FROM "user" WHERE userName='hr_devopspro'),   'Trân trọng,\nQuang Huy - HR DevOps Pro',(SELECT posId FROM HRPOSITION WHERE posName='Recruiter'),        (SELECT compId FROM COMPANY WHERE compName='DevOps Pro')),
((SELECT userId FROM "user" WHERE userName='hr_dndh'),        'Trân trọng,\nXuân Dũng - HR DNDH',     (SELECT posId FROM HRPOSITION WHERE posName='Recruiter'),        (SELECT compId FROM COMPANY WHERE compName='DaNang Digital Hub')),
((SELECT userId FROM "user" WHERE userName='hr_centralcode'), 'Trân trọng,\nBảo Châu - HR CentralCode',(SELECT posId FROM HRPOSITION WHERE posName='Recruiter'),        (SELECT compId FROM COMPANY WHERE compName='Central Code')),
((SELECT userId FROM "user" WHERE userName='hr_sunrise'),     'Trân trọng,\nKhánh An - HR Sunrise',   (SELECT posId FROM HRPOSITION WHERE posName='Senior Recruiter'),  (SELECT compId FROM COMPANY WHERE compName='Sunrise Outsourcing')),
((SELECT userId FROM "user" WHERE userName='hr_mekong'),      'Trân trọng,\nVăn Phúc - HR Mekong',    (SELECT posId FROM HRPOSITION WHERE posName='Recruiter'),        (SELECT compId FROM COMPANY WHERE compName='Mekong ERP')),
((SELECT userId FROM "user" WHERE userName='hr_qnit'),        'Trân trọng,\nThanh Sơn - HR QNIT',     (SELECT posId FROM HRPOSITION WHERE posName='Recruiter'),        (SELECT compId FROM COMPANY WHERE compName='Quang Ninh IT Park'));

-- ============================================================
-- 3. ADMIN PHỤ (Moderator) — Kiểm duyệt nội dung synthetic
-- ============================================================

INSERT INTO "user" (userName, pwd, fName, lName, email, phone, provId, ward, street, stat, role)
VALUES ('moderator', '123456', 'Phạm', 'Văn Mod', 'moderator@micareer.vn', '0900000099', 'HANOI', 'Cầu Giấy', '1 Xuân Thủy', 'ACTIVE', 'ADMIN');

INSERT INTO "admin" (userId, lastIp, roleId) VALUES (
    (SELECT userId FROM "user" WHERE userName = 'moderator'),
    '127.0.0.1',
    (SELECT roleId FROM ADMINROLE WHERE roleName = 'Moderator')
);

-- ============================================================
-- THỐNG KÊ CUỐI
-- ============================================================
-- SELECT 'COMPANY', COUNT(*) FROM COMPANY
-- UNION ALL SELECT 'HR_USER', COUNT(*) FROM HR
-- UNION ALL SELECT 'ADMIN_USER', COUNT(*) FROM "admin";
-- Expected: COMPANY=15, HR_USER=15, ADMIN_USER=2 (admin + moderator)
