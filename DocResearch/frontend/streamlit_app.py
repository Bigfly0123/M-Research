"""
DocResearch-Agent 2026 - Streamlit demo page.

Usage: streamlit run frontend/streamlit_app.py
"""

import os
import sys
import json
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=r".*__path__.*", category=FutureWarning)

os.environ.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none")

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import config
from app.state import AgentState

st.set_page_config(
    page_title="DocResearch-Agent 2026",
    page_icon="",
    layout="wide",
)

st.title("DocResearch-Agent 2026")
st.caption("Context-Engineered Agentic GraphRAG for Technical Documentation QA")


def _get_retriever(index_dir: str):
    """每次都创建新的 retriever + load_index，不在 session_state 中缓存 FAISS 对象。"""
    print(f"[DEBUG] _get_retriever called, index_dir={index_dir}", flush=True)
    from app.retrieval.hybrid_retriever import HybridGraphRetriever
    retriever = HybridGraphRetriever()

    if os.path.exists(index_dir) and len(os.listdir(index_dir)) > 0:
        try:
            print(f"[DEBUG] _get_retriever: calling load_index...", flush=True)
            retriever.load_index(index_dir)
            print(f"[DEBUG] _get_retriever: load_index OK", flush=True)
        except Exception as e:
            print(f"[DEBUG] _get_retriever: load_index FAILED: {type(e).__name__}: {e}", flush=True)
            st.warning(f"Index load error: {type(e).__name__}: {e}")

    return retriever


with st.sidebar:
    st.header("Index Management")

    index_dir = st.text_input("Index directory", value=str(ROOT_DIR / "data" / "index"))
    index_loaded = os.path.exists(index_dir) and len(os.listdir(index_dir)) > 0
    print(f"[DEBUG] index_dir={index_dir}, index_loaded={index_loaded}", flush=True)

    if index_loaded:
        st.success("Index directory exists")
    else:
        st.warning("Index directory is empty, please upload docs first")

    st.markdown("---")
    st.header("Document Upload")
    uploaded_files = st.file_uploader(
        "Select documents (Markdown/TXT/PDF)",
        type=["md", "txt", "pdf"],
        accept_multiple_files=True,
    )

    upload_clicked = st.button("Upload & Build Index", disabled=not uploaded_files)
    upload_status = st.empty()
    if uploaded_files and upload_clicked:
        print(f"[DEBUG] Upload button clicked! {len(uploaded_files)} files", flush=True)
        from app.ingestion.chunker import StructureAwareChunker, ChunkerConfig
        from app.retrieval.hybrid_retriever import HybridGraphRetriever

        raw_dir = ROOT_DIR / "data" / "raw_docs"
        raw_dir.mkdir(parents=True, exist_ok=True)

        try:
            saved_paths = []
            for f in uploaded_files:
                path = raw_dir / f.name
                path.write_bytes(f.getbuffer())
                saved_paths.append(str(path))

            chunker = StructureAwareChunker(ChunkerConfig())
            result = chunker.run(saved_paths)

            print(f"[DEBUG] Chunking: status={result.status}, chunks={len(result.chunks)}", flush=True)

            if result.status == "fail" or not result.chunks:
                upload_status.error(f"Chunking failed: {result.trace}")
            else:
                chunk_dicts = [c.model_dump() for c in result.chunks]

                retriever = HybridGraphRetriever()
                retriever.build_index(chunk_dicts, index_dir=index_dir)
                print(f"[DEBUG] build_index DONE", flush=True)

                upload_status.info(f"Chunked: {result.total_chunks} chunks, Index built!")
        except Exception as e:
            print(f"[DEBUG] Upload FAILED: {type(e).__name__}: {e}", flush=True)
            upload_status.error(f"Upload/Index failed: {type(e).__name__}: {e}")

    st.markdown("---")
    st.header("Retrieval Config")
    retrieval_plan = st.multiselect(
        "Retrieval paths",
        ["dense", "bm25", "graph_expand"],
        default=["dense", "bm25", "graph_expand"],
    )
    use_rerank = st.checkbox("Use Reranker", value=True)

    st.markdown("---")
    st.caption(f"Dense backend: {config.DENSE_BACKEND}")


question = st.text_input("Enter your question", placeholder="e.g. What is StateGraph in LangGraph?")

