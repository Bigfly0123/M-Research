import json
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import exc
from app.utils.llm import get_llm
from app.graph.state import AgentState

"""
================================================================================
【学习指南】reviewer.py - 质量审查员
================================================================================

📚 核心概念:
Reviewer 是整个工作流的"审核员",负责检查 Writer 生成的报告是否充分回答了用户的问题,
质量是否合格。这是 Agentic Workflow 实现自我修正的核心机制。

🎯 为什么需要 Reviewer?
1. 质量控制: 避免低质量报告直接输出给用户
2. 自我修正: FAIL 时回到 planner 重新规划,形成"生成-审查-修正"循环
3. 防幻觉: 通过审查发现编造的内容,要求补充真实证据

💡 类比理解:
想象论文投稿流程:
- Writer 写完论文提交
- Reviewer (审稿人)检查:
  ├─ 是否回答了研究问题? → PASS
  └─ 缺少实验数据 → FAIL,返回修改意见
- 作者根据意见修改后重新提交

🔑 关键函数说明:

1. _clean_json_text(s: str) -> str:
   - 作用: 清理 LLM 输出的 JSON 字符串
   - 逻辑: 移除 Markdown 代码块标记(```json),提取 {} 之间的内容
   - 场景: LLM 经常不按格式输出,需要容错处理

2. review_node(state: AgentState) -> Dict:
   - 作用: 审查报告质量,给出通过/不通过的判定
   - 输入: state["query"] (用户问题) + state["final_report"] (待审查报告)
   - 输出: {"critique": str, "revision_number": int, "review_status": str}
   
   - 工作流程:
     Step 1: 构造 Prompt,包含用户问题和报告内容
     Step 2: 调用 LLM 进行审查,要求返回 JSON 格式
             {
               "status": "PASS" 或 "FAIL",
               "feedback": "改进建议"
             }
     Step 3: 清理并解析 JSON
     Step 4: 如果解析失败,重试一次
     Step 5: 如果仍然失败,使用兜底策略(强制 FAIL)
     Step 6: 返回审查结果,revision_number +1
   
   - JSON 解析容错机制:
     * 第一次尝试: 直接解析 LLM 输出
     * 第二次尝试: 构造重试 Prompt,要求只输出一行合法 JSON
     * 兜底策略: 如果两次都失败,返回强制 FAIL,避免系统崩溃
   
   - 典型场景:
     * 场景1: 报告质量合格
       → status="PASS", feedback="", revision_number+1
       → graph.py 中 should_continue 返回 END
     
     * 场景2: 报告缺少关键信息
       → status="FAIL", feedback="缺少对 Multi-Agent 协作模式的讨论"
       → graph.py 中 should_continue 返回 planner,带着 critique 重新规划
     
     * 场景3: LLM 输出格式错误
       → 重试一次 → 仍失败 → 兜底 FAIL

🎓 学习要点:
1. 结构化输出: 要求 LLM 返回 JSON,便于程序化处理
2. 多层容错: 清理 → 解析 → 重试 → 兜底,保证系统稳定性
3. 反馈驱动: critique 作为下一轮规划的输入,实现针对性改进
4. 循环控制: revision_number 防止无限循环(最多 3 次)
5. 严格性: temperature=0,要求绝对理性,不要创造力

⚠️ 注意事项:
- LLM 可能不按要求输出 JSON,必须有完善的容错机制
- feedback 应该具体明确,如"缺少案例分析",而不是"质量不好"
- 可以根据实际需求调整最大重试次数(当前是 3)

🔗 与其他模块的关系:
- graph.py: reviewer → [should_continue] → planner(FAIL) 或 END(PASS)
- writer.py: 提供 final_report 供审查
- planner.py: 接收 critique,指导下一次规划
================================================================================
"""

llm = get_llm(model_type="smart")


REVIEW_PROMPT = ChatPromptTemplate.from_template(
    """你是一个严厉的审核员。
    请检查以下报告是否充分回答了用户的问题：{query}
    
    报告内容：
    {report}
    
    请严格按照以下 JSON 格式返回结果（不要包含 Markdown 代码块）：
    {{
        "status": "PASS" 或 "FAIL",
        "feedback": "如果是 PASS，这里留空。如果是 FAIL，请列出 1 个具体的改进建议或需要补充搜索的方向。"
    }}
    """
)

def _clean_json_text(s: str) -> str:
    """清理 LLM 输出的 JSON 字符串:移除 Markdown 代码块标记,提取 {} 之间的内容。"""
    s = (s or "").strip()
    s = s.replace("```json", "").replace("```", "").strip()
    l = s.find("{")
    r = s.rfind("}")
    if l != -1 and r != -1 and r > l:
        s = s[l:r+1]
    return s

def review_node(state: AgentState):
    """
    质量审查节点:审查报告质量,给出通过/不通过的判定
    
    检查 Writer 生成的报告是否充分回答了用户的问题,质量是否合格。
    
    参数:
    - state: 当前的 AgentState,包含 query、final_report 和 revision_number
    
    返回:
    - {"critique": str, "revision_number": int, "review_status": str}
    
    工作流程:
    1. 构造 Prompt,包含用户问题和报告内容
    2. 调用 LLM 进行审查,要求返回 JSON 格式
    3. 清理并解析 JSON
    4. 如果解析失败,重试一次
    5. 如果仍然失败,使用兜底策略(强制 FAIL)
    6. 返回审查结果,revision_number +1
    """
    print("--- [节点] 正在审查报告质量 ---")
    query = state["query"]
    report = state["final_report"]

    num = state.get("revision_number", 0)
    

    response = llm.invoke(REVIEW_PROMPT.format(query=query, report=report))
    raw = response.content
    content = _clean_json_text(raw)
    
    result = None
    try:
        result = json.loads(content)
    except Exception as e1:
        retry_prompt = f'''
        你刚才的输出无法被 JSON 解析。
        请只输出一行合法 JSON，不要 Markdown，不要解释：
        {{"status":"PASS"或"FAIL","feedback":"PASS留空，FAIL给1条具体建议"}}

        用户问题：{query}
        报告：{report}
        '''
        retry_raw = llm.invoke(retry_prompt).content
        retry_content = _clean_json_text(retry_raw)
        try:
            result = json.loads(retry_content)
        except Exception as e2:
            # 兜底策略
            print(f"--- [Reviewer][WARN] JSON解析失败，fail-closed。raw={raw!r} retry_raw={retry_raw!r} ---")
            result = {
                "status": "FAIL",
                "feedback": "审查器输出格式异常（未返回合法JSON）。请按要求重写报告，并确保内容充分回答问题且结构清晰；如资料不足请明确说明并提出需要补充检索的点。"
            }

    return {
        "critique": result.get("feedback",""),
        "revision_number": num + 1,
        "review_status": result.get("status", "FAIL")
    }

# 测试函数
def test_review_node():
    """测试函数:验证 Reviewer 的功能"""
    print("\n========== [TEST] review_node ==========\n")

    # -----------------------------
    # Case 1: 正常 PASS
    # -----------------------------
    state_pass: AgentState = {
        "query": "解释一下 Beam Search 的 length penalty 如何影响生成结果？",
        "final_report": "Beam Search 是一种搜索算法，可以找到更好的句子。谢谢。"
                        "对序列中每个位置，计算它与其它位置的相关性权重，然后对 value 做加权求和，"
                        "从而在不依赖 RNN 的情况下建模长距离依赖。报告还解释了 Q/K/V 的含义与计算流程。",
        "revision_number": 0,
    }
    out1 = review_node(state_pass)
    print("[Case 1 Output]", out1)
# test_review_node()
