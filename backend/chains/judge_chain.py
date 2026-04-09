# backend/chains/judge_chain.py

"""
合规判定 Chain

演示 LCEL 链式调用 + 结构化输出：
- prompt | llm 组合为 chain
- with_structured_output() 自动解析为 Pydantic 模型
"""

from chains.prompts import COMPLIANCE_PROMPT
from chains.llm import get_llm
from models.schemas import ComplianceJudgment

# LCEL chain
judge_chain = COMPLIANCE_PROMPT | get_llm().with_structured_output(ComplianceJudgment)

# 使用方式：
# 异步调用：result = await judge_chain.ainvoke({"clause": "...", "regulations": "..."})
# 返回 ComplianceJudgment(risk_level="高风险", reason="...", suggestion="...")