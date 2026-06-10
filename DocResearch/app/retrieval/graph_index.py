"""
Lightweight Graph Index: 轻量级术语图索引。

不做复杂知识图谱，只建立 term→chunks、chunk→terms、term→related_terms 的映射。
用于 graph expansion 检索：从一个术语出发，找到相关术语和相关 chunk，
解决多跳概念关联问题。

Day4 增强:
- 更丰富的术语抽取规则 (驼峰/下划线/大写缩写/dashed/引用括号/技术词)
- 带权重的 co-occurrence 图 (共现次数越多边越强)
- 多 hop 扩展 (BFS，按边权排序)
- 统计接口 (term 数量、边数量、平均度数)
- trace 记录扩展路径
"""

import os
import json
import re
from typing import List, Set, Dict, Optional, Tuple
from collections import defaultdict
from pydantic import BaseModel, Field


class GraphStats(BaseModel):
    """图统计信息。"""
    total_terms: int = 0
    total_chunks_indexed: int = 0
    total_edges: int = 0
    avg_degree: float = 0.0
    top_terms: List[Tuple[str, int]] = Field(default_factory=list, description="度数最高的术语")


class ExpansionResult(BaseModel):
    """图扩展结果。"""
    seed_term: str = ""
    expanded_terms: List[str] = Field(default_factory=list)
    related_chunks: List[str] = Field(default_factory=list)
    hops_used: int = 0
    trace: dict = Field(default_factory=dict)


# 常见技术关键词白名单 (用于补充正则可能遗漏的技术术语)
TECH_KEYWORDS = {
    "retriever", "retrieval", "embedding", "reranker", "rerank",
    "chunk", "chunker", "planner", "evaluator", "composer",
    "generator", "judge", "guardrail", "repair", "router",
    "rag", "graph", "hybrid", "dense", "sparse",
    "faithfulness", "relevance", "citation", "hallucination",
    "context", "evidence", "trace", "token", "latency",
}


