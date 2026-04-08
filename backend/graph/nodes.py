"""
LangGraph 节点函数

演示 StateGraph 节点模式：
- 每个节点是一个函数，接收 state，返回 state 更新
- 节点之间通过 state 传递数据
- LLM 节点使用 with_structured_output 实现可靠解析
"""

import logging
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from graph.state import AuditState
from graph.tools import parse_contract, search_regulations
from graph.prompts import KEYWORD_PROMPT, COMPLIANCE_PROMPT, SUMMARY_PROMPT
from models.schemas import KeywordOutput, ComplianceJudgment, SectionAuditResult
from services.report_generator import ReportGenerator
from config import settings

logger = logging.getLogger(__name__)

# ============ LLM 初始化 ============

def get_llm():
    """
    获取配置好的 LLM 实例

    演示 ChatOpenAI 自定义 base_url：
    - 支持任意 OpenAI 兼容 API
    - 通过 api_key 和 base_url 配置
    """
    return ChatOpenAI(
        model=settings.bailian_model,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.bailian_base_url,
        temperature=0.3
    )


# ============ 节点函数 ============

def parse_node(state: AuditState) -> Dict[str, Any]:
    """
    解析合同节点

    演示工具调用节点：
    - 不使用 LLM，直接调用工具函数
    - 返回 state 更新字典
    """
    logger.info("=== 节点: parse ===")

    file_path = state["file_path"]
    sections = parse_contract.invoke({"file_path": file_path})

    logger.info(f"解析完成: {len(sections)} 个章节")

    return {
        "sections": sections,
        "current_section_idx": 0,
        "audit_results": []  # 初始化空列表
    }


def extract_keywords_node(state: AuditState) -> Dict[str, Any]:
    """
    关键词提取节点

    演示 LLM 结构化输出：
    - with_structured_output 绑定 Pydantic Schema
    - 自动解析 JSON 为 Python 对象
    """
    logger.info("=== 节点: extract_keywords ===")

    idx = state["current_section_idx"]
    section = state["sections"][idx]
    clause = section["content"]

    # 使用结构化输出
    llm = get_llm()
    llm_with_schema = llm.with_structured_output(KeywordOutput)

    # 生成 prompt 并调用
    prompt = KEYWORD_PROMPT.format(clause=clause)
    result: KeywordOutput = llm_with_schema.invoke(prompt)

    keywords = result.keywords
    logger.info(f"章节 [{section['section_name']}] 关键词: {keywords}")

    return {"keywords": keywords}


def search_node(state: AuditState) -> Dict[str, Any]:
    """
    法规搜索节点

    演示 ToolNode 模式（手动调用）：
    - 调用 search_regulations 工具
    - 将结果存入 state
    """
    logger.info("=== 节点: search ===")

    keywords = state["keywords"]
    query_text = " ".join(keywords)

    # 调用搜索工具
    regulations = search_regulations.invoke({
        "query_text": query_text,
        "size": 10
    })

    logger.info(f"搜索到 {len(regulations)} 条法规")

    return {"regulations": regulations}


def judge_node(state: AuditState) -> Dict[str, Any]:
    """
    合规判定节点

    演示复杂结构化输出：
    - 使用 Literal 类型约束枚举值
    - 嵌套列表结构
    """
    logger.info("=== 节点: judge ===")

    idx = state["current_section_idx"]
    section = state["sections"][idx]
    clause = section["content"]
    regulations = state["regulations"]

    # 格式化法规文本
    reg_text = "\n".join([
        f"{i+1}. {r['title']}\n   {r['content'][:300]}"
        for i, r in enumerate(regulations)
    ]) if regulations else "未找到相关法规"

    # 使用结构化输出
    llm = get_llm()
    llm_with_schema = llm.with_structured_output(ComplianceJudgment)

    prompt = COMPLIANCE_PROMPT.format(clause=clause, regulations=reg_text)
    result: ComplianceJudgment = llm_with_schema.invoke(prompt)

    logger.info(f"章节 [{section['section_name']}] 判定: {result.risk_level}")

    # 构建审计结果
    audit_result = {
        "section_name": section["section_name"],
        "original_content": clause,
        "risk_level": result.risk_level,
        "violated_regulations": result.violated_regulations,
        "reason": result.reason,
        "suggestion": result.suggestion
    }

    return {"audit_results": [audit_result]}  # 列表形式，配合 Annotated add


def accumulate_node(state: AuditState) -> Dict[str, Any]:
    """
    累积节点 - 推进索引

    演示状态更新节点：
    - 简单的计数器推进
    - 不涉及 LLM 调用
    """
    logger.info("=== 节点: accumulate ===")

    idx = state["current_section_idx"]
    total = len(state["sections"])

    new_idx = idx + 1
    logger.info(f"进度: {new_idx}/{total}")

    return {"current_section_idx": new_idx}


def summary_node(state: AuditState) -> Dict[str, Any]:
    """
    摘要生成节点

    演示 LLM 摘要生成：
    - 根据审阅结果生成总结
    - 不使用结构化输出，直接生成文本
    """
    logger.info("=== 节点: summary ===")

    audit_results = state["audit_results"]

    # 统计风险等级
    compliant_count = sum(1 for r in audit_results if r["risk_level"] == "合规")
    high_risk_count = sum(1 for r in audit_results if r["risk_level"] == "高风险")
    non_compliant_count = sum(1 for r in audit_results if r["risk_level"] == "不合规")

    # 使用 LLM 生成摘要
    llm = get_llm()

    results_summary = f"""
    共审阅 {len(audit_results)} 个章节：
    - 合规条款: {compliant_count} 个
    - 高风险条款: {high_risk_count} 个
    - 不合规条款: {non_compliant_count} 个
    """

    prompt = SUMMARY_PROMPT.format(audit_results_summary=results_summary)
    summary = llm.invoke(prompt).content

    logger.info(f"摘要生成完成")

    return {"summary": summary}


def report_node(state: AuditState) -> Dict[str, Any]:
    """
    报告生成节点

    演示非 LLM 节点：
    - 调用外部服务生成文档
    - 作为流程终点
    """
    logger.info("=== 节点: report ===")

    # 构建报告数据
    from models.schemas import AuditReport, SectionAuditResult

    audit_results = [
        SectionAuditResult(**r) for r in state["audit_results"]
    ]

    report = AuditReport(
        sections=audit_results,
        summary=state["summary"]
    )

    # 生成报告
    generator = ReportGenerator()
    report_path = generator.generate(report, "审阅报告.docx")

    logger.info(f"报告生成完成: {report_path}")

    return {"report_path": report_path}


# ============ 条件路由函数 ============

def should_continue(state: AuditState) -> str:
    """
    条件路由：判断是否继续处理下一个章节

    演示条件边模式：
    - 返回路由目标节点名称
    - 在 graph.py 中映射到具体节点
    """
    idx = state["current_section_idx"]
    total = len(state["sections"])

    if idx < total:
        return "process_next"
    else:
        return "summary"