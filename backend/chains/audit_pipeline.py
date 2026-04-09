# backend/chains/audit_pipeline.py

"""
审阅流水线 Pipeline

演示 RunnableLambda：
- 将异步函数包装为 Runnable
- 自动获得 ainvoke/abatch 等方法
- 简单 for 循环替代 LangGraph 条件路由
"""

from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from models.schemas import AuditReport, SectionAuditResult
from tools.parse_contract import parse_contract
from tools.search_regulations import search_regulations
from chains.keyword_chain import keyword_chain
from chains.judge_chain import judge_chain
from chains.llm import get_llm
from chains.prompts import SUMMARY_PROMPT
from services.report_generator import ReportGenerator


def format_regulations(regulations: list) -> str:
    """格式化法规列表为文本"""
    if not regulations:
        return "未找到相关法规"
    return "\n".join([
        f"{i+1}. {r['title']}\n   {r['content'][:300]}"
        for i, r in enumerate(regulations)
    ])


async def generate_summary(results: list) -> str:
    """生成审阅摘要"""
    compliant_count = sum(1 for r in results if r.risk_level == "合规")
    high_risk_count = sum(1 for r in results if r.risk_level == "高风险")
    non_compliant_count = sum(1 for r in results if r.risk_level == "不合规")

    summary_text = f"""
    共审阅 {len(results)} 个章节：
    - 合规条款: {compliant_count} 个
    - 高风险条款: {high_risk_count} 个
    - 不合规条款: {non_compliant_count} 个
    """

    summary_chain = SUMMARY_PROMPT | get_llm() | StrOutputParser()
    return await summary_chain.ainvoke({"audit_results_summary": summary_text})


async def audit_contract(input: dict) -> dict:
    """
    审阅合同核心逻辑

    Args:
        input: {"file_path": "合同文件路径"}

    Returns:
        {"report_path": "报告路径", "report": AuditReport}
    """
    file_path = input["file_path"]

    # 1. 解析合同
    sections = parse_contract.invoke(file_path)

    # 2. 逐章节处理
    results = []
    for section in sections:
        # 关键词提取
        keywords = await keyword_chain.ainvoke({"clause": section["content"]})

        # 法规搜索
        regulations = await search_regulations.ainvoke({
            "query_text": " ".join(keywords.keywords),
            "size": 10
        })

        # 格式化法规文本
        reg_text = format_regulations(regulations)

        # 合规判定
        judgment = await judge_chain.ainvoke({
            "clause": section["content"],
            "regulations": reg_text
        })

        # 构建结果
        results.append(SectionAuditResult(
            section_name=section["section_name"],
            original_content=section["content"],
            risk_level=judgment.risk_level,
            violated_regulations=judgment.violated_regulations,
            reason=judgment.reason,
            suggestion=judgment.suggestion
        ))

    # 3. 生成摘要
    summary = await generate_summary(results)

    # 4. 生成报告
    report = AuditReport(sections=results, summary=summary)
    report_path = ReportGenerator().generate(report, "审阅报告.docx")

    return {"report_path": report_path, "report": report}


# 包装为 Runnable
audit_pipeline = RunnableLambda(audit_contract)

# 使用方式：
# result = await audit_pipeline.ainvoke({"file_path": "contract.docx"})
# results = await audit_pipeline.abatch([{"file_path": "1.docx"}, {"file_path": "2.docx"}])