class LightweightGraphIndex:
    """轻量级术语图索引。"""

    def __init__(self):
        self.term_to_chunks: Dict[str, Set[str]] = defaultdict(set)
        self.chunk_to_terms: Dict[str, Set[str]] = defaultdict(set)
        self.term_graph: Dict[str, Set[str]] = defaultdict(set)
        # 带权重的边: (t1, t2) -> 共现次数
        self._edge_weights: Dict[Tuple[str, str], int] = defaultdict(int)
        self._built = False

    def build(self, chunks: List[dict]):
        """从 chunk 列表构建术语图索引。

        步骤:
        1. 抽取每个 chunk 的技术术语
        2. 建立 term→chunk 和 chunk→term 映射
        3. 通过 co-occurrence 建立带权重的 term→related_term 图
        """
        self.term_to_chunks.clear()
        self.chunk_to_terms.clear()
        self.term_graph.clear()
        self._edge_weights.clear()

        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", "")
            text = chunk.get("text", chunk.get("raw_text", ""))
            terms = self.extract_terms(text)

            for term in terms:
                self.term_to_chunks[term].add(chunk_id)
                self.chunk_to_terms[chunk_id].add(term)

        # 构建 co-occurrence 图
        for chunk_id, terms in self.chunk_to_terms.items():
            terms_list = sorted(terms)  # 排序确保 (t1,t2) 和 (t2,t1) 一致
            for i in range(len(terms_list)):
                for j in range(i + 1, len(terms_list)):
                    t1, t2 = terms_list[i], terms_list[j]
                    self.term_graph[t1].add(t2)
                    self.term_graph[t2].add(t1)
                    key = (t1, t2) if t1 < t2 else (t2, t1)
                    self._edge_weights[key] += 1

        self._built = True

    def extract_terms(self, text: str) -> List[str]:
        """从文本中抽取技术术语。

        规则 (按优先级):
        1. CamelCase: AnswerJudge, RepairRouter, ContextPlanner
        2. snake_case: failure_type, repair_action, context_budget
        3. UPPERCASE 缩写: BM25, RAG, LLM, API
        4. dashed-case: cross-encoder, self-reflection
        5. 方括号引用: [D1-C012]
        6. 技术关键词白名单匹配
        """
        if not text:
            return []

        terms = set()

        # CamelCase
        camel = re.findall(r'[A-Z][a-z]+(?:[A-Z][a-z]+)+', text)
        terms.update(camel)

        # snake_case
        snake = re.findall(r'\b[a-z]+(?:_[a-z]+)+\b', text)
        terms.update(snake)

        # UPPERCASE abbreviations (2-6 字母, 可含数字: BM25, B2B, K8s)
        upper = re.findall(r'\b[A-Z][A-Z0-9]{1,5}\b', text)
        terms.update(upper)

        # dashed-case
        dashed = re.findall(r'\b[a-z]+(?:-[a-z]+)+\b', text)
        terms.update(dashed)

        # 引用括号中的术语: [D1-C012] → 提取 D1-C012
        refs = re.findall(r'\[([A-Za-z0-9_-]+-C\d+)\]', text)
        terms.update(refs)

        # 技术关键词白名单匹配 (整词匹配)
        text_lower = text.lower()
        for kw in TECH_KEYWORDS:
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                terms.add(kw)

        # 过滤: 去掉太短或太长的
        terms = {t for t in terms if 2 <= len(t) <= 40}

        return sorted(terms)

    def expand(self, term: str, max_hops: int = 1) -> ExpansionResult:
        """从给定术语出发，沿 term graph 做 BFS 扩展。

        Args:
            term: 起始术语
            max_hops: 最大跳数 (1=直接关联, 2=关联的关联)

        Returns:
            ExpansionResult: 包含 expanded_terms, related_chunks, trace
        """
        if not term or term not in self.term_graph:
            # 术语不在图中，尝试模糊匹配
            fuzzy_match = self._fuzzy_match(term)
            if fuzzy_match:
                term = fuzzy_match
            else:
                return ExpansionResult(
                    seed_term=term,
                    trace={"status": "term_not_found", "term": term},
                )

        visited_terms = set()
        current_terms = {term}
        related_chunks = set()
        expansion_path = []

        for hop in range(max_hops):
            next_terms = set()
            for t in current_terms:
                if t in visited_terms:
                    continue
                visited_terms.add(t)

                # 获取相关术语，按边权排序 (共现越多越优先)
                neighbors = self.term_graph.get(t, set())
                weighted_neighbors = []
                for nb in neighbors:
                    key = (t, nb) if t < nb else (nb, t)
                    weight = self._edge_weights.get(key, 1)
                    weighted_neighbors.append((nb, weight))
                weighted_neighbors.sort(key=lambda x: x[1], reverse=True)

                # 记录扩展路径
                expansion_path.append({
                    "hop": hop + 1,
                    "from_term": t,
                    "to_terms": [nb for nb, _ in weighted_neighbors[:10]],
                    "to_count": len(weighted_neighbors),
                })

                next_terms.update(neighbors)
                related_chunks.update(self.term_to_chunks.get(t, set()))

            current_terms = next_terms
            if not current_terms:
                break

        expanded = sorted(visited_terms - {term})

        return ExpansionResult(
            seed_term=term,
            expanded_terms=expanded,
            related_chunks=sorted(related_chunks),
            hops_used=max_hops,
            trace={
                "status": "ok",
                "seed": term,
                "expanded_count": len(expanded),
                "chunks_count": len(related_chunks),
                "expansion_path": expansion_path,
            },
        )

    def expand_multi(self, terms: List[str], max_hops: int = 1) -> ExpansionResult:
        """从多个术语出发做扩展，合并结果。"""
        all_expanded = set()
        all_chunks = set()
        all_traces = []

        for t in terms:
            result = self.expand(t, max_hops=max_hops)
            all_expanded.update(result.expanded_terms)
            all_chunks.update(result.related_chunks)
            all_traces.append(result.trace)

        return ExpansionResult(
            seed_term=", ".join(terms[:3]),
            expanded_terms=sorted(all_expanded),
            related_chunks=sorted(all_chunks),
            hops_used=max_hops,
            trace={"seeds": terms, "expanded_count": len(all_expanded), "chunks_count": len(all_chunks)},
        )

    def _fuzzy_match(self, term: str) -> Optional[str]:
        """模糊匹配: 大小写不敏感匹配图中的术语。"""
        term_lower = term.lower()
        for existing_term in self.term_graph:
            if existing_term.lower() == term_lower:
                return existing_term
        return None

    def get_stats(self) -> GraphStats:
        """获取图统计信息。"""
        total_terms = len(self.term_graph)
        total_edges = sum(len(v) for v in self.term_graph.values()) // 2  # 无向图
        avg_degree = (sum(len(v) for v in self.term_graph.values()) / total_terms) if total_terms > 0 else 0.0

        # 度数最高的术语
        degree_map = {t: len(neighbors) for t, neighbors in self.term_graph.items()}
        top_terms = sorted(degree_map.items(), key=lambda x: x[1], reverse=True)[:10]

        return GraphStats(
            total_terms=total_terms,
            total_chunks_indexed=len(self.chunk_to_terms),
            total_edges=total_edges,
            avg_degree=round(avg_degree, 2),
            top_terms=[(t, d) for t, d in top_terms],
        )

    def save(self, path: str):
        """持久化图索引到 JSON。"""
        data = {
            "term_to_chunks": {k: sorted(v) for k, v in self.term_to_chunks.items()},
            "chunk_to_terms": {k: sorted(v) for k, v in self.chunk_to_terms.items()},
            "term_graph": {k: sorted(v) for k, v in self.term_graph.items()},
            "edge_weights": {f"{k[0]}|{k[1]}": v for k, v in self._edge_weights.items()},
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> bool:
        """从 JSON 加载图索引。"""
        if not os.path.exists(path):
            return False
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.term_to_chunks = defaultdict(set, {k: set(v) for k, v in data.get("term_to_chunks", {}).items()})
        self.chunk_to_terms = defaultdict(set, {k: set(v) for k, v in data.get("chunk_to_terms", {}).items()})
        self.term_graph = defaultdict(set, {k: set(v) for k, v in data.get("term_graph", {}).items()})

        # 加载边权重
        self._edge_weights.clear()
        for key_str, weight in data.get("edge_weights", {}).items():
            parts = key_str.split("|")
            if len(parts) == 2:
                self._edge_weights[(parts[0], parts[1])] = weight

        self._built = True
        return True
