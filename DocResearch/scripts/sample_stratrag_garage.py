"""
从 StratRAG 和 GaRAGe 的 eval_dataset_v1.jsonl 中抽样。

规则:
- random seed=42
- 优先选择 question、gold_chunk_ids 都非空的样本
- StratRAG 抽 100 条, GaRAGe 抽 50 条
"""
import json
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(data, path: Path):
    with path.open("w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"写入 {len(data)} 条 -> {path}")


def is_valid(row):
    return bool(row.get("question")) and bool(row.get("gold_chunk_ids"))


def sample_dataset(name: str, processed_dir: Path, sample_size: int):
    eval_path = processed_dir / "eval_dataset_v1.jsonl"
    if not eval_path.exists():
        print(f"跳过 {name}: {eval_path} 不存在")
        return

    eval_rows = load_jsonl(eval_path)
    print(f"\n{name}: 加载 {len(eval_rows)} 条")

    valid = [r for r in eval_rows if is_valid(r)]
    invalid = [r for r in eval_rows if not is_valid(r)]
    print(f"  完整样本: {len(valid)}, 不完整: {len(invalid)}")

    random.shuffle(valid)
    random.shuffle(invalid)

    if len(valid) >= sample_size:
        sampled = valid[:sample_size]
    else:
        sampled = valid + invalid[:sample_size - len(valid)]

    out_path = processed_dir / f"eval_dataset_sample_{sample_size}.jsonl"
    write_jsonl(sampled, out_path)

    v = sum(1 for r in sampled if is_valid(r))
    print(f"  sample_{sample_size}: {v}/{sample_size} 条完整 ({v/sample_size*100:.1f}%)")


def main():
    random.seed(42)
    sample_dataset("StratRAG", PROJECT_ROOT / "data" / "processed" / "stratrag", 100)
    sample_dataset("GaRAGe", PROJECT_ROOT / "data" / "processed" / "garage", 50)


if __name__ == "__main__":
    main()
