-- PiBot — Schema PostgreSQL v1.2

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

CREATE TABLE IF NOT EXISTS agent_conversations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content     TEXT NOT NULL,
    agent_name  TEXT,
    channel     TEXT,
    is_voice    BOOLEAN DEFAULT FALSE,
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON agent_conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON agent_conversations(created_at DESC);

CREATE TABLE IF NOT EXISTS agent_audit_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name      TEXT NOT NULL,
    action          TEXT NOT NULL,
    input_payload   JSONB,
    output_payload  JSONB,
    status          TEXT NOT NULL CHECK (status IN ('ok', 'confirmed', 'rejected', 'blocked', 'expired', 'error')),
    user_id         TEXT,
    channel         TEXT,
    duration_ms     INTEGER,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_agent ON agent_audit_log(agent_name);
CREATE INDEX IF NOT EXISTS idx_audit_status ON agent_audit_log(status);
CREATE INDEX IF NOT EXISTS idx_audit_created ON agent_audit_log(created_at DESC);

CREATE TABLE IF NOT EXISTS agent_confirmations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    redis_key   TEXT NOT NULL UNIQUE,
    agent_name  TEXT NOT NULL,
    action      TEXT NOT NULL,
    payload     JSONB,
    status      TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'rejected', 'expired')),
    user_id     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS agent_memory (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key         TEXT NOT NULL UNIQUE,
    value       TEXT NOT NULL,
    source      TEXT,
    category    TEXT DEFAULT 'general',
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_embeddings (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content     TEXT NOT NULL,
    embedding   vector(1536),
    source_type TEXT NOT NULL,
    source_id   UUID,
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_embeddings_source ON agent_embeddings(source_type);
CREATE INDEX IF NOT EXISTS idx_embeddings_created ON agent_embeddings(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON agent_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS agent_alerts (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    severity    TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'urgent', 'critical')),
    source      TEXT NOT NULL,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,
    context     JSONB DEFAULT '{}',
    sent_to     TEXT[],
    status      TEXT DEFAULT 'new' CHECK (status IN ('new', 'sent', 'read', 'resolved', 'dismissed')),
    resolved_by TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON agent_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON agent_alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON agent_alerts(created_at DESC);

CREATE TABLE IF NOT EXISTS agent_prompt_versions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_name     TEXT NOT NULL,
    version         INTEGER NOT NULL,
    content         TEXT NOT NULL,
    change_reason   TEXT,
    proposed_by     TEXT DEFAULT 'meta_agent',
    approved_by     TEXT,
    status          TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'active', 'rollback')),
    performance     JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    activated_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_prompts_name ON agent_prompt_versions(prompt_name);
CREATE INDEX IF NOT EXISTS idx_prompts_status ON agent_prompt_versions(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_prompts_active ON agent_prompt_versions(prompt_name) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS meta_agent_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_type   TEXT NOT NULL,
    findings        TEXT NOT NULL,
    recommendations JSONB DEFAULT '[]',
    audit_ids       UUID[],
    status          TEXT DEFAULT 'new' CHECK (status IN ('new', 'reviewing', 'applied', 'dismissed')),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_meta_log_type ON meta_agent_log(analysis_type);
CREATE INDEX IF NOT EXISTS idx_meta_log_created ON meta_agent_log(created_at DESC);
