"""
FastAPI 主应用

演示 LangChain Runnable 与 FastAPI 集成：
- 使用 ainvoke() 异步执行
- 简单 POST API（无 SSE）
"""

import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from chains.audit_pipeline import audit_pipeline
from config import settings

app = FastAPI(
    title="税务合同审阅助手",
    description="基于 LangChain 1.x LCEL 的税务合同审阅系统",
    version="3.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/upload")
async def upload_contract(file: UploadFile = File(...)):
    """
    上传合同进行审阅

    使用 audit_pipeline.ainvoke() 异步执行
    """
    # 验证文件类型
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="只支持 docx 格式文件")

    # 保存临时文件
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp:
        content = await file.read()
        temp.write(content)
        temp_path = temp.name

    # 执行审阅
    result = await audit_pipeline.ainvoke({"file_path": temp_path})

    return {"report_path": result["report_path"]}


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
        "version": "3.0.0",
        "framework": "LangChain 1.x LCEL"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.backend_port)