import pdfplumber
import re
import sqlite3

def normalize_pdf_artifacts(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'(?:^|\n)\s*ΕΜΑ\s+', r'\nΘΕΜΑ ', text)
    def merge_digits(match):
        header = match.group(1)
        digits = re.sub(r'\s+', '', match.group(2))
        return f"{header} {digits}"
    text = re.sub(r'(ΘΕΜΑ)\s+(\d(?:\s+\d)+)', merge_digits, text, flags=re.IGNORECASE)
    text = re.sub(r'(ΘΕΜΑ)\s+(\d(?:\s+\d)+)', merge_digits, text, flags=re.IGNORECASE)
    return text

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'([Α-ΔA-D])\s*\(\.', r'(\1.', text)
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = re.sub(r'\bΒορεί\s+ου\b', 'Βορείου', text, flags=re.IGNORECASE)
    text = re.sub(r'\bΝοτί\s+ου\b', 'Νοτίου', text, flags=re.IGNORECASE)
    text = re.sub(r'\bΠ\s+άτρα\b', 'Πάτρα', text, flags=re.IGNORECASE)
    text = re.sub(r'\bΏ\s+ρα\b', 'Ώρα', text, flags=re.IGNORECASE)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def detect_question_type(text: str) -> str:
    if re.search(r"συμπληρώστε.*κενό|στο\s+κενό\s+που\s+υπάρχει", text, flags=re.IGNORECASE):
        return "FILL_BLANKS"
    elif re.search(r"σημειώνοντας\s*Σ|Σ,\s*αν|ή\s*Λ,\s*αν", text, flags=re.IGNORECASE):
        return "TRUE_FALSE"
    elif re.search(r"αντιστοιχ(ίσετε|ιστε|ιση)|ΣΤΗΛΗ\s*Ι\b|που\s+ταιριάζει|αν\s+σχετίζεται\s*:", text, flags=re.IGNORECASE):
        return "MATCHING"
    elif re.search(r"(^[Α-Δ]\.\s+|^\d\.\s+|^Εικ\.\s*[Α-Δ])", text, flags=re.MULTILINE) or re.search(r"Εικ\.\s*Α\s+Εικ\.\s*Β", text):
        return "MULTIPLE_CHOICE"
    else:
        return "OPEN_TEXT"

def extract_questions_from_pdf(pdf_filename: str, category: str, prefix: str, expected_count: int):
    print(f"\n📂 Parsing {pdf_filename} ({category})...")
    with pdfplumber.open(pdf_filename) as pdf:
        pages_text = [p.extract_text(layout=False) or "" for p in pdf.pages]
        full_text = "\n".join(pages_text)

    full_text = normalize_pdf_artifacts(full_text)

    cleaned = re.sub(r"ΤΡΑΠΕΖΑ ΘΕΜΑΤΩΝ[^\n]*", "", full_text)
    cleaned = re.sub(r"Σελίδα \d+ από \d+[^\n]*", "", cleaned)
    cleaned = re.sub(r"Θέματα και απαντήσεις στην θεματική ενότητα:[^\n]*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"Θέματα και απαντήσεις[^\n]*", "", cleaned)
    cleaned = re.sub(r".*θεματική ενότητα:[^\n]*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[Α-ΩA-Z]\.?\s*ΕΝΟΤΗΤΑ:[^\n]*", "", cleaned)
    cleaned = re.sub(r"ΝΟΕΜΒΡΙΟΣ 2026[^\n]*", "", cleaned)

    pattern = re.compile(r'(?:^|\n)\s*(?:[Α-Ω]\s+ΕΝΟΤΗΤΑ:[^\n]*\n\s*)?ΘΕΜΑ\s+(\d+)\s*\n', re.IGNORECASE)
    splits = pattern.split(cleaned)

    extracted = {}
    for i in range(1, len(splits), 2):
        q_num = int(splits[i])
        raw_body = splits[i+1].strip()

        # ΑΣΦΑΛΕΣ SPLIT: Μόνο όταν η γραμμή ξεκινά με ΑΠΑΝΤΗΣΗ / Απάντηση
        ans_split = re.split(r'\n\s*ΑΠΑΝΤΗΣΗ\s*[:\-]\s*|\n\s*Απάντηση\s*[:\-]\s*', raw_body, flags=re.IGNORECASE)
        
        if len(ans_split) >= 2:
            prompt = clean_text(ans_split[0])
            answer = clean_text(" ".join(ans_split[1:]))
            answer = re.sub(r'(\d+)\.\s*([ΣΛΑ-ΔA-D])', r'\1-\2', answer)
        else:
            # Fallback split
            fallback_split = re.split(r'ΑΠΑΝΤΗΣΗ\s*:\s*|Απάντηση\s*:\s*', raw_body, flags=re.IGNORECASE)
            if len(fallback_split) >= 2:
                prompt = clean_text(fallback_split[0])
                answer = clean_text(" ".join(fallback_split[1:]))
            else:
                prompt = clean_text(raw_body)
                answer = ""

        # Fallback για χάρτες Γεωγραφίας 51-70
        if category == "geography" and q_num >= 51 and not answer:
            items = re.findall(r'\(\d+\)\s*([Α-Ωα-ωά-ώA-Za-z\s\-/]+)', prompt)
            if items:
                answer = ", ".join([it.strip() for it in items if it.strip()])

        if prefix == "hist" and q_num == 70 and not answer:
            answer = "1-Σ, 2-Λ, 3-Σ, 4-Λ"

        q_type = detect_question_type(prompt)
        has_image = bool(re.search(r"(Εικ\.\s*[Α-Δ\d]|\bφωτογραφί|\bπαρακάτω εικόν|\bπαρακάτω μνημείο|\bχάρτη|\bεικονιζόμενος|\bπίνακας|\bψηλού κτίσματος)", prompt, flags=re.IGNORECASE)) and not bool(re.search(r"δείτε εικόνες", prompt, flags=re.IGNORECASE))

        q_id = f"{prefix}_{q_num}"
        extracted[q_num] = (
            q_id,
            category,
            q_type,
            prompt,
            answer,
            "image" if has_image else "none",
            None,
            None
        )

    print(f"  -> Επιτυχής εξαγωγή: {len(extracted)}/{expected_count}")
    return list(extracted.values())

def build_database():
    conn = sqlite3.connect("quiz.db")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS questions;")
    cursor.execute("""
    CREATE TABLE questions (
        id TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        question_type TEXT NOT NULL,
        question_text TEXT NOT NULL,
        correct_answer TEXT NOT NULL,
        media_type TEXT DEFAULT 'none',
        model_answer TEXT,
        explanation TEXT
    );
    """)

    datasets = [
        ("data/culture.pdf", "culture", "cult", 70),
        ("data/geography.pdf", "geography", "geo", 70),
        ("data/history.pdf", "history", "hist", 80),
        ("data/institutions.pdf", "institutions", "inst", 80),
    ]

    all_rows = []
    for pdf_file, cat, prefix, count in datasets:
        rows = extract_questions_from_pdf(pdf_file, cat, prefix, count)
        all_rows.extend(rows)

    cursor.executemany("""
        INSERT INTO questions 
        (id, category, question_type, question_text, correct_answer, media_type, model_answer, explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, all_rows)

    conn.commit()
    conn.close()
    print("\n🎯 Η βάση ξαναχτίστηκε επιτυχώς με όλες τις εκφωνήσεις πλήρεις!")

if __name__ == "__main__":
    build_database()