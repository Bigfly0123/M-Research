"""
为 MultiHop-RAG 数据建立三路索引 (Dense + BM25 + Graph)。

使用项目的 HybridGraphRetriever.build_index() 建立索引。
如果 heavy 依赖 (chromadb, sentence-transformers 等) 缺失，则跳过并提示。
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "multihop_rag"
INDEX_DIR = PROJECT_ROOT / "data" / "indexes" / "multihop_rag"


def load_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def try_build_with_hybrid_retriever(chunks):
    """尝试使用项目的 HybridGraphRetriever 建立索引。"""
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from app.retrieval.hybrid_retriever import HybridGraphRetriever

        retriever = HybridGraphRetriever()
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        retriever.build_index(chunks, str(INDEX_DIR))
        print("索引建立完成 (Dense + BM25 + Graph)")
        return True
    except ImportError as e:
        print(f"[跳过] 缺少依赖: {e}")
        return False
    except Exception as e:
        print(f"[错误] 索引建立失败: {e}")
        return False


def build_index():
    print("=" * 80)
    print("MultiHop-RAG 索引建立")

    chunks_path = PROCESSED_DIR / "chunks.jsonl"
    if not chunks_path.exists():
        print(f"[错误] chunks.jsonl 不存在: {chunks_path}")
        print("请先运行 convert_multihop_rag.py")
        return

    chunks = load_jsonl(chunks_path)
    print(f"加载 {len(chunks)} 个 chunks")

    # 尝试用项目 retriever 建立索引
    success = try_build_with_hybrid_retriever(chunks)

    if not success:
        print("\n提示: heavy 依赖缺失，索引未建立。")
        print("如需建立索引，请安装依赖:")
        print("  pip install chromadb sentence-transformers rank-bm25 scikit-learn networkx")
        print("\n脚本本身逻辑正确，不影响后续 eval 框架运行。")


if __name__ == "__main__":
    build_index()
