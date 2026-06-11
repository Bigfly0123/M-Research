"""
Citation Guardrails: 引用可靠性护栏 (指南模块09)。

三层检查: existence(格式) / alignment(来源) / support(长句引用支撑)。
完全无引用或引用全部不存在 → block; 有无效引用或未引用声明 → repair; 全通过 → pass。
"""

import re
import time
from typing import List, Literal, Optional
from pydantic import BaseModel
from app.config import config


class CitationGuardResult(BaseModel):
    pass_: bool = True
    decision: Literal["PASS", "SOFT_WARN", "HARD_FAIL"] = "PASS"
    invalid_citations: List[str] = []
    unsupported_claims: List[str] = []
    action: Literal["pass", "repair", "block"] = "pass"
    reason: str = ""


class GuardrailOutput(BaseModel):
    status: Literal["ok", "warn", "fail"] = "ok"
    result: Optional[CitationGuardResult] = None
    trace: dict = {}
    next_action: Optional[str] = None


CITATION_PATTERN = re.compile(r'\[.+?-s\d+-c\d+\]')


def check_existence(answer: str) -> List[str]:
    """第一层: 引用格式是否正确 [Dx-Cyyy]。"""
    return CITATION_PATTERN.findall(answer)


def check_alignment(found_citations: List[str], valid_ids: set) -> List[str]:
    """第二层: 引用是否存在于 context_pack 的 citation_id 中。"""
    return [cid for cid in found_citations if cid.strip("[]") not in valid_ids]


def check_support(answer: str, min_length: int = 40) -> List[str]:
    """第三层: 长句子(>40字)是否有引用支撑 (规则版，不依赖LLM)。"""
    sentences = re.split(r'[.!?。！？]', answer)
    uncited = []
    for s in sentences:
        stripped = s.strip()
        if len(stripped) > min_length and not CITATION_PATTERN.search(stripped):
            uncited.append(stripped)
    return uncited


def check_citations(answer: str, context_pack: List[dict]) -> GuardrailOutput:
    """三层引用检查入口。"""
    start = time.time()

    if not answer:
        return GuardrailOutput(
            status="fail",
            result=CitationGuardResult(
                pass_=False,
                action="block",
                reason="答案为空",
            ),
            trace={
                "module": "CitationGuardrails",
                "total_citations": 0,
                "invalid_count": 0,
                "uncited_count": 0,
                "action": "block",
                "fallback_used": False,
                "latency_ms": int((time.time() - start) * 1000),
            },
            next_action="repair",
        )

    valid_ids = {item.get("citation_id", "") for item in context_pack}

    found = check_existence(answer)
    invalid = check_alignment(found, valid_ids)
    uncited = check_support(answer)

    total_citations = len(found)
    invalid_count = len(invalid)
    uncited_count = len(uncited)

    pass_ = True
    decision: Literal["PASS", "SOFT_WARN", "HARD_FAIL"] = "PASS"
    action: Literal["pass", "repair", "block"] = "pass"
    reason = ""

    if total_citations == 0:
        pass_ = False
        decision = "HARD_FAIL"
        action = "block"
        reason = "完全无引用"
    elif invalid_count == total_citations:
        pass_ = False
        decision = "HARD_FAIL"
        action = "block"
        reason = "引用全部不存在于 context_pack"
    elif invalid_count > 0:
        # 有无效引用 → HARD_FAIL
        pass_ = False
        decision = "HARD_FAIL"
        action = "repair"
        reason = f"存在{invalid_count}个无效引用"
    elif uncited_count > 0 and total_citations > 0:
        # 有有效引用但部分长句子未引用 → SOFT_WARN (不 repair)
        pass_ = True  # 不触发 repair
        decision = "SOFT_WARN"
        action = "pass"
        reason = f"存在{uncited_count}个未引用长句，但有有效引用"

    latency = int((time.time() - start) * 1000)

    trace = {
        "module": "CitationGuardrails",
        "total_citations": total_citations,
        "invalid_count": invalid_count,
        "uncited_count": uncited_count,
        "action": action,
        "fallback_used": False,
        "latency_ms": latency,
    }

    next_action = None
    if action == "block":
        next_action = "repair"
    elif action == "repair":
        next_action = "repair"
    # SOFT_WARN 不触发 next_action

    return GuardrailOutput(
        status="ok",
        result=CitationGuardResult(
            pass_=pass_,
            decision=decision,
            invalid_citations=invalid,
            unsupported_claims=uncited[:5],
            action=action,
            reason=reason,
        ),
        trace=trace,
        next_action=next_action,
    )


def run_from_state(state: dict) -> dict:
    """从 AgentState 取输入，执行引用护栏检查，返回 state 更新。"""
    answer = state.get("answer", "")
    context_pack = state.get("context_pack", [])

    output = check_citations(answer, context_pack)

    if output.result is None:
        return {
            "guardrail_result": {},
            "guardrail_pass": False,
            "trace": [{"node": "guardrails", "output": "fail", "latency_ms": output.trace.get("latency_ms", 0)}],
        }

    return {
        "guardrail_result": output.result.model_dump(),
        "guardrail_pass": output.result.pass_,
        "trace": [{"node": "guardrails", "output": f"action={output.result.action}, reason={output.result.reason}", "latency_ms": output.trace.get("latency_ms", 0)}],
    }
