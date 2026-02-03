import streamlit as st
import tempfile
import os
import fitz  # PyMuPDF

# IMPORT YOUR CUSTOM MODULES
from header_extractor import HeaderExtractor
from layout_engine import generate_layout_debug_pdf

st.set_page_config(page_title="Resume Layout Engine", layout="wide")

st.title("📄 Algorithmic Resume Layout Analyzer")
st.markdown("**System Status:** `Active` | **Engine:** `v1.0.2` | **Mode:** `Geometric Parsing`")

# Create the main layout
col1, col2 = st.columns([1, 3])

with col1:
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
    st.info("""
    **Architecture Note:**
    This system uses a 2-stage pass:
    1. `HeaderExtractor`: bootstraps font styles.
    2. `LayoutEngine`: calculates geometric column splits.
    """)
    
    st.markdown("---")
    st.markdown("**Legend:**")
    st.markdown("🟥 **Header** (Name/Title)")
    st.markdown("🟦 **Left Column**")
    st.markdown("🟩 **Right Column**")
    st.markdown("🟧 **Body Text**")

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