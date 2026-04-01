import os
import tempfile
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from services.contract_parser import ContractParser
from services.mcp_client import MCPClient
from services.ai_analyzer import AIAnalyzer
from services.report_generator import ReportGenerator
from models.schemas import AuditReport, SectionAuditResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="税务合同审计助手", version="1.0.0")

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


@app.post("/api/upload")
async def upload_contract(file: UploadFile = File(...)):
    """
    上传合同进行审计

    Args:
        file: docx合同文件

    Returns:
        审计报告docx文件
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

    try:
        # 1. 解析合同
        sections = parser.parse(temp_path)
        logger.info(f"Parsed {len(sections)} sections")

        # 2. 逐章节分析
        audit_results = []
        for section in sections:
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

        # 3. 生成摘要
        high_risk_count = sum(1 for r in audit_results if r.risk_level == "高风险")
        non_compliant_count = sum(1 for r in audit_results if r.risk_level == "不合规")

        summary = f"共审计{len(audit_results)}个章节，"
        if non_compliant_count > 0:
            summary += f"{non_compliant_count}个不合规条款需立即整改，"
        if high_risk_count > 0:
            summary += f"{high_risk_count}个高风险条款需要关注。"
        else:
            summary += "整体合规性良好。"

        # 4. 生成报告
        report = AuditReport(sections=audit_results, summary=summary)
        report_path = report_generator.generate(report, "审计报告.docx")

        # 5. 返回文件
        return FileResponse(
            path=report_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="审计报告.docx"
        )

    finally:
        # 清理临时文件
        os.unlink(temp_path)


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from config import settings
    uvicorn.run(app, host="0.0.0.0", port=settings.backend_port)