CREATE TABLE IF NOT EXISTS audit.ingestion_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('started', 'completed', 'failed')),
    source_file TEXT NOT NULL,
    source_hash TEXT,
    row_count BIGINT,
    error_message TEXT
);

ALTER TABLE audit.ingestion_runs
ADD COLUMN IF NOT EXISTS source_hash TEXT;
