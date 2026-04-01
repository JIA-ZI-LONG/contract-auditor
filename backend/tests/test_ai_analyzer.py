import pytest
from services.ai_analyzer import AIAnalyzer

@pytest.mark.asyncio
async def test_extract_keywords():
    """测试关键词提取"""
    analyzer = AIAnalyzer()
    clause = "买方应在收到发票后30日内支付货款，逾期按日利率0.05%计算违约金。"

    keywords = await analyzer.extract_keywords(clause)

    assert isinstance(keywords, list)
    assert len(keywords) >= 3
    # 应包含税务相关关键词
    assert any(k in ["发票", "付款", "违约金", "增值税", "货款"] for k in keywords)

@pytest.mark.asyncio
async def test_judge_compliance():
    """测试合规判定"""
    analyzer = AIAnalyzer()
    clause = "买方应在收到发票后30日内支付货款。"
    regulations = [
        {"title": "增值税发票管理办法", "content": "发票应在交易发生后及时开具..."}
    ]

    result = await analyzer.judge_compliance(clause, regulations)

    assert result.risk_level in ["合规", "高风险", "不合规"]
    assert isinstance(result.violated_regulations, list)