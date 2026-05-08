-- Pace mode: per-category weekly time goal + time-tracking sessions.

ALTER TABLE categories
    ADD COLUMN weekly_hours_goal numeric NOT NULL DEFAULT 0
        CHECK (weekly_hours_goal >= 0);

CREATE TABLE time_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) NOT NULL,
    category_id uuid REFERENCES categories(id) ON DELETE CASCADE NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    ended_at timestamptz
);

CREATE INDEX idx_time_sessions_user_id ON time_sessions(user_id);
CREATE INDEX idx_time_sessions_category_id ON time_sessions(category_id);
CREATE INDEX idx_time_sessions_started_at ON time_sessions(started_at);
-- Quick lookup for any open session (ended_at IS NULL).
CREATE INDEX idx_time_sessions_open ON time_sessions(user_id) WHERE ended_at IS NULL;

ALTER TABLE time_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own sessions"
    ON time_sessions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own sessions"
    ON time_sessions FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own sessions"
    ON time_sessions FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own sessions"
    ON time_sessions FOR DELETE USING (auth.uid() = user_id);
