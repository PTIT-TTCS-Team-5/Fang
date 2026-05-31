CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE AIINDEXJOB (
  indexJobId SERIAL PRIMARY KEY,
  jobAppId INT NOT NULL,              
  stat VARCHAR(50) NOT NULL,
  retryCount INT NOT NULL DEFAULT 0,
  errorMsg TEXT,
  createdAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  startedAt TIMESTAMP,
  finishedAt TIMESTAMP,
  FOREIGN KEY (jobAppId) REFERENCES JOBAPPLICATION(jobAppId)
);
 
CREATE TABLE CVPARSED (
  cvParsedId SERIAL PRIMARY KEY,
  jobAppId INT NOT NULL UNIQUE,
  rawText TEXT NOT NULL,
  parsedJson JSONB,
  parserVer VARCHAR(50) NOT NULL,
  parseAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (jobAppId) REFERENCES JOBAPPLICATION(jobAppId)
);

CREATE TABLE NMAIEX_CANDIDATE_ENRICHMENT_JOB (
  enrichmentJobId SERIAL PRIMARY KEY,
  indexJobId INT REFERENCES AIINDEXJOB(indexJobId) ON DELETE SET NULL,
  jobAppId INT NOT NULL UNIQUE,
  candidateId INT,
  cvParsedId INT,
  stat VARCHAR(50) NOT NULL,
  retryCount INT NOT NULL DEFAULT 0,
  maxRetryCount INT NOT NULL DEFAULT 5,
  nextRunAt TIMESTAMPTZ,
  errorMsg TEXT,
  createdAt TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  startedAt TIMESTAMPTZ,
  finishedAt TIMESTAMPTZ,
  updatedAt TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  FOREIGN KEY (jobAppId) REFERENCES JOBAPPLICATION(jobAppId) ON DELETE CASCADE,
  FOREIGN KEY (candidateId) REFERENCES CANDIDATE(userId) ON DELETE CASCADE,
  FOREIGN KEY (cvParsedId) REFERENCES CVPARSED(cvParsedId) ON DELETE CASCADE
);

CREATE INDEX idx_nmaiex_candidate_enrichment_due
  ON NMAIEX_CANDIDATE_ENRICHMENT_JOB(stat, nextRunAt, retryCount);
 
CREATE TABLE AIDOCUMENTCHUNK (
  chunkId SERIAL PRIMARY KEY,
  jobAppId INT NOT NULL,
  sourceType VARCHAR(100) NOT NULL,
  content TEXT NOT NULL,
  chunkIndex INT NOT NULL,
  tokenCount INT NOT NULL,
  metadata JSONB,
  -- Mac dinh cho DEV/Test la halfvec(__TTCS_EMBEDDING_DIM__)
  -- Neu muon doi sang full precision, chi can sua:
  --   1. halfvec(__TTCS_EMBEDDING_DIM__) -> vector(__TTCS_EMBEDDING_DIM__)
  --   2. halfvec_cosine_ops -> vector_cosine_ops
  --   3. EMBEDDING_VECTOR_TYPE=vector trong env
  embedding halfvec(__TTCS_EMBEDDING_DIM__),
  createdAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_aidocumentchunk_hnsw_cosine
  ON AIDOCUMENTCHUNK
  USING hnsw (embedding halfvec_cosine_ops)
  WITH (m = 16, ef_construction = 64);
 
CREATE TABLE AIQUERYLOG (
  queryId SERIAL PRIMARY KEY,
  jobAppId INT NOT NULL,
  hrId INT NOT NULL,
  prompt TEXT NOT NULL,
  response TEXT NOT NULL,
  topK INT NOT NULL,
  latencyMs INT NOT NULL,
  model VARCHAR(100),
  modelMode VARCHAR(50),
  fallbackPath TEXT,
  createdAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (jobAppId) REFERENCES JOBAPPLICATION(jobAppId),
  FOREIGN KEY (hrId) REFERENCES HR(userId)
);

-- ========== Chat Management (FANG v2) ==========

CREATE TABLE AICHATCONVERSATION (
  conversationId UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jobAppId INT NOT NULL,
  hrId INT NOT NULL,
  createdAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  lastMessageAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (jobAppId) REFERENCES JOBAPPLICATION(jobAppId),
  FOREIGN KEY (hrId) REFERENCES HR(userId)
);

CREATE INDEX IF NOT EXISTS idx_conversation_hr_jobapp
  ON AICHATCONVERSATION (hrId, jobAppId);

CREATE TABLE AICHATMESSAGE (
  messageId SERIAL PRIMARY KEY,
  conversationId UUID NOT NULL,
  role VARCHAR(20) NOT NULL,           -- 'user' | 'assistant' | 'system'
  content TEXT NOT NULL,
  model VARCHAR(100),                  -- null cho user/system messages
  modelMode VARCHAR(50),
  topK INT,
  latencyMs INT,
  fallbackPath TEXT,
  summarized BOOLEAN NOT NULL DEFAULT FALSE,
  createdAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (conversationId) REFERENCES AICHATCONVERSATION(conversationId)
);

CREATE INDEX IF NOT EXISTS idx_chatmessage_conversation
  ON AICHATMESSAGE (conversationId, createdAt);

-- ========== JobPosting Agent (FANG C3.1) ==========

-- Tool catalog: registry of all 7 MVP JobPosting Agent tools
CREATE TABLE AIJOBPOSTINGTOOL (
    toolId           SERIAL PRIMARY KEY,
    toolName         VARCHAR(100) NOT NULL UNIQUE,
    displayName      VARCHAR(200) NOT NULL,
    description      TEXT,
    inputSchemaJson  JSONB,
    outputSchemaJson JSONB,
    isEnabled        BOOLEAN NOT NULL DEFAULT TRUE,
    category         VARCHAR(50),
    createdAt        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Conversations scoped to a single jobPostId + hrId pair.
-- No cascade delete from JOBPOSTING or HR; archive is soft-delete only.
CREATE TABLE AIJOBPOSTINGCHATCONVERSATION (
    conversationId UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jobPostId      INT NOT NULL,
    hrId           INT NOT NULL,
    title          VARCHAR(200) NOT NULL DEFAULT 'Cuộc trò chuyện mới',
    createdAt      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lastMessageAt  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    isArchived     BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (jobPostId) REFERENCES JOBPOSTING(jobPostId),
    FOREIGN KEY (hrId) REFERENCES HR(userId)
);

CREATE INDEX IF NOT EXISTS idx_jpchat_conv_jobpost_hr
    ON AIJOBPOSTINGCHATCONVERSATION (jobPostId, hrId);

-- Messages: user, assistant, tool_call, tool_result, system
CREATE TABLE AIJOBPOSTINGCHATMESSAGE (
    messageId      SERIAL PRIMARY KEY,
    conversationId UUID NOT NULL,
    role           VARCHAR(20) NOT NULL,
    content        TEXT NOT NULL,
    toolName       VARCHAR(100),
    toolCallId     VARCHAR(100),
    model          VARCHAR(100),
    modelMode      VARCHAR(50),
    latencyMs      INT,
    summarized     BOOLEAN NOT NULL DEFAULT FALSE,
    createdAt      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversationId) REFERENCES AIJOBPOSTINGCHATCONVERSATION(conversationId)
);

CREATE INDEX IF NOT EXISTS idx_jpchat_msg_conv_created
    ON AIJOBPOSTINGCHATMESSAGE (conversationId, createdAt);

-- Persistent working-set state for each conversation (1-to-1)
CREATE TABLE AIJOBPOSTINGCHATSTATE (
    conversationId UUID PRIMARY KEY,
    stateJson      JSONB NOT NULL DEFAULT '{}',
    updatedAt      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversationId) REFERENCES AIJOBPOSTINGCHATCONVERSATION(conversationId)
);

