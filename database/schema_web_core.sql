-- Ae muốn chạy trong PGAdmin thì phải chạy 3 khối riêng nhé, DROP
-- DROP DATABASE IF EXISTS micareer_lite_db;
-- CREATE DATABASE micareer_lite_db;

-- ============================================================
-- [NMAIex] MASTER DATA — Phải đặt TRƯỚC user và COMPANY (FK)
-- ============================================================

CREATE TABLE REGION (
  regId   VARCHAR(20)  PRIMARY KEY,
  regName VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE PROVINCE (
  provId      VARCHAR(20)  PRIMARY KEY,   -- Mã đầy đủ: HANOI, TPHCM, DANANG...
  provName    VARCHAR(100) NOT NULL UNIQUE,
  regId       VARCHAR(20)  NOT NULL,
  mergedFrom  TEXT,                        -- Ghi chú sáp nhập (VD: 'Hải Phòng + Hải Dương')
  FOREIGN KEY (regId) REFERENCES REGION(regId)
);

CREATE TABLE JOBLEVEL (
  levelId     SERIAL PRIMARY KEY,
  levelName   VARCHAR(50) NOT NULL UNIQUE,  -- Intern/Fresher/Junior/Middle/Senior/Lead/Manager/Director
  minYears    INT NOT NULL DEFAULT 0,        -- Số năm KN tối thiểu để tính Seniority Penalty
  maxYears    INT,                           -- NULL = không giới hạn trên
  description TEXT
);

CREATE TABLE JOBCATEGORY (
  catId       SERIAL PRIMARY KEY,
  catName     VARCHAR(100) NOT NULL UNIQUE,
  description TEXT
);

-- [NMAIex] Bảng ngôn ngữ chuẩn (Language Requirement System — Phase 2.5)
-- Cập nhật thủ công khi có ngôn ngữ mới phổ biến trong thị trường VN
CREATE TABLE LANGUAGE (
    langId   SERIAL PRIMARY KEY,
    langCode VARCHAR(10)  NOT NULL UNIQUE,  -- ISO 639-1: 'en', 'ja', 'ko', 'zh', 'vi'...
    langName VARCHAR(50)  NOT NULL
);

-- [NMAIex] Yêu cầu ngôn ngữ của Job (N-N, REQUIRED vs PREFERRED)
-- Lưu ý: tiếng Việt ('vi') không cần chỉ định vì là mặc định của thị trường VN
-- Chỉ cần khai báo khi Job yêu cầu ngoại ngữ hoặc yêu cầu tiếng Việt ở level đặc biệt
CREATE TABLE JOB_LANG_REQUIREMENT (
    jobPostId  INT         NOT NULL REFERENCES JOBPOSTING(jobPostId) ON DELETE CASCADE,
    langId     INT         NOT NULL REFERENCES LANGUAGE(langId),
    reqType    VARCHAR(10) NOT NULL CHECK (reqType IN ('REQUIRED', 'PREFERRED')),
    minLevel   VARCHAR(20) CHECK (minLevel IN ('BASIC','INTERMEDIATE','ADVANCED','FLUENT','NATIVE')),
    PRIMARY KEY (jobPostId, langId)
);

-- ============================================================
-- Core User & Account tables
-- ============================================================

CREATE TABLE "user" (
  userId    SERIAL PRIMARY KEY,
  userName  VARCHAR(255) NOT NULL UNIQUE,
  pwd       VARCHAR(255) NOT NULL,
  fName     VARCHAR(100) NOT NULL,
  lName     VARCHAR(100) NOT NULL,
  email     VARCHAR(255) NOT NULL UNIQUE,
  phone     VARCHAR(20) UNIQUE,
  provId    VARCHAR(20) REFERENCES PROVINCE(provId),  -- [NMAIex] FK thay thế prov string
  ward      VARCHAR(100) NOT NULL,
  street    VARCHAR(255) NOT NULL,
  stat      VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
  role      VARCHAR(20) NOT NULL,
  createdAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
 
CREATE TABLE CANDIDATE (
  userId INT PRIMARY KEY,
  bio TEXT,
  cvUrl VARCHAR(255),
  dob DATE,
  expyears INT,
  FOREIGN KEY (userId) REFERENCES "user"(userId)
);
 
CREATE TABLE HRPOSITION (
  posId SERIAL PRIMARY KEY,
  posName VARCHAR(255) NOT NULL UNIQUE,
  description TEXT
);
 
CREATE TABLE COMPANY (
  compId       SERIAL PRIMARY KEY,
  compName     VARCHAR(255) NOT NULL,
  taxCode      VARCHAR(50) UNIQUE,
  webUrl       VARCHAR(255),
  logoUrl      VARCHAR(255),
  contactEmail VARCHAR(255),
  provId       VARCHAR(20) REFERENCES PROVINCE(provId),  -- [NMAIex] FK thay thế prov string
  ward         VARCHAR(100) NOT NULL,
  street       VARCHAR(255) NOT NULL
);
CREATE TABLE HR (
  userId INT PRIMARY KEY,
  emailSign TEXT,
  posId INT NOT NULL,
  compId INT NOT NULL,
  FOREIGN KEY (compId) REFERENCES COMPANY(compId),
  FOREIGN KEY (posId) REFERENCES HRPOSITION(posId),
  FOREIGN KEY (userId) REFERENCES "user"(userId)
);
 
--ADMIN & RBAC 
CREATE TABLE ADMINROLE (
  roleId SERIAL PRIMARY KEY,
  roleName VARCHAR(100) NOT NULL,
  description TEXT
);
 
CREATE TABLE "admin" (
  userId INT PRIMARY KEY,
  lastIp VARCHAR(50),
  roleId INT NOT NULL,
  FOREIGN KEY (roleId) REFERENCES ADMINROLE(roleId),
  FOREIGN KEY (userId) REFERENCES "user"(userId)
);
 
CREATE TABLE "permission" (
  permId SERIAL PRIMARY KEY,
  permCode VARCHAR(100) NOT NULL UNIQUE,
  description TEXT
);
 
CREATE TABLE HASPERM (
  roleId INT NOT NULL,
  permId INT NOT NULL,
  PRIMARY KEY (roleId, permId),
  FOREIGN KEY (roleId) REFERENCES ADMINROLE(roleId),
  FOREIGN KEY (permId) REFERENCES "permission"(permId)
);
 
--JOB & APPLICATION 
 
CREATE TABLE JOBPOSTING (
  jobPostId   SERIAL PRIMARY KEY,
  title       VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  minSalary   INT,
  maxSalary   INT,
  workLoc     VARCHAR(255),              -- Giữ nguyên cho mục đích display text
  workMode    VARCHAR(50),               -- ONSITE | HYBRID | REMOTE
  provId      VARCHAR(20) REFERENCES PROVINCE(provId),  -- [NMAIex] FK địa lý cho hard filter
  createdAt   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expAt       TIMESTAMP NOT NULL,
  compId      INT NOT NULL,
  FOREIGN KEY (compId) REFERENCES COMPANY(compId)
);

-- [NMAIex] Bảng nối N-N: JobPosting ↔ JobLevel
CREATE TABLE JOB_LEVEL_MAP (
  jobPostId INT NOT NULL,
  levelId   INT NOT NULL,
  PRIMARY KEY (jobPostId, levelId),
  FOREIGN KEY (jobPostId) REFERENCES JOBPOSTING(jobPostId) ON DELETE CASCADE,
  FOREIGN KEY (levelId)   REFERENCES JOBLEVEL(levelId)
);

-- [NMAIex] Bảng nối N-N: JobPosting ↔ JobCategory
CREATE TABLE JOB_CATEGORY_MAP (
  jobPostId INT NOT NULL,
  catId     INT NOT NULL,
  PRIMARY KEY (jobPostId, catId),
  FOREIGN KEY (jobPostId) REFERENCES JOBPOSTING(jobPostId) ON DELETE CASCADE,
  FOREIGN KEY (catId)     REFERENCES JOBCATEGORY(catId)
);
 
CREATE TABLE SKILL (
  skillId SERIAL PRIMARY KEY,
  skillName VARCHAR(100) NOT NULL UNIQUE,
  description TEXT
);
 
CREATE TABLE JOBREQUIREMENT (
  jobPostId INT NOT NULL,
  skillId INT NOT NULL,
  PRIMARY KEY (jobPostId, skillId),
  FOREIGN KEY (jobPostId) REFERENCES JOBPOSTING(jobPostId),
  FOREIGN KEY (skillId) REFERENCES SKILL(skillId)
);
 
CREATE TABLE CANDIDATESKILL (
  userId INT NOT NULL,                 
  skillId INT NOT NULL,
  PRIMARY KEY (userId, skillId),
  FOREIGN KEY (userId) REFERENCES CANDIDATE(userId),
  FOREIGN KEY (skillId) REFERENCES SKILL(skillId)
);

-- [NMAIex] Strategy C: Unmatched skills với vector cho fuzzy matching (Tầng 2)
CREATE TABLE CANDIDATE_SKILL_RAW (
    rawId      SERIAL PRIMARY KEY,
    candId     INT NOT NULL REFERENCES CANDIDATE(userId) ON DELETE CASCADE,
    rawText    VARCHAR(200) NOT NULL,
    embedding  vector(__NMAIEX_SKILL_EMBEDDING_DIM__),  -- dims từ NMAIEX_SKILL_EMBEDDING_DIMS
    createdAt  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_cand_skill_raw_cand ON CANDIDATE_SKILL_RAW(candId);

-- [NMAIex] Strategy C: Unmatched skills phía Job (khi HR nhập text-free skill)
-- Dung cho HR hybrid skill input -> LLM mapper -> unmatched -> embed -> JOB_SKILL_RAW
CREATE TABLE JOB_SKILL_RAW (
    rawId      SERIAL PRIMARY KEY,
    jobPostId  INT NOT NULL REFERENCES JOBPOSTING(jobPostId) ON DELETE CASCADE,
    rawText    VARCHAR(200) NOT NULL,
    embedding  vector(__NMAIEX_SKILL_EMBEDDING_DIM__),  -- cùng dims với CANDIDATE_SKILL_RAW
    createdAt  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_job_skill_raw_job ON JOB_SKILL_RAW(jobPostId);

CREATE TABLE JOBAPPLICATION (
  jobAppId SERIAL PRIMARY KEY,
  candidateId INT NOT NULL,
  jobPostId INT NOT NULL,
  appliedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  stat VARCHAR(30) NOT NULL,
  cvSnapUrl VARCHAR(255) NOT NULL,
  coverLetter TEXT,
  FOREIGN KEY (candidateId) REFERENCES CANDIDATE(userId),
  FOREIGN KEY (jobPostId) REFERENCES JOBPOSTING(jobPostId)
);
 
CREATE TABLE APPSTATUSHISTORY (
  histId SERIAL PRIMARY KEY,
  jobAppId INT NOT NULL,
  hrId INT NOT NULL,
  oldStat VARCHAR(30) NOT NULL,
  newStat VARCHAR(30) NOT NULL,
  changedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (jobAppId) REFERENCES JOBAPPLICATION(jobAppId),
  FOREIGN KEY (hrId) REFERENCES HR(userId)
);
 
--INTERVIEW & OFFER 
 
CREATE TABLE INTERVIEW (
  intervId SERIAL PRIMARY KEY,
  jobAppId INT NOT NULL,
  startAt TIMESTAMP NOT NULL,
  endAt TIMESTAMP NOT NULL,
  "mode" VARCHAR(50) NOT NULL,
  linkMeet VARCHAR(255),
  loc VARCHAR(255),
  FOREIGN KEY (jobAppId) REFERENCES JOBAPPLICATION(jobAppId)
);
 
CREATE TABLE INTERVIEWFEEDBACK (
  feedbackId SERIAL PRIMARY KEY,
  intervId INT NOT NULL,
  hrId INT NOT NULL,
  score INT NOT NULL,
  cmt TEXT,
  subAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (intervId) REFERENCES INTERVIEW(intervId),
  FOREIGN KEY (hrId) REFERENCES HR(userId)
);
 
CREATE TABLE OFFER (
  offerId SERIAL PRIMARY KEY,
  jobAppId INT NOT NULL,
  salary INT NOT NULL,
  description TEXT,
  stat VARCHAR(20) NOT NULL,
  subAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ver INT NOT NULL,
  hrId INT NOT NULL,
  FOREIGN KEY (jobAppId) REFERENCES JOBAPPLICATION(jobAppId),
  FOREIGN KEY (hrId) REFERENCES HR(userId)
);
 
-- EMAIL 
 
CREATE TABLE EMAILTYPE (
  typeId SERIAL PRIMARY KEY,
  typeName VARCHAR(100) NOT NULL UNIQUE,
  description TEXT
);
 
CREATE TABLE EMAILTEMPLATE (
  tmplId SERIAL PRIMARY KEY,
  typeId INT NOT NULL,
  subj VARCHAR(255) NOT NULL,
  body TEXT NOT NULL,
  description TEXT,
  FOREIGN KEY (typeId) REFERENCES EMAILTYPE(typeId)
);
 
CREATE TABLE EMAILLOG (
  logId SERIAL PRIMARY KEY,
  tmplId INT NOT NULL,
  jobAppId INT NOT NULL,
  hrId INT NOT NULL,                  
  "content" TEXT NOT NULL,
  sentAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  rcvEmail VARCHAR(255) NOT NULL,
  FOREIGN KEY (tmplId) REFERENCES EMAILTEMPLATE(tmplId),
  FOREIGN KEY (jobAppId) REFERENCES JOBAPPLICATION(jobAppId),
  FOREIGN KEY (hrId) REFERENCES HR(userId)
);

