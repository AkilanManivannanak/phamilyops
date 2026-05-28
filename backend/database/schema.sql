-- ============================================================
-- PhamilyOps — Complete Supabase Schema
-- Run this entire file in Supabase SQL Editor
-- ============================================================

-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- CANDIDATES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS candidates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    name TEXT NOT NULL,
    email TEXT,
    role TEXT NOT NULL,
    resume_text TEXT,
    resume_filename TEXT,
    overall_score INTEGER DEFAULT 0,
    skill_alignment NUMERIC(5,2) DEFAULT 0,
    culture_fit TEXT DEFAULT 'Unknown',
    status TEXT DEFAULT 'applied' CHECK (status IN ('applied','screened','interview','offered','hired','rejected')),
    source TEXT DEFAULT 'direct' CHECK (source IN ('linkedin','referral','jobboard','university','direct')),
    skills JSONB DEFAULT '[]',
    screening_questions JSONB DEFAULT '[]',
    outreach_email TEXT,
    pii_redacted BOOLEAN DEFAULT FALSE,
    bias_checked BOOLEAN DEFAULT FALSE,
    notes TEXT
);

-- ============================================================
-- HR POLICY DOCUMENTS TABLE (for copilot knowledge base)
-- ============================================================
CREATE TABLE IF NOT EXISTS hr_documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    title TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('pto','benefits','onboarding','culture','compensation','legal','ops')),
    content TEXT NOT NULL,
    embedding vector(384),  -- sentence-transformers all-MiniLM-L6-v2 dimension
    is_active BOOLEAN DEFAULT TRUE
);

-- ============================================================
-- CHAT HISTORY TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user','assistant')),
    message TEXT NOT NULL,
    retrieved_doc_ids JSONB DEFAULT '[]',
    faithfulness_score NUMERIC(4,3),
    response_time_ms INTEGER
);

-- ============================================================
-- WORKFLOW AUDIT TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS workflow_audits (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    process_name TEXT NOT NULL,
    frequency_per_week INTEGER DEFAULT 1,
    avg_hours NUMERIC(5,2) DEFAULT 1,
    error_rate_pct INTEGER DEFAULT 10,
    automation_score INTEGER DEFAULT 0,
    roi_annual NUMERIC(10,2) DEFAULT 0,
    priority_rank INTEGER DEFAULT 0,
    status TEXT DEFAULT 'identified' CHECK (status IN ('identified','in_progress','completed'))
);

-- ============================================================
-- AUTOMATION RUNS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS automation_runs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    workflow_name TEXT NOT NULL,
    trigger_event TEXT,
    status TEXT DEFAULT 'running' CHECK (status IN ('running','completed','failed')),
    time_saved_minutes INTEGER DEFAULT 0,
    details JSONB DEFAULT '{}'
);

-- ============================================================
-- ANALYTICS SNAPSHOTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_snapshots (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    snapshot_date DATE DEFAULT CURRENT_DATE,
    total_candidates INTEGER DEFAULT 0,
    screened INTEGER DEFAULT 0,
    interviewed INTEGER DEFAULT 0,
    offered INTEGER DEFAULT 0,
    hired INTEGER DEFAULT 0,
    avg_time_to_hire_days NUMERIC(5,2) DEFAULT 0,
    hours_saved NUMERIC(8,2) DEFAULT 0,
    copilot_queries INTEGER DEFAULT 0
);

-- ============================================================
-- RAGAS EVALUATIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS ragas_evaluations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    chat_session_id TEXT,
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    faithfulness NUMERIC(4,3),
    answer_recall NUMERIC(4,3),
    context_precision NUMERIC(4,3),
    f1_score NUMERIC(4,3)
);

-- ============================================================
-- INDEXES for performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);
CREATE INDEX IF NOT EXISTS idx_candidates_role ON candidates(role);
CREATE INDEX IF NOT EXISTS idx_candidates_score ON candidates(overall_score DESC);
CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id);
CREATE INDEX IF NOT EXISTS idx_hr_docs_category ON hr_documents(category);
CREATE INDEX IF NOT EXISTS idx_hr_docs_active ON hr_documents(is_active);
CREATE INDEX IF NOT EXISTS idx_automation_runs_created ON automation_runs(created_at DESC);

-- pgvector index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_hr_docs_embedding ON hr_documents
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE hr_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE automation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE ragas_evaluations ENABLE ROW LEVEL SECURITY;

