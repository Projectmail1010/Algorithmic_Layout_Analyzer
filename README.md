# 📄 Algorithmic Resume Layout Analyzer

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)
![PyMuPDF](https://img.shields.io/badge/Engine-PyMuPDF-green)
![Objective](https://img.shields.io/badge/Goal-Structured_Extraction-purple)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://algorithmicresumelayoutanalyzer.streamlit.app/)

## 📌 Project Overview
The **Algorithmic Resume Layout Analyzer** is a text extraction engine designed to convert unstructured, multi-column PDF resumes into structured, semantic data.

Standard PDF extractors (like `pypdf` or `pdfminer`) often treat documents as a flat stream of text, causing "column bleed" where left and right columns are jumbled together. This engine solves that problem by using **Coordinate Geometry** to segment the document into distinct semantic regions (Header, Left Column, Right Column) *before* extraction.

The goal of this tool is to prepare clean, reading-order-corrected text for downstream processing (e.g., NLP pipelines, LLMs, or Resume Parsing APIs).

## 🚀 Key Features

* **Structure Preservation:**
    * **Column Separation:** Algorithmically detects "whitespace rivers" to cleanly separate Left and Right column text, preserving the context of distinct sections (e.g., Skills vs. Experience).
    * **Reading Order Restoration:** Re-sequences text blocks using XY-sorting to match human reading patterns rather than the internal PDF binary stream order.
* **Semantic Tagging:**
    * **Header Identification:** Uses a 2-pass font analysis scan to tag Name/Title blocks based on visual prominence (size, weight) relative to the body text.
    * **Section Grouping:** Groups related text blocks under their respective headers (e.g., all text under "Education" is linked).
* **Visual Verification (Debug Mode):**
    * Includes a built-in "Debug View" that renders bounding boxes around detected regions, allowing developers to visually verify the extraction logic before processing the text.

## 🛠️ Tech Stack

* **Language:** Python
* **Core Library:** PyMuPDF (fitz) for coordinate extraction.
* **Visualization:** Streamlit (for the proof-of-concept interface).
* **Logic:** Custom Heuristic Geometry Algorithms.

## ⚙️ Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/Projectmail1010/Algorithmic_Layout_Analyzer.git
    cd Algorithmic_Layout_Analyzer
    ```

2.  **Create Virtual Env & Install**
    ```bash
    python -m venv venv
    # Windows: venv\Scripts\activate  ||  Mac/Linux: source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Run the Interface**
    ```bash
    streamlit run app.py
    ```

## 🧠 Algorithmic Logic

### 1. The "Bag of Words" Solution
Most parsers fail on 2-column layouts because PDF text is often stored in creation order, not reading order. This engine implements a **Split-Threshold** logic:
1.  Calculates the "Dynamic Center" of the page content.
2.  Scans for vertical whitespace gaps that run through the page.
3.  Sorts text blocks into `Left_Col` and `Right_Col` lists, ensuring that "Experience" on the left doesn't merge with "Skills" on the right.

### 2. Heuristic Header Detection
Instead of relying solely on Regex (which fails on unique section names), the `HeaderExtractor` analyzes the **Font Metadata**:
* **Pass 1:** Scans the document to determine the "Body Font" (modal font size).
* **Pass 2:** Identifies lines that are statistically larger or bolder than the body font.
* **Result:** This allows the system to detect headers like "Tech Stack" or "My Journey" even if they aren't in a hardcoded keyword list.

## ⚠️ Limitations
**Experimental / Out of Scope:**
    * **Floating Elements:** Text boxes with absolute positioning that defy standard flow.
    * **Graphics/Icons:** Visual elements disrupt block recognition.
    * **Complex Nested Tables:** May cause sequence fragmentation.
    * **OCR:** Scanned image-based PDFs are not supported (requires Tesseract integration, planned for v2.0).

## 👤 Author

**[Ayush Vajpayee]** *Final Year BCA Student* [www.linkedin.com/in/ayush-vajpayee]

