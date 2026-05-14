import os
import time
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAG_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "app", "rag"))
UPLOAD_DIR = os.path.join(RAG_DIR, "uploads")
DB_PATH = os.path.join(RAG_DIR, "chroma_db_test")


def _pick_pdf_path() -> str | None:
    if not os.path.isdir(UPLOAD_DIR):
        return None
    for name in os.listdir(UPLOAD_DIR):
        if name.lower().endswith(".pdf"):
            return os.path.join(UPLOAD_DIR, name)
    return None


def main() -> None:
    load_dotenv(os.path.join(RAG_DIR, "..", "..", ".env"))

    pdf_path = _pick_pdf_path()
    if pdf_path:
        print(f"[TEST] Using PDF: {pdf_path}")
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()
    else:
        print("[TEST] No PDF found, using a dummy document.")
        docs = [Document(page_content="This is a test document.")]

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = splitter.split_documents(docs)
    print(f"[TEST] Split count: {len(splits)}")

    embeddings = DashScopeEmbeddings(model="text-embedding-v4")
    print("[TEST] Embedding ping...")
    ping_start = time.time()
    embeddings.embed_documents(["ping"])
    print(f"[TEST] Embedding ping done ({time.time() - ping_start:.2f}s)")

    print("[TEST] Writing to Chroma...")
    write_start = time.time()
    Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=DB_PATH,
    )
    print(f"[TEST] Write done ({time.time() - write_start:.2f}s)")


if __name__ == "__main__":
    main()
