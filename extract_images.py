import pymupdf
import sqlite3
import os
import io
from PIL import Image

os.makedirs("images", exist_ok=True)

PDF_MAP = {
    "culture": "data/culture.pdf",
    "geography": "data/geography.pdf",
    "history": "data/history.pdf",
    "institutions": "data/institutions.pdf"
}

conn = sqlite3.connect("quiz.db")
cursor = conn.cursor()

# 1. Επαναφέρουμε τις MATCHING σε none για εικόνα - θα εμφανίζονται ως native πίνακες
cursor.execute("UPDATE questions SET media_type = 'none' WHERE question_type = 'MATCHING'")

# 2. Εντοπίζουμε μόνο όσες πραγματικά έχουν φωτογραφία/χάρτη/μνημείο
cursor.execute("""
    UPDATE questions SET media_type = 'image' 
    WHERE question_text LIKE '%εικον%' 
       OR question_text LIKE '%φωτογραφ%' 
       OR question_text LIKE '%χάρτη%' 
       OR question_text LIKE '%κτίσματος%'
       OR (category = 'geography' AND CAST(SUBSTR(id, 5) AS INTEGER) >= 51)
       OR (category = 'history' AND CAST(SUBSTR(id, 6) AS INTEGER) BETWEEN 38 AND 60)
""")
conn.commit()

cursor.execute("SELECT id, category FROM questions WHERE media_type = 'image'")
targets = cursor.fetchall()
conn.close()

print(f"🎯 Βρέθηκαν {len(targets)} ερωτήσεις που απαιτούν πραγματικό αρχείο εικόνας.\n")

for cat, pdf_path in PDF_MAP.items():
    if not os.path.exists(pdf_path):
        continue

    doc = pymupdf.open(pdf_path)
    cat_targets = [qid for qid, c in targets if c == cat]

    for qid in cat_targets:
        q_num = qid.split("_")[1]
        
        # Εντοπισμός της σελίδας που περιέχει το ΘΕΜΑ
        for page_idx, page in enumerate(doc):
            text = page.get_text()
            if f"ΘΕΜΑ {q_num}" in text or f"ΘΕΜΑ  {q_num}" in text:
                image_list = page.get_images(full=True)
                
                # Φιλτράρισμα: αγνοούμε μικροσκοπικά εικονίδια/λογότυπα (< 100px)
                valid_images = []
                for img_info in image_list:
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    if base_image["width"] > 120 and base_image["height"] > 120:
                        valid_images.append(base_image)

                if valid_images:
                    # Επιλέγουμε τη μεγαλύτερη embedded εικόνα του θέματος (τον χάρτη/φωτογραφία)
                    best_img = max(valid_images, key=lambda x: x["width"] * x["height"])
                    img_bytes = best_img["image"]
                    ext = best_img["ext"]

                    out_path = os.path.join("images", f"{qid}.{ext}")
                    with open(out_path, "wb") as f:
                        f.write(img_bytes)
                    print(f"  ✅ [{cat}] Εξήχθη καθαρή εικόνα: {out_path} ({best_img['width']}x{best_img['height']})")
                break

    doc.close()

print("\n🚀 Η εξαγωγή πραγματικών γραφικών ολοκληρώθηκε!")