-- Sanitized tool call audit log (no raw CV/email/phone data)
CREATE TABLE AIJOBPOSTINGTOOLCALLLOG (
    toolCallLogId  SERIAL PRIMARY KEY,
    conversationId UUID NOT NULL,
    messageId      INT,
    jobPostId      INT NOT NULL,
    hrId           INT NOT NULL,
    toolId         INT,
    toolName       VARCHAR(100) NOT NULL,
    toolInput      JSONB,
    toolOutputMeta JSONB,
    status         VARCHAR(20) NOT NULL DEFAULT 'success',
    latencyMs      INT,
    errorMsg       TEXT,
    createdAt      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversationId) REFERENCES AIJOBPOSTINGCHATCONVERSATION(conversationId),
    FOREIGN KEY (messageId) REFERENCES AIJOBPOSTINGCHATMESSAGE(messageId),
    FOREIGN KEY (toolId) REFERENCES AIJOBPOSTINGTOOL(toolId)
);

CREATE INDEX IF NOT EXISTS idx_jpchat_toollog_conv
    ON AIJOBPOSTINGTOOLCALLLOG (conversationId);

-- ---- Seed: 7 MVP tool catalog rows ----
INSERT INTO AIJOBPOSTINGTOOL (toolName, displayName, description, category) VALUES
    ('get_job_posting_context',    'Xem thông tin tin tuyển dụng', 'Lấy thông tin đầy đủ về tin tuyển dụng, yêu cầu và số lượng ứng viên.', 'context'),
    ('get_job_candidate_ranking',  'Xếp hạng ứng viên',            'Xếp hạng ứng viên phù hợp nhất cho tin tuyển dụng dựa trên điểm tổng hợp.', 'ranking'),
    ('search_job_applications_text','Tìm kiếm ứng viên',           'Tìm kiếm ứng viên bằng full-text search trên CV/hồ sơ.', 'search'),
    ('get_job_application_summary','Tóm tắt ứng viên',             'Xem tóm tắt thông tin ứng viên: kỹ năng, kinh nghiệm, ngôn ngữ, địa chỉ.', 'detail'),
    ('get_job_application_full_cv','Xem CV đầy đủ',                'Xem toàn bộ nội dung CV của ứng viên (có masking PII).', 'detail'),
    ('get_candidate_ats_history',  'Lịch sử tuyển dụng',           'Xem lịch sử trạng thái ứng tuyển, phỏng vấn và phản hồi của ứng viên.', 'detail'),
    ('count_job_applications',     'Đếm ứng viên',                 'Đếm tổng số ứng viên với các bộ lọc tùy chọn.', 'aggregate')
ON CONFLICT (toolName) DO NOTHING;

