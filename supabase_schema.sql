-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Searches table to track overall search processes
CREATE TABLE searches (
search_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
position VARCHAR(255) NOT NULL,
experience_level VARCHAR(50) NOT NULL,
status VARCHAR(50) NOT NULL DEFAULT 'CREATED',
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
results JSONB DEFAULT '{}'::jsonb
);

-- Events table for detailed tracking of the entire process
CREATE TABLE events (
event_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
search_id UUID REFERENCES searches(search_id) ON DELETE CASCADE,
agent_type VARCHAR(50) NOT NULL, -- 'SEARCHER', 'SCRAPER', 'TAILOR'
event_type VARCHAR(50) NOT NULL, -- 'INFO', 'ERROR', 'SUCCESS'
details JSONB NOT NULL,
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster event retrieval
CREATE INDEX idx_events_search_id ON events(search_id);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
NEW.updated_at = CURRENT_TIMESTAMP;
RETURN NEW;
END;
$$ language 'plpgsql';


CREATE TRIGGER update_searches_updated_at
BEFORE UPDATE ON searches
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Add RLS policies
ALTER TABLE searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;


-- Create policies (adjust according to your auth setup)
CREATE POLICY "Enable read access for all users" ON searches
FOR SELECT
USING (true);

CREATE POLICY "Enable read access for all users" ON events
FOR SELECT
USING (true);

  
-- Create table called jobs
CREATE TABLE jobs (
job_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
search_id UUID REFERENCES searches(search_id),
title VARCHAR(255) NOT NULL,
company VARCHAR(255) NOT NULL,
link TEXT NOT NULL,
posted_date VARCHAR(100),
description TEXT,
tailored_resume JSONB,
status VARCHAR(50) DEFAULT 'discovered',
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create table called applications
CREATE TABLE applications (
application_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
job_id UUID REFERENCES jobs(job_id),
search_id UUID REFERENCES searches(search_id),
status VARCHAR(50) NOT NULL, -- 'tailored', 'submitted', 'failed'
tailored_resume JSONB,
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Create a view for easier querying of search status with events
CREATE VIEW search_status AS
SELECT
s.search_id,
s.position,
s.experience_level,
s.status,
s.created_at,
s.updated_at,
COUNT(e.event_id) as event_count,
jsonb_agg(e.details ORDER BY e.created_at) as event_history
FROM searches s
LEFT JOIN events e ON s.search_id = e.search_id
GROUP BY s.search_id, s.position, s.experience_level, s.status, s.created_at, s.updated_at;  