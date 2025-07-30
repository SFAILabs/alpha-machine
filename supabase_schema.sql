-- Alpha Machine Supabase Database Schema
-- This file contains the SQL schema for storing filtered transcripts and related data

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- FILTERED TRANSCRIPTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS filtered_transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Original file information
    original_filename TEXT NOT NULL,
    original_length INTEGER NOT NULL,
    
    -- Filtered content
    filtered_content TEXT NOT NULL,
    filtered_length INTEGER NOT NULL,
    redaction_count INTEGER NOT NULL DEFAULT 0,
    
    -- Meeting metadata
    meeting_date TIMESTAMP WITH TIME ZONE,
    participants TEXT[] DEFAULT '{}',
    project_tags TEXT[] DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_filtered_transcripts_meeting_date 
    ON filtered_transcripts(meeting_date);

CREATE INDEX IF NOT EXISTS idx_filtered_transcripts_project_tags 
    ON filtered_transcripts USING GIN(project_tags);

CREATE INDEX IF NOT EXISTS idx_filtered_transcripts_participants 
    ON filtered_transcripts USING GIN(participants);

CREATE INDEX IF NOT EXISTS idx_filtered_transcripts_created_at 
    ON filtered_transcripts(created_at);

-- ============================================================================
-- ORIGINAL TRANSCRIPTS TABLE (for backup/reference)
-- ============================================================================

CREATE TABLE IF NOT EXISTS original_transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filtered_transcript_id UUID REFERENCES filtered_transcripts(id) ON DELETE CASCADE,
    
    -- Original content
    original_content TEXT NOT NULL,
    original_length INTEGER NOT NULL,
    
    -- File metadata
    filename TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_original_transcripts_filtered_id 
    ON original_transcripts(filtered_transcript_id);

-- ============================================================================
-- MEETING SUMMARIES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS meeting_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transcript_id UUID REFERENCES filtered_transcripts(id) ON DELETE CASCADE,
    
    -- Summary content
    summary_title TEXT NOT NULL,
    summary_content TEXT NOT NULL,
    key_points TEXT[] DEFAULT '{}',
    action_items TEXT[] DEFAULT '{}',
    
    -- Meeting metadata
    meeting_type TEXT,
    duration_minutes INTEGER,
    attendees_count INTEGER,
    
    -- AI processing metadata
    ai_model_used TEXT,
    processing_time_seconds DECIMAL(10,2),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_meeting_summaries_transcript_id 
    ON meeting_summaries(transcript_id);

CREATE INDEX IF NOT EXISTS idx_meeting_summaries_meeting_type 
    ON meeting_summaries(meeting_type);

-- ============================================================================
-- CLIENT STATUS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS client_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Client information
    client_name TEXT NOT NULL UNIQUE,
    client_email TEXT,
    client_phone TEXT,
    
    -- Project status
    current_projects TEXT[] DEFAULT '{}',
    active_issues INTEGER DEFAULT 0,
    completed_issues INTEGER DEFAULT 0,
    
    -- Timeline information
    next_milestone TEXT,
    next_milestone_date DATE,
    overall_deadline DATE,
    
    -- Status tracking
    status TEXT DEFAULT 'active', -- active, paused, completed, archived
    priority TEXT DEFAULT 'medium', -- low, medium, high, urgent
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_client_status_name 
    ON client_status(client_name);

CREATE INDEX IF NOT EXISTS idx_client_status_status 
    ON client_status(status);

CREATE INDEX IF NOT EXISTS idx_client_status_priority 
    ON client_status(priority);

-- ============================================================================
-- PROCESSING LOGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS processing_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transcript_id UUID REFERENCES filtered_transcripts(id) ON DELETE CASCADE,
    
    -- Processing information
    operation_type TEXT NOT NULL, -- filter, summarize, analyze, etc.
    status TEXT NOT NULL, -- success, failed, in_progress
    
    -- Performance metrics
    processing_time_seconds DECIMAL(10,2),
    tokens_used INTEGER,
    ai_model_used TEXT,
    
    -- Error information
    error_message TEXT,
    error_details JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_processing_logs_transcript_id 
    ON processing_logs(transcript_id);

CREATE INDEX IF NOT EXISTS idx_processing_logs_operation_type 
    ON processing_logs(operation_type);

CREATE INDEX IF NOT EXISTS idx_processing_logs_status 
    ON processing_logs(status);

CREATE INDEX IF NOT EXISTS idx_processing_logs_created_at 
    ON processing_logs(created_at);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE filtered_transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE original_transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE meeting_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_logs ENABLE ROW LEVEL SECURITY;

-- Create policies for authenticated users
-- Note: These are basic policies - adjust based on your authentication setup

