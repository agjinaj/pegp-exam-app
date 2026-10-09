import sqlite3
import pandas as pd

conn = sqlite3.connect("quiz.db")

print("=" * 65)
print("🔍 ΕΛΕΓΧΟΣ ΑΚΕΡΑΙΟΤΗΤΑΣ ΒΑΣΗΣ ΔΕΔΟΜΕΝΩΝ (QUIZ.DB)")
print("=" * 65)

# 1. Έλεγχος για κενές ή ελλιπείς τιμές
empty_checks = conn.execute("""
    SELECT id, category, question_text, correct_answer 
    FROM questions 
    WHERE TRIM(question_text) = '' 
       OR TRIM(correct_answer) = '' 
       OR question_text IS NULL 
       OR correct_answer IS NULL
""").fetchall()

if empty_checks:
    print(f"⚠️ Βρέθηκαν {len(empty_checks)} εγγραφές με κενή εκφώνηση ή απάντηση:")
    for row in empty_checks:
        print(f"   • ID: {row[0]} | Κατηγορία: {row[1]}")
else:
    print("✅ Κανένα κενό πεδίο: Όλες οι 300 ερωτήσεις έχουν εκφώνηση και απάντηση!")

# 2. Έλεγχος κατανομής τύπων ερωτήσεων ανά κατηγορία
print("\n📊 ΚΑΤΑΝΟΜΗ ΤΥΠΩΝ ΕΡΩΤΗΣΕΩΝ:")
cursor = conn.cursor()
cursor.execute("""
    SELECT category, question_type, COUNT(*) 
    FROM questions 
    GROUP BY category, question_type
    ORDER BY category, COUNT(*) DESC
""")
for cat, q_type, count in cursor.fetchall():
    print(f"   • [{cat:<12}] {q_type:<16}: {count}")

# 3. Έλεγχος ερωτήσεων με εικόνα
cursor.execute("SELECT category, COUNT(*) FROM questions WHERE media_type = 'image' GROUP BY category")
image_counts = cursor.fetchall()
print("\n🖼️ ΕΡΩΤΗΣΕΙΣ ΠΟΥ ΑΠΑΙΤΟΥΝ ΕΙΚΟΝΑ:")
for cat, count in image_counts:
    print(f"   • {cat}: {count} ερωτήσεις")

# 4. Εξαγωγή σε ένα ενιαίο Excel για γρήγορο visual inspection
df = pd.read_sql_query("SELECT id, category, question_type, media_type, question_text, correct_answer FROM questions ORDER BY category, CAST(SUBSTR(id, INSTR(id, '_') + 1) AS INTEGER)", conn)
excel_out = "all_300_questions_audit.xlsx"
df.to_excel(excel_out, index=False)
print(f"\n📁 Δημιουργήθηκε το αρχείο: '{excel_out}' για πλήρη έλεγχο στο Excel/LibreOffice!")
print("=" * 65)

conn.close()