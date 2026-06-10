"""
从转换后的 eval_dataset_v1.jsonl 中抽样。

规则:
- random seed=42
- 优先选择 question、expected_answer、gold_chunk_ids 都非空的样本
- 输出 sample_100 和 sample_300
"""
import json
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "multihop_rag"


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


def is_valid_sample(row):
    """判断样本是否完整: question、expected_answer、gold_chunk_ids 都非空。"""
    if not row.get("question"):
        return False
    if not row.get("expected_answer"):
        return False
    if not row.get("gold_chunk_ids"):
        return False
    return True


def sample():
    random.seed(42)

    eval_path = PROCESSED_DIR / "eval_dataset_v1.jsonl"
    eval_rows = load_jsonl(eval_path)
    print(f"加载 {len(eval_rows)} 条 eval 数据")

    # 分离完整样本和不完整样本
    valid_rows = [r for r in eval_rows if is_valid_sample(r)]
    invalid_rows = [r for r in eval_rows if not is_valid_sample(r)]
    print(f"完整样本: {len(valid_rows)}, 不完整样本: {len(invalid_rows)}")

    # 优先从完整样本中抽取
    random.shuffle(valid_rows)
    random.shuffle(invalid_rows)

    for sample_size in [100, 300]:
        if len(valid_rows) >= sample_size:
            sampled = valid_rows[:sample_size]
        else:
            # 完整样本不够，补充不完整样本
            need = sample_size - len(valid_rows)
            sampled = valid_rows + invalid_rows[:need]

        out_path = PROCESSED_DIR / f"eval_dataset_sample_{sample_size}.jsonl"
        write_jsonl(sampled, out_path)

        # 统计抽样质量
        valid_in_sample = sum(1 for r in sampled if is_valid_sample(r))
        print(f"  sample_{sample_size}: {valid_in_sample}/{sample_size} 条完整 ({valid_in_sample/sample_size*100:.1f}%)")


if __name__ == "__main__":
    sample()
