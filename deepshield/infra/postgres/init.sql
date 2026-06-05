-- ============================================================
-- DeepShield Enterprise — PostgreSQL Schema
-- Run: psql -U deepshield -d deepshield -f init.sql
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ── Organizations ────────────────────────────────────────────
CREATE TABLE organizations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    plan            VARCHAR(50) NOT NULL DEFAULT 'free'
                        CHECK (plan IN ('free','pro','enterprise','government')),
    monthly_quota   INTEGER NOT NULL DEFAULT 1000,
    api_tier        VARCHAR(50) NOT NULL DEFAULT 'free',
    logo_url        TEXT,
    contact_email   VARCHAR(255),
    country_code    CHAR(2),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_org_slug ON organizations(slug);
CREATE INDEX idx_org_plan ON organizations(plan);

-- ── Users ────────────────────────────────────────────────────
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    full_name       VARCHAR(255),
    role            VARCHAR(50) NOT NULL DEFAULT 'analyst'
                        CHECK (role IN ('super_admin','org_admin','analyst','viewer','api_client')),
    mfa_enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret      TEXT,
    last_login_at   TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_org    ON users(org_id);
CREATE INDEX idx_users_email  ON users(email);
CREATE INDEX idx_users_role   ON users(role);

-- ── API Keys ─────────────────────────────────────────────────
CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    key_hash        TEXT NOT NULL UNIQUE,
    key_prefix      VARCHAR(10) NOT NULL,
    rate_limit_rpm  INTEGER NOT NULL DEFAULT 60,
    scopes          TEXT[] NOT NULL DEFAULT ARRAY['detect','upload'],
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_apikeys_org  ON api_keys(org_id);
CREATE INDEX idx_apikeys_hash ON api_keys(key_hash);

-- ── Analyses ─────────────────────────────────────────────────
CREATE TABLE analyses (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID NOT NULL REFERENCES users(id),
    org_id           UUID NOT NULL REFERENCES organizations(id),
    media_type       VARCHAR(20) NOT NULL CHECK (media_type IN ('image','video','audio')),
    s3_key           TEXT,
    original_filename TEXT,
    file_size_bytes  BIGINT,
    file_sha256      VARCHAR(64),
    verdict          VARCHAR(20) CHECK (verdict IN ('deepfake','authentic','uncertain')),
    confidence       FLOAT,
    fake_probability FLOAT,
    heatmap_url      TEXT,
    processing_ms    INTEGER,
    status           VARCHAR(20) NOT NULL DEFAULT 'pending'
                         CHECK (status IN ('pending','queued','processing','completed','failed')),
    error_message    TEXT,
    metadata         JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMPTZ
);

CREATE INDEX idx_analyses_org        ON analyses(org_id);
CREATE INDEX idx_analyses_user       ON analyses(user_id);
CREATE INDEX idx_analyses_verdict    ON analyses(verdict);
CREATE INDEX idx_analyses_status     ON analyses(status);
CREATE INDEX idx_analyses_created    ON analyses(created_at DESC);
CREATE INDEX idx_analyses_sha256     ON analyses(file_sha256);

-- ── Detections (per-model results) ───────────────────────────
CREATE TABLE detections (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id   UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    model_name    VARCHAR(100) NOT NULL,
    score         FLOAT NOT NULL,
    confidence    FLOAT NOT NULL,
    processing_ms INTEGER,
    region_data   JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_detections_analysis ON detections(analysis_id);
CREATE INDEX idx_detections_model    ON detections(model_name);

-- ── Reports ──────────────────────────────────────────────────
CREATE TABLE reports (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id     UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    pdf_s3_key      TEXT,
    pdf_url         TEXT,
    exif_data       JSONB,
    file_sha256     VARCHAR(64),
    blockchain_tx   VARCHAR(100),
    blockchain_net  VARCHAR(50),
    ipfs_cid        TEXT,
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    generated_by    UUID REFERENCES users(id)
);

CREATE INDEX idx_reports_analysis ON reports(analysis_id);

-- ── Evidence chain (blockchain anchors) ──────────────────────
CREATE TABLE evidence_chain (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id    UUID NOT NULL REFERENCES analyses(id),
    tx_hash        VARCHAR(100) UNIQUE,
    block_number   BIGINT,
    network        VARCHAR(50) NOT NULL DEFAULT 'polygon',
    ipfs_cid       TEXT,
    anchored_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    anchored_by    UUID REFERENCES users(id)
);

-- ── Audit logs ───────────────────────────────────────────────
CREATE TABLE audit_logs (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID REFERENCES users(id),
    org_id        UUID REFERENCES organizations(id),
    action        VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id   UUID,
    ip_address    INET,
    user_agent    TEXT,
    request_id    UUID,
    metadata      JSONB,
    ts            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_user   ON audit_logs(user_id);
CREATE INDEX idx_audit_org    ON audit_logs(org_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_ts     ON audit_logs(ts DESC);

-- ── Model registry ───────────────────────────────────────────
CREATE TABLE model_registry (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name           VARCHAR(100) NOT NULL,
    version        VARCHAR(20) NOT NULL,
    mlflow_run_id  VARCHAR(100),
    accuracy       FLOAT,
    auc_roc        FLOAT,
    f1_score       FLOAT,
    weights_s3_key TEXT,
    is_active      BOOLEAN NOT NULL DEFAULT FALSE,
    deployed_at    TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(name, version)
);

-- ── Drift monitoring ─────────────────────────────────────────
CREATE TABLE drift_reports (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name        VARCHAR(100) NOT NULL,
    drift_score       FLOAT NOT NULL,
    confidence_drift  FLOAT,
    accuracy_trend    FLOAT,
    alert_level       VARCHAR(20) CHECK (alert_level IN ('none','warning','critical')),
    recommendation    TEXT,
    retrain_triggered BOOLEAN NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_drift_model   ON drift_reports(model_name);
CREATE INDEX idx_drift_created ON drift_reports(created_at DESC);

-- ── Auto-update timestamps trigger ───────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ── Seed: default org + super admin ──────────────────────────
INSERT INTO organizations (id, name, slug, plan, monthly_quota, api_tier)
VALUES ('00000000-0000-0000-0000-000000000001',
        'DeepShield Internal', 'deepshield', 'enterprise', 9999999, 'enterprise');

INSERT INTO users (org_id, email, password_hash, full_name, role)
VALUES ('00000000-0000-0000-0000-000000000001',
        'admin@deepshield.ai',
        crypt('ChangeMe@2024!', gen_salt('bf')),
        'System Administrator', 'super_admin');