-- Service role has full access (backend uses service role key)
CREATE POLICY "service_role_all" ON candidates FOR ALL USING (true);
CREATE POLICY "service_role_all" ON hr_documents FOR ALL USING (true);
CREATE POLICY "service_role_all" ON chat_history FOR ALL USING (true);
CREATE POLICY "service_role_all" ON workflow_audits FOR ALL USING (true);
CREATE POLICY "service_role_all" ON automation_runs FOR ALL USING (true);
CREATE POLICY "service_role_all" ON analytics_snapshots FOR ALL USING (true);
CREATE POLICY "service_role_all" ON ragas_evaluations FOR ALL USING (true);

-- ============================================================
-- SEED HR POLICY DOCUMENTS (Phamily-specific content)
-- ============================================================
INSERT INTO hr_documents (title, category, content) VALUES
(
    'Phamily PTO Policy',
    'pto',
    'Phamily offers up to 35 paid days off per year for full-time employees. This includes: 12 vacation days accrued annually for rest, travel, and personal time. Up to 9 sick and wellness days to prioritize health and wellbeing. 12 paid company holidays throughout the year. 2 paid give-back days for community service. For summer interns, PTO is prorated based on internship duration (June 15 to August 14). PTO requests must be submitted at least 5 business days in advance through the HRIS system. Unused PTO does not roll over at year end.'
),
(
    'Phamily Benefits Package',
    'benefits',
    'Phamily provides comprehensive benefits including: Medical, dental, and vision coverage for employees and dependents at low cost. HSA and FSA account options for healthcare savings. 401(k) retirement plan with company match after 6 months of full-time employment — 100% match on first 3% contributed, 50% match on the next 2% contributed. The internship program does not include 401(k) or full benefits but does include access to the collaborative, mission-driven team environment.'
),
(
    'Phamily Five Core Principles',
    'culture',
    'Phamily culture is built on five principles: Care — We put patients, clients, teammates, and outcomes first in everything we do. Curiosity — We ask better questions, challenge assumptions, and keep learning continuously. Clarity — We simplify complexity, communicate directly, and create alignment across teams. Co-Creation — We collaborate across teams, perspectives, and disciplines to build better solutions. Craftsmanship — We execute with excellence, ownership, and continuous improvement. Every employee and intern is expected to embody these principles daily.'
),
(
    'Intern Onboarding Process',
    'onboarding',
    'Phamily intern onboarding follows this process: Pre-Day 1 — Sign offer letter and NDA, complete I-9 verification, receive equipment, get Slack and Gmail access, join Phamily workspace channels. Day 1 — Meet with HR Operations Manager, attend orientation covering mission and culture, complete access setup for HRIS, ATS, Google Drive, and review the five Phamily principles. Week 1 — Shadow HR team workflows, complete first workflow audit of 2-3 processes, define intern project scope and success metrics with manager. The intern project should produce measurable impact including hours saved, processes shortened, or quality improved, to be presented to company leadership at the end of the internship.'
),
(
    'Compensation and Salary Policy',
    'compensation',
    'Phamily intern compensation ranges from $25 to $35 per hour depending on experience and impact. The HR AI Automation Intern role is based in New York City, 5 days per week in office, running from June 15 to August 14, 2026. The AI Native Process Automation Intern role is based in New York City or Chicago, also full-time in office for the summer. Compensation is paid bi-weekly. Interns are expected to work standard business hours with flexibility as needed in a high-growth environment.'
),
(
    'Performance Improvement Plan Guidelines',
    'legal',
    'A Performance Improvement Plan at Phamily follows this structure: Identification of specific measurable behaviors needing improvement. Clear action plan with concrete steps and realistic timelines. 30, 60, and 90 day review checkpoints with HR and direct manager. Quantifiable success metrics agreed upon at the start. Documentation must be reviewed by legal before delivery to employee. The PIP is a supportive tool designed for growth, aligned with Phamily values of Care and Craftsmanship. HR Copilot can draft PIP templates but all PIPs must be reviewed by the HR Operations Manager before use.'
);

-- ============================================================
-- SEED INITIAL ANALYTICS SNAPSHOT
-- ============================================================
INSERT INTO analytics_snapshots (
    snapshot_date, total_candidates, screened, interviewed,
    offered, hired, avg_time_to_hire_days, hours_saved, copilot_queries
) VALUES (CURRENT_DATE, 247, 89, 34, 12, 9, 7.4, 142, 1847);

-- Done
SELECT 'PhamilyOps schema installed successfully' AS status;
