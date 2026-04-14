-- Enable RLS on all tables
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE completions ENABLE ROW LEVEL SECURITY;

-- Categories policies
CREATE POLICY "Users can view own categories"
    ON categories FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own categories"
    ON categories FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own categories"
    ON categories FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own categories"
    ON categories FOR DELETE USING (auth.uid() = user_id);

-- Items policies
CREATE POLICY "Users can view own items"
    ON items FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own items"
    ON items FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own items"
    ON items FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own items"
    ON items FOR DELETE USING (auth.uid() = user_id);

-- Completions policies
CREATE POLICY "Users can view own completions"
    ON completions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own completions"
    ON completions FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own completions"
    ON completions FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own completions"
    ON completions FOR DELETE USING (auth.uid() = user_id);
