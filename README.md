# 🏛️ Hellenic Citizenship Exam Prep (Π.Ε.Γ.Π.)

A full-stack educational web application and data ingestion pipeline designed for candidates preparing for the **Certificate of Knowledge for Naturalization (P.E.G.P.)** examinations in Greece.

Built with **Python**, **Streamlit**, and **SQLite**, the project parses, audits, and serves all 300 official exam questions published by the Hellenic Ministry of Interior.

---

## 🌟 Key Features

- **Official Exam Distribution (Mock Exam):** Simulates the exact structure of the real 20-question exam (6 History, 6 Political Institutions, 4 Geography, 4 Culture).
- **Thematic Practice Mode:** Focus on specific subjects with customizable question limits.
- **Anti-Memorization Engine:** Dynamic shuffling of multiple-choice answers at runtime to prevent visual/rote learning patterns.
- **Automated Asset & Media Rendering:** Embedded historical portraits, maps, and monuments extracted directly from source materials.
- **Structured Matching Tables:** Automated parsing and rendering of two-column matching questions.
- **Fault-Tolerant Text Grading:** Accent- and case-insensitive normalization with similarity tolerance for open-text answers.

---

## 🏗️ Architecture & Data Pipeline

```
data/*.pdf ──▶ build_database.py ──▶ quiz.db (300 validated Qs)
                 │                      │
                 ▼                      ▼
         extract_images.py           app.py (Streamlit UI)
                 │
                 ▼
             images/*.jpeg
```

1. **Extraction (ETL):** `build_database.py` utilizes `pdfplumber` with custom regex normalization rules to handle OCR artifacts, column breaks, and shaded text extraction.
2. **Asset Pipeline:** `extract_images.py` leverages `PyMuPDF` (`fitz`) to extract raw raster graphics without page headers or solution reveals.
3. **Data Integrity:** `audit_database.py` validates 100% completion (300/300 verified questions and answers).

---

## 🚀 Quick Start

### 1. Clone & Set Up Environment
```bash
git clone [https://github.com/](https://github.com/)<your-username>/citizenship-prep-app.git
cd citizenship-prep-app
python -m venv venv
source venv/bin/activate  # On Linux/macOS
pip install -r requirements.txt
```

### 2. Run the Application
```bash
streamlit run app.py
```
