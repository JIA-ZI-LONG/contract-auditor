import os
import tempfile
import logging
import json
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from services.contract_parser import ContractParser
from services.mcp_client import MCPClient
from services.ai_analyzer import AIAnalyzer
from services.report_generator import ReportGenerator
from models.schemas import AuditReport, SectionAuditResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="税务合同审阅助手", version="1.0.0")

# CORS配置（允许前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 服务实例
parser = ContractParser()
mcp_client = MCPClient()
ai_analyzer = AIAnalyzer()
report_generator = ReportGenerator()


async def process_contract_with_progress(temp_path: str, filename: str):
    """处理合同并通过SSE推送进度"""

    def progress_event(stage: str, current: int, total: int, section: str = ""):
        return f"data: {json.dumps({'stage': stage, 'current': current, 'total': total, 'section': section})}\n\n"

    try:
        # 1. 解析合同
        yield progress_event("parsing", 0, 0, "正在解析合同...")
        sections = parser.parse(temp_path)
        logger.info(f"Parsed {len(sections)} sections")
        yield progress_event("parsed", 0, len(sections), "解析完成")

        await asyncio.sleep(0.1)

        # 2. 逐章节分析
        audit_results = []
        for i, section in enumerate(sections):
            # 推送当前进度
            yield progress_event("analyzing", i + 1, len(sections), section.section_name)
            logger.info(f"Analyzing section {i + 1}/{len(sections)}: {section.section_name}")

            # 提取关键词
            keywords = await ai_analyzer.extract_keywords(section.content)
            logger.info(f"Keywords for {section.section_name}: {keywords}")

            # 搜索法规
            query_text = " ".join(keywords)
            search_result = await mcp_client.search_regulations(query_text)
            regulations = mcp_client.parse_regulations(search_result)
            logger.info(f"Found {len(regulations)} regulations for {section.section_name}")

            # 合规判定
            audit_result = await ai_analyzer.judge_compliance(
                section.content,
                [{"title": r.title, "content": r.content} for r in regulations]
            )
            audit_result.section_name = section.section_name
            audit_results.append(audit_result)

            await asyncio.sleep(0.1)

        # 3. 生成摘要
        yield progress_event("summary", len(sections), len(sections), "正在生成摘要...")
        high_risk_count = sum(1 for r in audit_results if r.risk_level == "高风险")
        non_compliant_count = sum(1 for r in audit_results if r.risk_level == "不合规")

        summary = f"共审阅{len(audit_results)}个章节，"
        if non_compliant_count > 0:
            summary += f"{non_compliant_count}个不合规条款需立即整改，"
        if high_risk_count > 0:
            summary += f"{high_risk_count}个高风险条款需要关注。"
        else:
            summary += "整体合规性良好。"

        # 4. 生成报告
        yield progress_event("generating", len(sections), len(sections), "正在生成报告...")
        report = AuditReport(sections=audit_results, summary=summary)
        report_path = report_generator.generate(report, "审阅报告.docx")

        # 5. 完成
        yield progress_event("done", len(sections), len(sections), filename)
        logger.info("Audit completed")

    except Exception as e:
        logger.error(f"Error processing contract: {e}")
        yield f"data: {json.dumps({'stage': 'error', 'message': str(e)})}\n\n"


@app.post("/api/upload-stream")
async def upload_contract_stream(file: UploadFile = File(...)):
    """
    上传合同进行审阅，通过SSE返回进度和结果

    Args:
        file: docx合同文件

    Returns:
        SSE流，包含进度和最终结果
    """
    logger.info(f"Received file: {file.filename}")

    # 验证文件类型
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="只支持docx格式文件")

    # 保存临时文件
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp:
        content = await file.read()
        temp.write(content)
        temp_path = temp.name

    return StreamingResponse(
        process_contract_with_progress(temp_path, file.filename),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
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
    return {"status": "ok"}


# 清理临时文件的异步任务
import atexit
temp_files = []

def cleanup_temp_files():
    for path in temp_files:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except:
            pass

atexit.register(cleanup_temp_files)


if __name__ == "__main__":
    import uvicorn
    from config import settings
    uvicorn.run(app, host="0.0.0.0", port=settings.backend_port)