import streamlit as st
import tempfile
import os
import pymupdf as fitz

# IMPORT YOUR CUSTOM MODULES
from header_extractor import HeaderExtractor
from layout_engine import generate_layout_debug_pdf

st.set_page_config(page_title="Resume Layout Engine", layout="wide")

st.title("📄 Algorithmic Resume Layout Analyzer")
st.markdown("**System Status:** `Active` | **Engine:** `v1.0.2` | **Mode:** `Geometric Parsing`")

# Create the main layout
col1, col2 = st.columns([1, 3])

with col1:

    with st.expander("How it Works", expanded=True):
        st.markdown("""
        **Core Engine: Geometric Parsing (v1.0.2)**
        Unlike standard regex parsers that treat PDFs as flat text strings, this engine analyzes the **spatial geometry** of the document.
        
        1.  **Font Bootstrap:** Identifies header styles via a 2-pass heuristic scan.
        2.  **Scan-Line Analysis:** Detects vertical whitespace rivers to identify column splits.
        3.  **XY-Sort:** Re-sequences text blocks based on visual reading order (Top-Left → Bottom-Right) rather than internal PDF stream order.
        """)

    st.write("### ✅ Operational Design Domain")
    st.success("""
    **Supported Layouts:**
    * **Single-Column Linear:** Standard chronological resumes.
    * **Clean 2-Column Grids:** Distinct separation between Left/Right columns.
    * **Text-Layer PDFs:** Documents generated from Word/LaTeX/Docs.
    """)
    
    st.write("### ⚠️ Known Limitations")
    st.warning("""
    **Experimental / Out of Scope:**
    * **Floating Elements:** Text boxes with absolute positioning that defy standard flow.
    * **Graphics/Icons:** Visual elements disrupt block recognition.
    * **Scanned Images:** Requires OCR (planned for v2.0).
    * **Complex Nested Tables:** May cause sequence fragmentation.
    """)
    
    st.info("💡 **Note to Recruiters:** This project demonstrates *algorithmic layout analysis* rather than commercial-grade parsing. It is designed to visualize how machines 'see' document structure.")

    st.write("### Input Source")
    
    # 1. Toggle between Upload and Sample
    mode = st.radio("Select Input Method:", ("Upload PDF", "Use Sample Resume"))
    
    uploaded_file = None
    selected_sample_path = None
    
    if mode == "Upload PDF":
        uploaded_file = st.file_uploader("Select PDF", type="pdf")
    else:
        # Check if resumes folder exists
        resume_folder = "resumes"
        if os.path.exists(resume_folder) and os.path.isdir(resume_folder):
            files = [f for f in os.listdir(resume_folder) if f.lower().endswith(".pdf")]
            if files:
                selected_file = st.selectbox("Choose a sample resume:", files)
                selected_sample_path = os.path.join(resume_folder, selected_file)
            else:
                st.error("No PDF files found in 'resumes' folder.")
        else:
            st.error(f"Folder '{resume_folder}' not found. Please create it and add PDFs.")
            

    st.markdown("---")
    st.markdown("**Legend:**")
    st.markdown("🟥 **Header** (Name/Title)")
    st.markdown("🟦 **Left Column**")
    st.markdown("🟩 **Right Column**")
    st.markdown("🟧 **Body Text**")
    st.markdown("🟦 **Cyan Section Block**")

with col2:
    # Logic to handle processing based on mode
    process_path = None
    
    # CASE 1: User Uploaded a File
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            process_path = tmp.name
            
    # CASE 2: User Selected a Sample
    elif selected_sample_path:
        process_path = selected_sample_path

    # Execution Block
    if process_path:
        try:
            # 1. Header Extraction
            with st.spinner("Analyzing Font Styles..."):
                extractor = HeaderExtractor()
                headers, body_size, avg_height = extractor.extract(process_path)
            
            # 2. Layout Engine
            with st.spinner("Calculating Geometry & Splits..."):
                debug_pdf_bytes = generate_layout_debug_pdf(process_path, headers, body_size, avg_height)
            
            st.success(f"**Analysis Complete:** Detected Body Font Size: {body_size}pt")

            # --- VISUALIZATION SECTION ---
            st.subheader("Layout Deconstruction")
            
            view_col1, view_col2 = st.columns(2)
            
            with view_col1:
                st.markdown("#### 📄 Original Input")
                with fitz.open(process_path) as doc_in:
                    page_in = doc_in[0]
                    pix_in = page_in.get_pixmap(matrix=fitz.Matrix(2, 2))
                    st.image(pix_in.tobytes(), use_container_width=True)

            with view_col2:
                st.markdown("#### 🤖 Algorithmic Output")
                if debug_pdf_bytes:
                    with fitz.open(stream=debug_pdf_bytes, filetype="pdf") as doc_out:
                        page_out = doc_out[0]
                        pix_out = page_out.get_pixmap(matrix=fitz.Matrix(2, 2))
                        st.image(pix_out.tobytes(), use_container_width=True)

            # Download Button
            if debug_pdf_bytes:
                st.download_button(
                    label="📥 Download Debug PDF Report", 
                    data=debug_pdf_bytes, 
                    file_name="layout_analysis_report.pdf",
                    mime="application/pdf"
                )

        except Exception as e:
            st.error(f"An error occurred: {e}")
            
        finally:
            # Cleanup temp file ONLY if it was created from upload (not sample)
            if mode == "Upload PDF" and process_path and os.path.exists(process_path):
                os.remove(process_path)
    else:
        st.info("👈 Waiting for input... Upload a resume or select a sample to see the geometric engine in action.")