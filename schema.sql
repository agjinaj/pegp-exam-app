CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    question_type TEXT NOT NULL,
    question_text TEXT NOT NULL,
    correct_answer TEXT,
    media_type TEXT DEFAULT 'none', 
    model_answer TEXT,
    explanation TEXT

);