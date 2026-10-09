import streamlit as st
import sqlite3
import re
import os
import random
import unicodedata
from difflib import SequenceMatcher

st.set_page_config(
    page_title="Εξετάσεις Π.Ε.Γ.Π.",
    page_icon="🏛️",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
        max-width: 720px;
    }
    .question-box {
        font-size: 1.05rem;
        line-height: 1.6;
        white-space: pre-wrap;
    }
    .table-container {
        margin: 15px 0;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    table.custom-table {
        width: 100%;
        border-collapse: collapse;
    }
    table.custom-table th, table.custom-table td {
        padding: 10px 14px;
        border: 1px solid rgba(128, 128, 128, 0.15);
        text-align: left;
    }
    table.custom-table th {
        background-color: rgba(128, 128, 128, 0.1);
        font-weight: 600;
    }
    button[kind="primary"] {
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

CATEGORY_NAMES = {
    "culture": "🏛️ Πολιτισμός",
    "geography": "🌍 Γεωγραφία",
    "history": "📜 Ιστορία",
    "institutions": "⚖️ Θεσμοί του Πολιτεύματος"
}

def clean_display_text(text: str) -> str:
    text = re.sub(r'\bΒορεί\s+ου\b', 'Βορείου', text, flags=re.IGNORECASE)
    text = re.sub(r'\bΝοτί\s+ου\b', 'Νοτίου', text, flags=re.IGNORECASE)
    text = re.sub(r'\bΑχιλλ\s+έα\b', 'Αχιλλέα', text, flags=re.IGNORECASE)
    text = re.sub(r'\bΠ\s+ραγματοποιήθηκε\b', 'Πραγματοποιήθηκε', text, flags=re.IGNORECASE)
    return text

def parse_and_render_matching(text: str):
    """Μετατρέπει καθαρά το κείμενο αντιστοίχισης σε HTML πίνακα."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    intro_lines = []
    pairs = []

    for line in lines:
        m = re.match(r"^(\d+[\.\)])\s*(.*?)\s+([Α-ΔA-D][\.\)])\s*(.*)", line)
        if m:
            c1 = f"{m.group(1)} {m.group(2).strip()}"
            c2 = f"{m.group(3)} {m.group(4).strip()}"
            pairs.append((c1, c2))
        else:
            if not pairs and not re.search(r"ΣΤΗΛΗ\s*Ι", line, flags=re.IGNORECASE):
                intro_lines.append(line)

    if len(pairs) >= 3:
        intro_text = " ".join(intro_lines)
        html = f"<div class='question-box'>{intro_text}</div>"
        html += """
        <div class="table-container">
            <table class="custom-table">
                <thead>
                    <tr><th>Στήλη Ι</th><th>Στήλη ΙΙ</th></tr>
                </thead>
                <tbody>
        """
        for c1, c2 in pairs:
            html += f"<tr><td>{c1}</td><td>{c2}</td></tr>"
        html += "</tbody></table></div>"
        return html
    return None

def process_multiple_choice_shuffle(raw_text: str, correct_ans: str):
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    prompt_lines = []
    options_dict = {}

    for l in lines:
        m = re.match(r"^([Α-ΔA-D])[\.\)]\s*(.*)", l)
        if m:
            letter = m.group(1).upper()
            letter = {'A': 'Α', 'B': 'Β', 'C': 'Γ', 'D': 'Δ'}.get(letter, letter)
            options_dict[letter] = m.group(2).strip()
        else:
            if not options_dict:
                prompt_lines.append(l)
            else:
                prompt_lines.append(l)

    if len(options_dict) >= 3:
        orig_target = correct_ans.strip().upper()
        orig_target = {'A': 'Α', 'B': 'Β', 'C': 'Γ', 'D': 'Δ'}.get(orig_target, orig_target)
        correct_text = options_dict.get(orig_target, "")

        items = list(options_dict.values())
        random.shuffle(items)

        new_labels = ["Α", "Β", "Γ", "Δ"][:len(items)]
        new_correct_letter = orig_target
        reconstructed_lines = []

        for lbl, txt in zip(new_labels, items):
            reconstructed_lines.append(f"{lbl}. {txt}")
            if txt == correct_text:
                new_correct_letter = lbl

        new_prompt = "\n".join(prompt_lines) + "\n" + "\n".join(reconstructed_lines)
        return new_prompt, new_correct_letter

    return raw_text, correct_ans

def latin_to_greek(text: str) -> str:
    mapping = {'A': 'Α', 'B': 'Β', 'C': 'Γ', 'G': 'Γ', 'D': 'Δ', 'S': 'Σ', 'L': 'Λ', 'E': 'Ε', 'T': 'Τ', 'N': 'Ν'}
    return "".join(mapping.get(c, c) for c in text.upper())

def remove_greek_accents(text: str) -> str:
    normalized = unicodedata.normalize('NFKD', text)
    without_accents = "".join([c for c in normalized if not unicodedata.combining(c)])
    return latin_to_greek(without_accents.strip().upper())

def is_word_similar(user_word: str, real_word: str, tolerance: float = 0.75) -> bool:
    clean_user = remove_greek_accents(user_word)
    clean_real = remove_greek_accents(real_word)
    return SequenceMatcher(None, clean_user, clean_real).ratio() >= tolerance

def check_answer(user_input: str, correct_answer: str, question_type: str) -> bool:
    if not user_input.strip():
        return False
    clean_user = remove_greek_accents(user_input)
    clean_target = remove_greek_accents(correct_answer)

    if question_type == "MULTIPLE_CHOICE":
        choice_letter = clean_user[0] if clean_user else ""
        target_letter = clean_target[0] if clean_target else ""
        return choice_letter == target_letter
    elif question_type in ("MATCHING", "TRUE_FALSE", "FILL_BLANKS"):
        user_symbols = re.sub(r'[^A-ZΑ-Ω0-9]', '', clean_user)
        target_symbols = re.sub(r'[^A-ZΑ-Ω0-9]', '', clean_target)
        return user_symbols == target_symbols
    elif question_type == "OPEN_TEXT":
        accepted = re.findall(r'[Α-Ωα-ωά-ώ]+', correct_answer)
        user_words = re.findall(r'[Α-Ωα-ωά-ώa-zA-Z]+', user_input)
        if not accepted:
            return True
        matches = sum(1 for u in user_words if any(is_word_similar(u, acc) for acc in accepted))
        return matches >= min(len(accepted), 2)
    return False

def fetch_questions(mode="category", category="culture", limit=5):
    db = sqlite3.connect("quiz.db")
    cursor = db.cursor()
    raw_rows = []
    if mode == "category":
        cursor.execute("""
            SELECT id, category, question_type, question_text, correct_answer, media_type
            FROM questions
            WHERE category = ?
            ORDER BY RANDOM()
            LIMIT ?
        """, (category, limit))
        raw_rows = cursor.fetchall()
    else:
        quotas = [("history", 6), ("institutions", 6), ("geography", 4), ("culture", 4)]
        for cat, q_limit in quotas:
            cursor.execute("""
                SELECT id, category, question_type, question_text, correct_answer, media_type
                FROM questions
                WHERE category = ?
                ORDER BY RANDOM()
                LIMIT ?
            """, (cat, q_limit))
            raw_rows.extend(cursor.fetchall())
        random.shuffle(raw_rows)
    db.close()

    processed = []
    for q_id, cat, q_type, q_text, c_ans, media in raw_rows:
        q_text = clean_display_text(q_text)
        if q_type == "MULTIPLE_CHOICE":
            q_text, c_ans = process_multiple_choice_shuffle(q_text, c_ans)
        processed.append((q_id, cat, q_type, q_text, c_ans, media))
    return processed

with st.sidebar:
    st.header("⚙️ Ρυθμίσεις")
    quiz_mode = st.radio(
        "Τρόπος Εξάσκησης:",
        options=["Θεματική Ενότητα", "Προσομοίωση Εξετάσεων (Mock Exam)"]
    )
    selected_category = "culture"
    num_questions = 5
    if quiz_mode == "Θεματική Ενότητα":
        cat_display = st.selectbox("Ενότητα:", options=list(CATEGORY_NAMES.values()))
        selected_category = [k for k, v in CATEGORY_NAMES.items() if v == cat_display][0]
        num_questions = st.select_slider("Πλήθος ερωτήσεων:", options=[5, 10, 15, 20], value=5)
    else:
        st.info("📋 **Επίσημη Δομή Εξετάσεων (20 θέματα):**\n- 📜 Ιστορία: 6\n- ⚖️ Θεσμοί: 6\n- 🌍 Γεωγραφία: 4\n- 🏛️ Πολιτισμός: 4")

    if st.button("🔄 Νέο Τεστ / Reset", use_container_width=True):
        mode_val = "mock" if quiz_mode == "Προσομοίωση Εξετάσεων (Mock Exam)" else "category"
        st.session_state.questions = fetch_questions(mode_val, selected_category, num_questions)
        st.session_state.current_idx = 0
        st.session_state.score = 0
        st.session_state.completed = False
        st.session_state.user_answers = {}
        st.rerun()

if "questions" not in st.session_state:
    st.session_state.questions = fetch_questions("category", "culture", 5)
    st.session_state.current_idx = 0
    st.session_state.score = 0
    st.session_state.completed = False
    st.session_state.user_answers = {}

st.markdown("### 🏛️ Εξετάσεις του Πιστοποιητικού Επάρκειας Γνώσεων για Πολιτογράφηση (Π.Ε.Γ.Π.)")

total_q = len(st.session_state.questions)

if not st.session_state.completed:
    idx = st.session_state.current_idx
    q_id, cat, q_type, raw_text, correct_ans, media = st.session_state.questions[idx]

    c1, c2 = st.columns([3, 1])
    c1.caption(f"Ενότητα: **{CATEGORY_NAMES.get(cat, cat)}**")
    c2.caption(f"Ερώτηση: **{idx + 1} / {total_q}**")
    st.progress((idx + 1) / total_q)

    with st.container(border=True):
        # 1. Έλεγχος & Προβολή ΜΟΝΟ πραγματικής εικόνας (απομονωμένη, χωρίς περιβάλλοντα κείμενα)
        img_extensions = [".png", ".jpg", ".jpeg", ".webp"]
        found_img = False
        for ext in img_extensions:
            path = os.path.join("images", f"{q_id}{ext}")
            if os.path.exists(path):
                st.image(path, use_container_width=True)
                found_img = True
                break

        # 2. Προβολή Κειμένου / Πίνακα
        if q_type == "MATCHING":
            table_html = parse_and_render_matching(raw_text)
            if table_html:
                st.markdown(table_html, unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="question-box">{raw_text}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="question-box">{raw_text}</div>', unsafe_allow_html=True)

    # Inputs
    user_ans = ""
    if q_type == "MULTIPLE_CHOICE":
        user_ans = st.radio(
            "Επιλέξτε τη σωστή απάντηση:",
            options=["Α", "Β", "Γ", "Δ"],
            index=None,
            key=f"mc_{q_id}_{idx}",
            horizontal=True
        )
    elif q_type == "TRUE_FALSE":
        user_ans = st.text_input(
            "Σημειώστε Σωστό/Λάθος (π.χ. 1-Σ, 2-Λ, 3-Σ, 4-Λ):",
            key=f"tf_{q_id}_{idx}",
            placeholder="1-Σ, 2-Λ, 3-Σ, 4-Λ"
        )
    elif q_type == "MATCHING":
        user_ans = st.text_input(
            "Αντιστοίχιση (π.χ. 1-Α, 2-Β, 3-Γ, 4-Δ):",
            key=f"match_{q_id}_{idx}",
            placeholder="1-Α, 2-Β, 3-Γ, 4-Δ"
        )
    elif q_type == "FILL_BLANKS":
        user_ans = st.text_input(
            "Συμπλήρωση (π.χ. 1-Α, 2-Β, 3-Γ, 4-Δ):",
            key=f"fill_{q_id}_{idx}",
            placeholder="1-Α, 2-Β, 3-Γ, 4-Δ"
        )
    else:
        user_ans = st.text_area(
            "Η απάντησή σας:",
            key=f"open_{q_id}_{idx}",
            placeholder="Πληκτρολογήστε εδώ την απάντηση..."
        )

    st.write("")
    if st.button("Επόμενη Ερώτηση ➔", type="primary", use_container_width=True):
        if user_ans:
            is_correct = check_answer(user_ans, correct_ans, q_type)
            if is_correct:
                st.session_state.score += 1

            st.session_state.user_answers[idx + 1] = {
                "category": cat,
                "prompt": raw_text,
                "user": user_ans,
                "correct": correct_ans,
                "is_correct": is_correct
            }

            if idx + 1 < total_q:
                st.session_state.current_idx += 1
                st.rerun()
            else:
                st.session_state.completed = True
                st.rerun()
        else:
            st.warning("⚠️ Παρακαλώ επιλέξτε ή πληκτρολογήστε μια απάντηση.")

else:
    score = st.session_state.score
    percentage = (score / total_q) * 100

    if percentage >= 70:
        st.balloons()
        st.success(f"### 🎉 Συγχαρητήρια, Επιτυχία!\n**Τελικό Σκορ:** {score}/{total_q} ({percentage:.0f}%)")
    else:
        st.error(f"### ❌ Χρειάζεται περισσότερη εξάσκηση\n**Τελικό Σκορ:** {score}/{total_q} ({percentage:.0f}%) — Βάση: 70%")

    st.divider()
    st.subheader("📋 Αναλυτική Επισκόπηση Απαντήσεων")

    for q_num, data in st.session_state.user_answers.items():
        icon = "✅" if data["is_correct"] else "❌"
        cat_badge = CATEGORY_NAMES.get(data['category'], data['category'])
        with st.expander(f"{icon} Ερώτηση {q_num} ({cat_badge})"):
            st.markdown(f"**Εκφώνηση:**\n\n{data['prompt']}")
            st.markdown(f"* **Η απάντησή σας:** `{data['user']}`")
            st.markdown(f"* **Σωστή απάντηση:** `{data['correct']}`")

    st.write("")
    if st.button("🔄 Νέο Τεστ / Επανεκκίνηση", type="primary", use_container_width=True):
        mode_val = "mock" if quiz_mode == "Προσομοίωση Εξετάσεων (Mock Exam)" else "category"
        st.session_state.questions = fetch_questions(mode_val, selected_category, num_questions)
        st.session_state.current_idx = 0
        st.session_state.score = 0
        st.session_state.completed = False
        st.session_state.user_answers = {}
        st.rerun()