-- Initial schema. Applied automatically by PostgreSQL on an empty Docker volume.
-- JSON (rather than JSONB) intentionally matches SQLAlchemy's portable JSON type.
BEGIN;
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(36) PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES conversations(id),
    role VARCHAR(16) NOT NULL CHECK (role IN ('user','assistant')),
    content TEXT NOT NULL,
    payload JSON NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_messages_session_id ON messages(session_id);
CREATE TABLE IF NOT EXISTS tool_calls (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES conversations(id),
    request_id VARCHAR(36) NOT NULL,
    name VARCHAR(64) NOT NULL,
    input JSON NOT NULL,
    output JSON NOT NULL,
    status VARCHAR(16) NOT NULL CHECK (status IN ('ok','error')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_tool_calls_session_id ON tool_calls(session_id);
CREATE INDEX IF NOT EXISTS ix_tool_calls_request_id ON tool_calls(request_id);
COMMIT;
