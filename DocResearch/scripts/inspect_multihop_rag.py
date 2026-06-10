"""
检查 MultiHop-RAG 原始数据结构。
不假设字段名固定，先 inspect 再决定转换逻辑。
"""
import json
import sys
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "multihop_rag"


def load_json_any(path: Path):
    """加载 JSON 或 JSONL 文件。"""
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows


def preview_obj(name, obj, n=3):
    print("\n" + "=" * 80)
    print(f"[{name}] type={type(obj).__name__}")

    if isinstance(obj, list):
        print(f"len={len(obj)}")
        for i, row in enumerate(obj[:n]):
            print(f"\n--- sample {i} ---")
            print(json.dumps(row, ensure_ascii=False, indent=2)[:3000])
    elif isinstance(obj, dict):
        print(f"keys={list(obj.keys())[:30]}")
        for i, (k, v) in enumerate(list(obj.items())[:n]):
            print(f"\n--- item {i}, key={k} ---")
            print(json.dumps(v, ensure_ascii=False, indent=2)[:3000])


def key_stats(obj):
    """统计字段出现频率。"""
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        counter = Counter()
        for row in obj:
            for k in row.keys():
                counter[k] += 1
        print("\n字段出现频率:")
        for k, c in counter.most_common():
            print(f"  {k}: {c}")


def analyze_qa(qa_data):
    """分析 QA 数据集的 question_type 和 evidence_list 分布。"""
    print("\n" + "=" * 80)
    print("[MultiHopRAG.json 详细分析]")

    # question_type 分布
    qt_counter = Counter(row.get("question_type") for row in qa_data)
    print("\nquestion_type 分布:")
    for qt, cnt in qt_counter.most_common():
        print(f"  {qt}: {cnt}")

    # evidence_list 长度分布
    ev_len_counter = Counter(len(row.get("evidence_list", [])) for row in qa_data)
    print("\nevidence_list 长度分布:")
    for ev_len, cnt in sorted(ev_len_counter.items()):
        print(f"  长度={ev_len}: {cnt}条")

    # evidence 字段分析
    if qa_data and qa_data[0].get("evidence_list"):
        first_ev = qa_data[0]["evidence_list"][0]
        print(f"\nevidence 单条字段: {list(first_ev.keys())}")

    # query/answer 非空统计
    q_nonempty = sum(1 for r in qa_data if r.get("query"))
    a_nonempty = sum(1 for r in qa_data if r.get("answer"))
    print(f"\nquery 非空: {q_nonempty}/{len(qa_data)}")
    print(f"answer 非空: {a_nonempty}/{len(qa_data)}")


def analyze_corpus(corpus_data):
    """分析 corpus 数据集。"""
    print("\n" + "=" * 80)
    print("[corpus.json 详细分析]")

    # source 分布
    src_counter = Counter(row.get("source") for row in corpus_data)
    print("\nsource 分布 (top 10):")
    for src, cnt in src_counter.most_common(10):
        print(f"  {src}: {cnt}")

    # category 分布
    cat_counter = Counter(row.get("category") for row in corpus_data)
    print("\ncategory 分布:")
    for cat, cnt in cat_counter.most_common():
        print(f"  {cat}: {cnt}")

    # body 长度统计
    body_lens = [len(row.get("body", "")) for row in corpus_data]
    print(f"\nbody 长度: min={min(body_lens)}, max={max(body_lens)}, avg={sum(body_lens)/len(body_lens):.0f}")

    # title 唯一性
    titles = [row.get("title") for row in corpus_data]
    print(f"title 总数: {len(titles)}, 唯一: {len(set(titles))}")


def main():
    print(f"原始数据目录: {RAW_DIR}")
    print(f"目录存在: {RAW_DIR.exists()}")

    # 查找所有数据文件
    filenames = ["MultiHopRAG.json", "corpus.json"]
    for fn in filenames:
        path = RAW_DIR / fn
        if not path.exists():
            print(f"[警告] 文件不存在: {path}")
            continue
        obj = load_json_any(path)
        preview_obj(fn, obj)
        key_stats(obj)

    # 详细分析
    qa_path = RAW_DIR / "MultiHopRAG.json"
    corpus_path = RAW_DIR / "corpus.json"

    if qa_path.exists():
        qa_data = load_json_any(qa_path)
        analyze_qa(qa_data)

    if corpus_path.exists():
        corpus_data = load_json_any(corpus_path)
        analyze_corpus(corpus_data)

    print("\n" + "=" * 80)
    print("Inspect 完成。")


if __name__ == "__main__":
    main()
