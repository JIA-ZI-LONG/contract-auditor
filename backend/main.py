"""
FastAPI 主应用

演示 LangGraph 与 FastAPI 集成：
- 使用 SSE (Server-Sent Events) 推送进度
- LangGraph stream() 与 SSE 结合
- 保留原有 API 接口
"""

import os
import json
import uuid
import tempfile
import logging
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from graph.graph import stream_audit, invoke_audit
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="税务合同审阅助手",
    description="基于 LangChain/LangGraph 的税务合同审阅系统",
    version="2.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ SSE 流式处理 ============

async def process_contract_stream(file_path: str, filename: str):
    """
    使用 LangGraph streaming 处理合同并通过 SSE 推送进度

    演示 LangGraph stream 与 SSE 集成：
    - stream_audit() 返回节点更新事件
    - 转换为 SSE 格式推送给前端
    - 实时显示处理进度
    """
    thread_id = str(uuid.uuid4())

    def sse_event(stage: str, current: int, total: int, section: str = "", **extra):
        """生成 SSE 事件格式"""
        data = {
            "stage": stage,
            "current": current,
            "total": total,
            "section": section,
            **extra
        }
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    try:
        # 发送开始事件
        yield sse_event("start", 0, 0, "正在启动审阅...")

        # 流式执行 LangGraph
        async for event in stream_audit(file_path, thread_id):
            # event 格式: {node_name: state_update}
            node_name = list(event.keys())[0]
            state_update = event[node_name]

            logger.info(f"节点 [{node_name}] 完成")

            # 根据不同节点生成不同的 SSE 事件
            if node_name == "parse":
                sections = state_update.get("sections", [])
                yield sse_event(
                    "parsed",
                    0,
                    len(sections),
                    f"解析完成，共 {len(sections)} 个章节"
                )

            elif node_name == "extract_keywords":
                idx = state_update.get("current_section_idx", 0)
                # 注意：extract_keywords 不更新 idx，需要从之前的 state 获取
                yield sse_event(
                    "extracting",
                    0,
                    0,
                    "正在提取关键词..."
                )

            elif node_name == "judge":
                # 获取刚完成的审计结果
                audit_results = state_update.get("audit_results", [])
                if audit_results:
                    last_result = audit_results[-1]
                    yield sse_event(
                        "analyzing",
                        len(audit_results),
                        0,  # total 在 accumulate 后才知道
                        last_result.get("section_name", ""),
                        risk_level=last_result.get("risk_level", "")
                    )

            elif node_name == "accumulate":
                idx = state_update.get("current_section_idx", 0)
                # 我们需要知道总章节数，这在 parse 阶段设置
                # 由于 state_update 只包含当前节点更新，这里简化处理
                yield sse_event(
                    "progress",
                    idx,
                    0,
                    f"已完成 {idx} 个章节"
                )

            elif node_name == "summary":
                summary = state_update.get("summary", "")
                yield sse_event(
                    "summary",
                    0,
                    0,
                    "摘要生成完成",
                    summary=summary[:100] + "..."
                )

            elif node_name == "report":
                report_path = state_update.get("report_path", "")
                yield sse_event(
                    "done",
                    0,
                    0,
                    filename,
                    report_path=report_path
                )

            # 短暂延迟，让前端有时间处理
            await asyncio.sleep(0.05)

    except Exception as e:
        logger.error(f"处理合同出错: {e}", exc_info=True)
        yield sse_event("error", 0, 0, str(e))


# ============ API 端点 ============

@app.post("/api/upload-stream")
async def upload_contract_stream(file: UploadFile = File(...)):
    """
    上传合同进行审阅，通过 SSE 返回进度和结果

    演示流式 API 设计：
    - 返回 StreamingResponse
    - media_type="text/event-stream" 启用 SSE
    - 客户端通过 EventSource 接收
    """
    logger.info(f"收到文件: {file.filename}")

    # 验证文件类型
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="只支持 docx 格式文件")

    # 保存临时文件
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp:
        content = await file.read()
        temp.write(content)
        temp_path = temp.name

    return StreamingResponse(
        process_contract_stream(temp_path, file.filename),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        }
    )


@app.get("/api/download/{filename}")
async def download_report(filename: str):
    """下载审阅报告"""
    report_path = os.path.join(os.getcwd(), "审阅报告.docx")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="报告不存在")

    return FileResponse(
        path=report_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename
    )


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "version": "2.0.0",
        "framework": "LangChain + LangGraph"
    }


# ============ 启动配置 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.backend_port)