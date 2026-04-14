-- Categories
CREATE TABLE categories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) NOT NULL,
    title text NOT NULL,
    rank integer NOT NULL,
    UNIQUE (user_id, rank)
);

CREATE INDEX idx_categories_user_id ON categories(user_id);

-- Items
CREATE TABLE items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) NOT NULL,
    title text NOT NULL,
    notes text,
    category_id uuid REFERENCES categories(id),
    start_date date,
    due_date date,
    cadence_days integer,
    frequency_target integer,
    frequency_window_days integer,
    window_start time,
    window_end time,
    external_source text,
    external_data jsonb,
    priority_score float DEFAULT 0,
    defer_count integer DEFAULT 0,
    deferred_until timestamptz,
    created_at timestamptz DEFAULT now(),
    completed_at timestamptz,
    last_touched_at timestamptz,
    score_updated_at timestamptz,
    is_project boolean DEFAULT false
);

CREATE INDEX idx_items_user_id ON items(user_id);
CREATE INDEX idx_items_category_id ON items(category_id);
CREATE INDEX idx_items_completed_at ON items(completed_at);

-- Completions
CREATE TABLE completions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) NOT NULL,
    item_id uuid REFERENCES items(id) ON DELETE CASCADE,
    completed_at timestamptz DEFAULT now()
);

CREATE INDEX idx_completions_item_id ON completions(item_id);
CREATE INDEX idx_completions_user_id ON completions(user_id);
