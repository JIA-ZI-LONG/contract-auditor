"""
LangGraph StateGraph 组装

演示 StateGraph 核心模式：
- StateGraph 创建和节点添加
- 边（edge）和条件边（conditional_edges）
- ToolNode 工具执行节点
- MemorySaver 检查点持久化
- 编译为可执行应用
"""

import logging
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from graph.state import AuditState
from graph.nodes import (
    parse_node,
    extract_keywords_node,
    search_node,
    judge_node,
    accumulate_node,
    summary_node,
    report_node,
    should_continue
)
from graph.tools import search_regulations

logger = logging.getLogger(__name__)


def build_audit_graph() -> StateGraph:
    """
    构建税务合同审阅 StateGraph

    演示 StateGraph 组装模式：
    1. 创建 StateGraph 并指定 State 类型
    2. 添加节点（普通节点和 ToolNode）
    3. 添加边（普通边和条件边）
    4. 编译应用（可选添加 checkpointer）

    流程图：
    START -> parse -> extract_keywords -> tools -> judge -> accumulate
                                                                    |
                            (条件路由: should_continue)           |
                            process_next ─────────────────────────┘
                            summary -> report -> END
    """
    # 1. 创建 StateGraph
    workflow = StateGraph(AuditState)

    # 2. 添加节点
    #    - 普通节点：直接传入函数
    #    - ToolNode：传入工具列表，自动处理工具调用
    workflow.add_node("parse", parse_node)
    workflow.add_node("extract_keywords", extract_keywords_node)
    workflow.add_node("tools", ToolNode([search_regulations]))  # ToolNode 模式
    workflow.add_node("judge", judge_node)
    workflow.add_node("accumulate", accumulate_node)
    workflow.add_node("summary", summary_node)
    workflow.add_node("report", report_node)

    # 3. 添加边

    # START -> parse: 入口边
    workflow.add_edge(START, "parse")

    # parse -> extract_keywords: 解析完成后开始关键词提取
    workflow.add_edge("parse", "extract_keywords")

    # extract_keywords -> tools: 提取关键词后调用工具搜索
    workflow.add_edge("extract_keywords", "tools")

    # tools -> judge: 搜索完成后进行合规判定
    workflow.add_edge("tools", "judge")

    # judge -> accumulate: 判定完成后累积结果
    workflow.add_edge("judge", "accumulate")

    # accumulate -> 条件路由: 根据进度决定下一步
    workflow.add_conditional_edges(
        "accumulate",
        should_continue,  # 路由函数
        {
            "process_next": "extract_keywords",  # 继续处理下一章节
            "summary": "summary"                  # 所有章节处理完成，生成摘要
        }
    )

    # summary -> report: 摘要完成后生成报告
    workflow.add_edge("summary", "report")

    # report -> END: 报告生成完成，流程结束
    workflow.add_edge("report", END)

    return workflow


def compile_audit_app():
    """
    编译审阅应用

    演示 MemorySaver 模式：
    - MemorySaver 在内存中保存状态检查点
    - 支持流程中断后恢复
    - 通过 thread_id 区分不同会话
    """
    workflow = build_audit_graph()

    # 创建内存检查点存储
    memory = MemorySaver()

    # 编译应用
    app = workflow.compile(
        checkpointer=memory,
        interrupt_before=[],  # 可选：在指定节点前中断（用于人机交互）
        interrupt_after=[]    # 可选：在指定节点后中断
    )

    logger.info("Audit graph compiled successfully")
    return app


# ============ 导出编译后的应用 ============

# 全局应用实例（单例模式）
_audit_app = None


def get_audit_app():
    """获取审阅应用实例"""
    global _audit_app
    if _audit_app is None:
        _audit_app = compile_audit_app()
    return _audit_app


# 默认导出编译后的应用
audit_app = get_audit_app()


# ============ 流式执行辅助函数 ============

async def stream_audit(file_path: str, thread_id: str = "default"):
    """
    流式执行审阅流程

    演示 LangGraph streaming 模式：
    - 使用 stream() 方法获取每个节点的输出
    - stream_mode="updates" 只返回状态更新
    - 通过 thread_id 实现会话隔离

    Args:
        file_path: 合同文件路径
        thread_id: 会话 ID（用于检查点）

    Yields:
        dict: 每个节点的状态更新
    """
    app = get_audit_app()

    # 配置检查点
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    # 输入数据
    inputs = {
        "file_path": file_path,
        "sections": [],
        "current_section_idx": 0,
        "audit_results": [],
        "regulations": [],
        "keywords": [],
        "summary": "",
        "report_path": "",
        "error": ""
    }

    # 流式执行
    for event in app.stream(inputs, config, stream_mode="updates"):
        # event 格式: {node_name: state_update}
        yield event


async def invoke_audit(file_path: str, thread_id: str = "default"):
    """
    同步执行审阅流程（等待完成）

    演示 invoke 模式：
    - 阻塞等待流程完成
    - 返回最终状态

    Args:
        file_path: 合同文件路径
        thread_id: 会话 ID

    Returns:
        AuditState: 最终状态
    """
    app = get_audit_app()

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    inputs = {
        "file_path": file_path,
        "sections": [],
        "current_section_idx": 0,
        "audit_results": [],
        "regulations": [],
        "keywords": [],
        "summary": "",
        "report_path": "",
        "error": ""
    }

    # 执行并返回最终状态
    result = await app.ainvoke(inputs, config)
    return result