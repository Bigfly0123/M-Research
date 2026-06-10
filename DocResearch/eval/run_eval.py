"""
MultiHop-RAG 评测运行器。

EvalRunner 类:
- load_dataset(dataset_path) → 读取 eval_dataset jsonl
- load_config(config_path) → 读取 yaml 配置
- run_single(case, config) → 跑检索/全pipeline，计算指标
- run_all(dataset_path, config_path, output_path) → 跑全部，保存结果jsonl

支持两种 mode: retrieval_only (只跑检索) 和 full_qa (跑完整pipeline)。
"""
import json
import time
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 将项目根目录加入 sys.path 以支持直接运行
sys.path.insert(0, str(PROJECT_ROOT))

from eval.metrics import (
    gold_doc_recall_at_k,
    all_gold_docs_hit_at_k,
    gold_chunk_recall_at_k,
    selected_evidence_recall,
    answer_keyword_coverage,
)


def load_jsonl(path: Path) -> List[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(data: List[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def load_yaml_config(path: Path) -> dict:
    """加载 YAML 配置文件。"""
    try:
        import yaml
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        # 无 pyyaml 时手动解析简单 yaml
        config = {}
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip()
                    if val.lower() == "true":
                        val = True
                    elif val.lower() == "false":
                        val = False
                    elif val.isdigit():
                        val = int(val)
                    else:
                        try:
                            val = float(val)
                        except ValueError:
                            pass
                    config[key] = val
        return config


class MockRetriever:
    """Mock 检索器，用于依赖缺失时提供占位实现。"""

    def retrieve(self, query: str, **kwargs) -> dict:
        return {
            "retrieved_doc_ids": [],
            "retrieved_chunk_ids": [],
            "chunks": [],
        }


class EvalRunner:
    """MultiHop-RAG 评测运行器。"""

    def __init__(self):
        self.retriever = None

    def load_dataset(self, dataset_path: str) -> List[dict]:
        """读取 eval_dataset jsonl。"""
        path = Path(dataset_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / dataset_path
        rows = load_jsonl(path)
        print(f"加载数据集: {len(rows)} 条 <- {path}")
        return rows

    def load_config(self, config_path: str) -> dict:
        """读取 yaml 配置。"""
        path = Path(config_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / config_path
        config = load_yaml_config(path)
        print(f"加载配置: {path}")
        return config

    def _init_retriever(self, config: dict):
        """初始化检索器 (按需)。"""
        if self.retriever is not None:
            return

        index_dir = str(PROJECT_ROOT / "data" / "indexes" / "multihop_rag")
        try:
            sys.path.insert(0, str(PROJECT_ROOT))
            from app.retrieval.hybrid_retriever import HybridGraphRetriever
            retriever = HybridGraphRetriever()
            loaded = retriever.load_index(index_dir)
            if loaded:
                self.retriever = retriever
                print("检索器加载成功 (HybridGraphRetriever)")
            else:
                print("[警告] 索引加载失败，使用 MockRetriever")
                self.retriever = MockRetriever()
        except ImportError as e:
            print(f"[警告] 检索器依赖缺失 ({e})，使用 MockRetriever")
            self.retriever = MockRetriever()
        except Exception as e:
            print(f"[警告] 检索器初始化失败 ({e})，使用 MockRetriever")
            self.retriever = MockRetriever()

    def _get_retrieval_plan(self, config: dict) -> List[str]:
        """根据配置决定检索路。"""
        retriever_conf = config.get("retriever", config)
        plan = []
        if retriever_conf.get("use_dense", True):
            plan.append("dense")
        if retriever_conf.get("use_bm25", False):
            plan.append("bm25")
        if retriever_conf.get("use_graph", False):
            plan.append("graph_expand")
        return plan if plan else ["dense"]

    def run_single(self, case: dict, config: dict) -> dict:
        """跑单条检索/全pipeline，计算指标。"""
        question = case.get("question", "")
        gold_doc_ids = case.get("gold_doc_ids", [])
        gold_chunk_ids = case.get("gold_chunk_ids", [])
        expected_answer = case.get("expected_answer", "")
        mode = config.get("mode", "retrieval_only")
        top_k = config.get("retriever", config).get("top_k", 10)

        # 初始化检索器
        self._init_retriever(config)

        # 获取检索计划
        retrieval_plan = self._get_retrieval_plan(config)

        start_time = time.time()

        trace = {}
        retrieved_doc_ids = []
        retrieved_chunk_ids = []
        selected_chunk_ids = []
        answer = ""

        if mode == "retrieval_only":
            # 只跑检索
            result = self.retriever.retrieve(question, retrieval_plan=retrieval_plan, top_k=top_k)

            # 从结果中提取 doc_ids 和 chunk_ids
            if hasattr(result, "chunks"):
                for chunk in result.chunks:
                    retrieved_chunk_ids.append(chunk.chunk_id)
                    doc_id = chunk.chunk_id.rsplit("-c", 1)[0] if "-c" in chunk.chunk_id else ""
                    if doc_id:
                        retrieved_doc_ids.append(doc_id)
            elif isinstance(result, dict):
                retrieved_doc_ids = result.get("retrieved_doc_ids", [])
                retrieved_chunk_ids = result.get("retrieved_chunk_ids", [])

            trace = {
                "retrieved_doc_ids": retrieved_doc_ids,
                "retrieved_chunk_ids": retrieved_chunk_ids,
                "retrieval_plan": retrieval_plan,
            }

        elif mode == "full_qa":
            # 跑完整 pipeline
            result = self.retriever.retrieve(question, retrieval_plan=retrieval_plan, top_k=top_k)

            if hasattr(result, "chunks"):
                for chunk in result.chunks:
                    retrieved_chunk_ids.append(chunk.chunk_id)
                    doc_id = chunk.chunk_id.rsplit("-c", 1)[0] if "-c" in chunk.chunk_id else ""
                    if doc_id:
                        retrieved_doc_ids.append(doc_id)

            # TODO: 后续接入 evidence_composer, judge, repair 等模块
            answer = ""
            selected_chunk_ids = retrieved_chunk_ids

            trace = {
                "retrieved_doc_ids": retrieved_doc_ids,
                "retrieved_chunk_ids": retrieved_chunk_ids,
                "selected_chunk_ids": selected_chunk_ids,
                "answer": answer,
                "retrieval_plan": retrieval_plan,
            }

        latency_ms = int((time.time() - start_time) * 1000)

        # 计算指标
        metrics = {
            "gold_doc_recall@10": gold_doc_recall_at_k(retrieved_doc_ids, gold_doc_ids, top_k),
            "all_gold_docs_hit@10": all_gold_docs_hit_at_k(retrieved_doc_ids, gold_doc_ids, top_k),
            "gold_chunk_recall@10": gold_chunk_recall_at_k(retrieved_chunk_ids, gold_chunk_ids, top_k),
            "selected_evidence_recall": selected_evidence_recall(selected_chunk_ids, gold_chunk_ids),
            "answer_keyword_coverage": answer_keyword_coverage(answer, expected_answer) if answer else None,
            "latency_ms": latency_ms,
        }

        return {
            "question_id": case.get("id", ""),
            "source_dataset": case.get("source_dataset", "MultiHop-RAG"),
            "question": question,
            "expected_answer": expected_answer,
            "gold_doc_ids": gold_doc_ids,
            "gold_chunk_ids": gold_chunk_ids,
            "trace": trace,
            "metrics": metrics,
        }

    def run_all(
        self,
        dataset_path: str,
        config_path: str,
        output_path: str,
    ) -> List[dict]:
        """跑全部评测，保存结果 jsonl。"""
        dataset = self.load_dataset(dataset_path)
        config = self.load_config(config_path)

        results = []
        for i, case in enumerate(dataset):
            result = self.run_single(case, config)
            results.append(result)
            if (i + 1) % 50 == 0:
                print(f"进度: {i + 1}/{len(dataset)}")

        # 保存结果
        out = Path(output_path)
        if not out.is_absolute():
            out = PROJECT_ROOT / output_path
        write_jsonl(results, out)

        # 输出汇总
        self._print_summary(results, config.get("name", "unknown"))
        return results

    def _print_summary(self, results: List[dict], config_name: str):
        """输出评测汇总。"""
        print(f"\n{'=' * 60}")
        print(f"配置: {config_name}, 样本数: {len(results)}")

        metric_keys = ["gold_doc_recall@10", "all_gold_docs_hit@10", "gold_chunk_recall@10", "selected_evidence_recall"]
        for mk in metric_keys:
            values = [r["metrics"][mk] for r in results if r["metrics"].get(mk) is not None]
            if values:
                avg = sum(values) / len(values)
                print(f"  {mk}: {avg:.4f} (n={len(values)})")
            else:
                print(f"  {mk}: N/A")

        latencies = [r["metrics"]["latency_ms"] for r in results if r["metrics"].get("latency_ms") is not None]
        if latencies:
            print(f"  avg_latency_ms: {sum(latencies)/len(latencies):.0f}")


def main():
    parser = argparse.ArgumentParser(description="MultiHop-RAG 评测运行器")
    parser.add_argument("--dataset", required=True, help="eval_dataset jsonl 路径")
    parser.add_argument("--config", required=True, help="yaml 配置路径")
    parser.add_argument("--output", required=True, help="结果输出 jsonl 路径")
    args = parser.parse_args()

    runner = EvalRunner()
    runner.run_all(args.dataset, args.config, args.output)


if __name__ == "__main__":
    main()