query_clicked = st.button("Query", type="primary", disabled=not question)
if question and query_clicked:
    from app.context.context_planner import plan_context
    from app.retrieval.retrieval_evaluator import evaluate_retrieval
    from app.evidence.evidence_composer import compose_context_pack
    from app.generation.answer_generator import generate_answer
    from app.judge.self_reflection_judge import judge_answer
    from app.judge.guardrails import check_citations
    from app.repair.repair_router import route_repair

    try:
        overall_start = time.time()

        print(f"[DEBUG] Query: getting retriever...", flush=True)
        retriever = _get_retriever(index_dir)
        has_index = hasattr(retriever, 'dense') and retriever.dense.index is not None
        print(f"[DEBUG] retriever obtained, has_index={has_index}", flush=True)
        if not has_index:
            st.error("Index not loaded, please upload documents first")
            st.stop()

        with st.spinner("1/7 Context planning..."):
            plan_result = plan_context(question, use_llm=False)
            plan = plan_result.plan

        with st.spinner("2/7 Retrieving..."):
            retrieval_result = retriever.retrieve(
                question,
                retrieval_plan=retrieval_plan or plan.retrieval_plan,
                top_k=config.FINAL_TOP_K,
                use_rerank=use_rerank,
            )

        with st.spinner("3/7 Evaluating retrieval..."):
            chunks_dicts = [c.model_dump() for c in retrieval_result.chunks]
            eval_result = evaluate_retrieval(question, chunks_dicts, use_llm=False)

        with st.spinner("4/7 Composing evidence..."):
            budget = plan.context_budget if plan else config.DEFAULT_CONTEXT_BUDGET
            pack_result = compose_context_pack(chunks_dicts, question, context_budget=budget)

        with st.spinner("5/7 Generating answer..."):
            context_pack_dicts = [item.model_dump() for item in pack_result.context_pack]
            query_type = plan.query_type if plan else "concept"
            answer_result = generate_answer(question, context_pack_dicts, query_type=query_type)

        with st.spinner("6/7 Checking citations..."):
            guard_result = check_citations(answer_result.result.answer, context_pack_dicts)

        with st.spinner("7/7 Judging quality..."):
            judge_res = judge_answer(
                question, answer_result.result.answer, context_pack_dicts,
                used_citations=answer_result.result.used_citations,
            )

        overall_latency = int((time.time() - overall_start) * 1000)

        st.markdown("---")

        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("Answer")
            st.markdown(answer_result.result.answer)
        with col2:
            conf = answer_result.result.confidence
            color_map = {"high": ":green[high]", "medium": ":orange[medium]", "low": ":red[low]"}
            st.metric("Confidence", color_map.get(conf, conf))
            st.metric("Latency", f"{overall_latency} ms")
            st.metric("Context tokens", f"{pack_result.total_context_tokens}")

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Context Plan", "Retrieval", "Evidence", "Judge", "Guardrails",
        ])

        with tab1:
            if plan:
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Question type**: `{plan.query_type}`")
                c2.markdown(f"**Retrieval plan**: `{plan.retrieval_plan}`")
                c3.markdown(f"**Context budget**: `{plan.context_budget}` tokens")
                if plan.rewritten_query != question:
                    st.info(f"Rewritten query: {plan.rewritten_query}")
                if plan.judge_focus:
                    st.markdown(f"**Judge focus**: {', '.join(plan.judge_focus)}")
                if plan.expected_evidence:
                    st.markdown(f"**Expected evidence**: {', '.join(plan.expected_evidence)}")

        with tab2:
            st.markdown(f"**Status**: `{retrieval_result.status}`")
            st.markdown(f"**Source stats**: {retrieval_result.source_stats}")

            if retrieval_result.chunks:
                st.markdown("#### Top retrieved chunks")
                for i, chunk in enumerate(retrieval_result.chunks[:5]):
                    with st.expander(f"[{i+1}] {chunk.chunk_id} (score={chunk.final_score:.3f})"):
                        st.markdown(f"**Source**: {chunk.source} > {chunk.section}")
                        st.markdown(f"**Type**: {chunk.element_type}")
                        st.markdown(f"**Paths**: {chunk.retrieval_sources}")
                        st.text(chunk.text[:500])

            if "graph_expand" in (retrieval_plan or []):
                st.markdown("#### Graph Expansion")
                st.info(f"Graph path hits: {retrieval_result.source_stats.get('graph_expand', 0)} chunks")

        with tab3:
            st.markdown(f"**Evidence Pack**: {len(pack_result.context_pack)} items, {pack_result.total_context_tokens} tokens")
            st.markdown(f"**Dropped**: {len(pack_result.dropped_chunks)} chunks")

            if pack_result.context_pack:
                roles = {}
                for item in pack_result.context_pack:
                    roles[item.role] = roles.get(item.role, 0) + 1
                st.markdown(f"**Role distribution**: {roles}")

                for item in pack_result.context_pack[:5]:
                    with st.expander(f"[{item.citation_id}] role={item.role}, score={item.support_score:.2f}"):
                        st.markdown(f"**Source**: {item.source}")
                        if item.section_path:
                            st.markdown(f"**Section**: {' > '.join(item.section_path)}")
                        st.text((item.compressed_text or item.evidence_text)[:400])

        with tab4:
            jd = judge_res.result
            passed = jd.pass_
            pass_label = "PASS" if passed else "FAIL"
            st.markdown(f"**Judge result**: {pass_label}")

            dims = ["answer_relevance", "citation_support", "faithfulness", "context_sufficiency"]
            scores = {d: getattr(jd, d, 0.0) for d in dims}

            col1, col2 = st.columns(2)
            with col1:
                for d in dims[:2]:
                    v = scores[d]
                    st.progress(min(v, 1.0), text=f"{d}: {v:.2f}")
            with col2:
                for d in dims[2:]:
                    v = scores[d]
                    st.progress(min(v, 1.0), text=f"{d}: {v:.2f}")

            if not passed:
                st.error(f"**Failure type**: `{jd.failure_type}`")
                st.warning(f"**Repair action**: `{jd.repair_action}`")
                st.markdown(f"**Reason**: {jd.reason}")

        with tab5:
            gd = guard_result.result
            gp = gd.pass_
            gp_label = "PASS" if gp else "FAIL"
            st.markdown(f"**Guardrails**: {gp_label}")
            st.markdown(f"**Invalid citations**: {gd.invalid_citations}")
            st.markdown(f"**Unsupported claims**: {len(gd.unsupported_claims)}")

            if not gp:
                st.warning(f"**Action**: {gd.action}")

        st.markdown("---")
        st.subheader("Execution Trace")
        trace_data = {
            "question": question,
            "query_type": query_type,
            "retrieval_plan": retrieval_plan or (plan.retrieval_plan if plan else []),
            "retrieval_status": retrieval_result.status,
            "retrieval_source_stats": retrieval_result.source_stats,
            "evidence_pack_size": len(pack_result.context_pack),
            "context_tokens": pack_result.total_context_tokens,
            "answer_confidence": answer_result.result.confidence,
            "judge_pass": passed,
            "guardrail_pass": gp,
            "overall_latency_ms": overall_latency,
        }
        st.json(trace_data)
    except Exception as e:
        print(f"[DEBUG] Query FAILED: {type(e).__name__}: {e}", flush=True)
        st.error(f"Query pipeline failed: {type(e).__name__}: {e}")


