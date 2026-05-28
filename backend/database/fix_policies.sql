-- ============================================================
-- PhamilyOps — Policy Fix
-- Run this in Supabase SQL Editor if you get "policy already exists"
-- ============================================================

-- Drop existing policies first
DROP POLICY IF EXISTS "service_role_all" ON candidates;
DROP POLICY IF EXISTS "service_role_all" ON hr_documents;
DROP POLICY IF EXISTS "service_role_all" ON chat_history;
DROP POLICY IF EXISTS "service_role_all" ON workflow_audits;
DROP POLICY IF EXISTS "service_role_all" ON automation_runs;
DROP POLICY IF EXISTS "service_role_all" ON analytics_snapshots;
DROP POLICY IF EXISTS "service_role_all" ON ragas_evaluations;

-- Recreate them cleanly
CREATE POLICY "service_role_all" ON candidates FOR ALL USING (true);
CREATE POLICY "service_role_all" ON hr_documents FOR ALL USING (true);
CREATE POLICY "service_role_all" ON chat_history FOR ALL USING (true);
CREATE POLICY "service_role_all" ON workflow_audits FOR ALL USING (true);
CREATE POLICY "service_role_all" ON automation_runs FOR ALL USING (true);
CREATE POLICY "service_role_all" ON analytics_snapshots FOR ALL USING (true);
CREATE POLICY "service_role_all" ON ragas_evaluations FOR ALL USING (true);

-- Verify all tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
