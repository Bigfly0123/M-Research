"""
从 eval_dataset_v1.jsonl 中抽样。

规则:
- random seed=42
- 优先选 question_type 分布均匀的 30 条
- 输出 sample_30 和 sample_42 (全量副本)
"""
import json
import random
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "techdocqa"


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


def stratified_sample(rows, n, seed=42):
    """按 question_type 分层抽样，尽量让各类型均匀分布。"""
    rng = random.Random(seed)

    type_groups = {}
    for r in rows:
        qt = r.get("question_type", "unknown")
        type_groups.setdefault(qt, []).append(r)

    for group in type_groups.values():
        rng.shuffle(group)

    types_sorted = sorted(type_groups.keys())
    sampled = []
    remaining = n

    per_type = remaining // len(types_sorted)
    extras = remaining - per_type * len(types_sorted)

    for i, qt in enumerate(types_sorted):
        take = per_type + (1 if i < extras else 0)
        take = min(take, len(type_groups[qt]))
        sampled.extend(type_groups[qt][:take])
        type_groups[qt] = type_groups[qt][take:]

    shortfall = n - len(sampled)
    if shortfall > 0:
        leftover = []
        for qt in types_sorted:
            leftover.extend(type_groups[qt])
        rng.shuffle(leftover)
        sampled.extend(leftover[:shortfall])

    rng.shuffle(sampled)
    return sampled


def main():
    eval_path = PROCESSED_DIR / "eval_dataset_v1.jsonl"
    eval_rows = load_jsonl(eval_path)
    print(f"加载 {len(eval_rows)} 条 eval 数据")

    type_dist = Counter(r.get("question_type") for r in eval_rows)
    print(f"question_type 分布: {dict(type_dist)}")

    sample_30 = stratified_sample(eval_rows, 30, seed=42)
    out_30 = PROCESSED_DIR / "eval_dataset_sample_30.jsonl"
    write_jsonl(sample_30, out_30)

    sample_30_dist = Counter(r.get("question_type") for r in sample_30)
    print(f"  sample_30 question_type 分布: {dict(sample_30_dist)}")

    out_42 = PROCESSED_DIR / "eval_dataset_sample_42.jsonl"
    write_jsonl(eval_rows, out_42)


if __name__ == "__main__":
    main()