elif not question:
    st.markdown("---")
    st.subheader("System Architecture")
    st.code(
        "Question -> Context Planner -> Tool Registry -> Hybrid + Graph Retrieval\n"
        "  -> Retrieval Evaluator -> Evidence Composer -> Grounded Answer Generator\n"
        "  -> Self-Reflection Judge + Citation Guardrails -> Repair Router\n"
        "  -> Trace Store + Eval Runner",
        language="text",
    )

    st.subheader("Module Status")
    module_items = [
        ("Context Planner", "question_type + retrieval_plan + budget"),
        ("Structure-aware Chunker", "Markdown/PDF structure-aware chunking"),
        ("Dense + BM25 Hybrid", "score fusion + rerank"),
        ("Graph Retriever", "lightweight term graph + BFS multi-hop"),
        ("Retrieval Evaluator", "evidence quality: strong/weak/irrelevant"),
        ("Evidence Composer", "dedup + role labeling + budget control"),
        ("Answer Generator", "grounded generation + rule-based self-check"),
        ("Self-Reflection Judge", "4-dim scoring + failure_type driven repair"),
        ("Citation Guardrails", "3-level check: format/alignment/support"),
        ("Repair Router", "6 failure_types with targeted repair"),
        ("Trace Store", "full-pipeline tracing JSON/JSONL"),
    ]
    for name, desc in module_items:
        st.markdown(f"- [OK] **{name}**: {desc}")

print(f"[DEBUG] === Script end ===", flush=True)
