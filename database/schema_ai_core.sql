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
  createdAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (jobAppId) REFERENCES JOBAPPLICATION(jobAppId)
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
