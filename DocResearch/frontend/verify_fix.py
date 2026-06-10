"""Verify the import fix works"""
import streamlit as st
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

st.set_page_config(page_title="Verify", layout="wide")
st.title("Verify Fix")

with st.sidebar:
    uploaded = st.file_uploader("Upload any file", type=["pdf"], accept_multiple_files=True)
    btn = st.button("Test", disabled=not uploaded)

if uploaded and btn:
    # This is what the fixed loaders.py does
    from langchain_community.document_loaders.pdf import PyPDFLoader
    from app.ingestion.loaders import load_files, RawDocument
    st.success("Fixed imports OK - no crash on re-run?")
    print("[VERIFY] done", flush=True)

print("[VERIFY] === Script end ===", flush=True)