-- Filtered transcripts: Allow read/write for authenticated users
CREATE POLICY "Allow authenticated users to manage filtered transcripts"
    ON filtered_transcripts
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Original transcripts: Allow read/write for authenticated users
CREATE POLICY "Allow authenticated users to manage original transcripts"
    ON original_transcripts
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Meeting summaries: Allow read/write for authenticated users
CREATE POLICY "Allow authenticated users to manage meeting summaries"
    ON meeting_summaries
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Client status: Allow read/write for authenticated users
CREATE POLICY "Allow authenticated users to manage client status"
    ON client_status
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Processing logs: Allow read/write for authenticated users
CREATE POLICY "Allow authenticated users to manage processing logs"
    ON processing_logs
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_filtered_transcripts_updated_at 
    BEFORE UPDATE ON filtered_transcripts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_original_transcripts_updated_at 
    BEFORE UPDATE ON original_transcripts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_meeting_summaries_updated_at 
    BEFORE UPDATE ON meeting_summaries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_client_status_updated_at 
    BEFORE UPDATE ON client_status 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SAMPLE DATA INSERTS (for testing)
-- ============================================================================

-- Insert sample filtered transcript
INSERT INTO filtered_transcripts (
    original_filename,
    original_length,
    filtered_content,
    filtered_length,
    redaction_count,
    meeting_date,
    participants,
    project_tags
) VALUES (
    'sample_meeting.txt',
    1500,
    'nash@sfaiconsultants.com | 00:00\nLet''s discuss the technical requirements for the chatbot project.\n\ndirkjan@sfai.com | 00:03\nWe need to implement proactive conversation guidance and dual reviewer agents.\n\nnash@sfaiconsultants.com | 00:07\nPerfect. Let''s assign Jonathan to work on the AI model development.',
    300,
    0,
    NOW(),
    ARRAY['nash@sfaiconsultants.com', 'dirkjan@sfai.com'],
    ARRAY['Alpha Machine', 'Chatbot Project']
) ON CONFLICT DO NOTHING;

-- Insert sample client status
INSERT INTO client_status (
    client_name,
    client_email,
    current_projects,
    active_issues,
    completed_issues,
    status,
    priority
) VALUES (
    'Sample Client',
    'client@example.com',
    ARRAY['Alpha Machine', 'Chatbot Project'],
    5,
    12,
    'active',
    'high'
) ON CONFLICT DO NOTHING;

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View for transcript statistics
CREATE OR REPLACE VIEW transcript_stats AS
SELECT 
    COUNT(*) as total_transcripts,
    AVG(original_length) as avg_original_length,
    AVG(filtered_length) as avg_filtered_length,
    AVG(redaction_count) as avg_redactions,
    MIN(created_at) as earliest_transcript,
    MAX(created_at) as latest_transcript
FROM filtered_transcripts;

-- View for project activity
CREATE OR REPLACE VIEW project_activity AS
SELECT 
    unnest(project_tags) as project_name,
    COUNT(*) as transcript_count,
    AVG(redaction_count) as avg_redactions,
    MAX(meeting_date) as last_meeting
FROM filtered_transcripts
GROUP BY project_name
ORDER BY transcript_count DESC;

-- View for participant activity
CREATE OR REPLACE VIEW participant_activity AS
SELECT 
    unnest(participants) as participant,
    COUNT(*) as meeting_count,
    MAX(meeting_date) as last_meeting
FROM filtered_transcripts
GROUP BY participant
ORDER BY meeting_count DESC;

-- ============================================================================
-- CHAT SESSIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    previous_response_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for chat sessions
CREATE INDEX IF NOT EXISTS idx_chat_sessions_session_id 
    ON chat_sessions(session_id);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id 
    ON chat_sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_channel_id 
    ON chat_sessions(channel_id);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at 
    ON chat_sessions(updated_at);

-- Enable RLS on chat sessions
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;

-- Create policy for chat sessions
CREATE POLICY "Allow authenticated users to manage chat sessions"
    ON chat_sessions
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Create trigger for updated_at
CREATE TRIGGER update_chat_sessions_updated_at 
    BEFORE UPDATE ON chat_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE filtered_transcripts IS 'Stores AI-filtered meeting transcripts with commercial/monetary content removed';
COMMENT ON TABLE original_transcripts IS 'Stores original unfiltered transcripts for backup and reference';
COMMENT ON TABLE meeting_summaries IS 'Stores AI-generated meeting summaries and key points';
COMMENT ON TABLE client_status IS 'Tracks client project status and timelines';
COMMENT ON TABLE processing_logs IS 'Logs AI processing operations and performance metrics';
COMMENT ON TABLE chat_sessions IS 'Stores chat session data for OpenAI Responses API conversation history';

COMMENT ON COLUMN filtered_transcripts.redaction_count IS 'Number of commercial/monetary content redactions made by AI';
COMMENT ON COLUMN filtered_transcripts.project_tags IS 'Array of project names mentioned in the transcript';
COMMENT ON COLUMN filtered_transcripts.participants IS 'Array of participant email addresses or names';
COMMENT ON COLUMN chat_sessions.previous_response_id IS 'OpenAI response ID for conversation history management'; 