-- ============================================================
-- PhamilyOps — pgvector Similarity Search Function
-- Run this in Supabase SQL Editor AFTER schema.sql
-- ============================================================

CREATE OR REPLACE FUNCTION match_hr_documents(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.3,
    match_count int DEFAULT 3
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    category TEXT,
    content TEXT,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        hr_documents.id,
        hr_documents.title,
        hr_documents.category,
        hr_documents.content,
        1 - (hr_documents.embedding <=> query_embedding) AS similarity
    FROM hr_documents
    WHERE
        hr_documents.is_active = TRUE
        AND 1 - (hr_documents.embedding <=> query_embedding) > match_threshold
    ORDER BY hr_documents.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Verify it works
SELECT 'pgvector match function created successfully' AS status;
