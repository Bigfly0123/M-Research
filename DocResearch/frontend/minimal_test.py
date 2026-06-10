"""
Minimal Streamlit test: 不导入任何 DocResearch 代码，
只测 file_uploader + conditional button + st.success 这个模式。
"""
import streamlit as st
import os
import sys
import time

st.set_page_config(page_title="Minimal Test", page_icon="🔍", layout="wide")
st.title("Minimal Streamlit Test")
st.caption("Testing file_uploader + button + success pattern")

with st.sidebar:
    st.header("Upload Test")
    uploaded = st.file_uploader("Upload any file", type=["md", "txt", "pdf"], accept_multiple_files=True)

    if uploaded and st.button("Process"):
        print("[MINIMAL] Button clicked!", flush=True)
        time.sleep(1)
        st.success("Processing done!")
        print("[MINIMAL] Success shown", flush=True)

print("[MINIMAL] === Script end ===", flush=True)
