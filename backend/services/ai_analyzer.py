import json
import logging
from openai import AsyncOpenAI
from config import settings
from models.schemas import SectionAuditResult

logger = logging.getLogger(__name__)

KEYWORD_PROMPT = """你是一个税务合同分析专家。请从以下合同条款中提取用于搜索相关税务法规的关键词。

条款内容：
{clause}

要求：
1. 提取3-5个关键词，聚焦税务合规相关内容
2. 关键词应能匹配到税务法规库中的相关文档
3. 输出格式：JSON数组，如 ["发票", "付款期限", "违约金"]

请直接输出关键词JSON数组，不要其他解释。"""

COMPLIANCE_PROMPT = """你是一个税务合同合规审计专家。请根据相关税务法规，判断以下合同条款的合规性。

【条款内容】
{clause}

【相关法规】
{regulations}

请判断该条款是否存在税务合规风险，并输出以下JSON格式：
{{
  "risk_level": "合规/高风险/不合规",
  "violated_regulations": ["违反的法规标题1", "法规标题2"],
  "reason": "详细分析该条款为什么存在风险或不合规，引用法规原文说明",
  "suggestion": "如果存在问题，给出具体的修改建议或替代条款"
}}

判定标准：
- 合规：条款完全符合税务法规要求
- 高风险：条款存在明显风险点，可能违规但需进一步确认
- 不合规：条款明确违反税务法规

请直接输出JSON，不要其他解释。"""

class AIAnalyzer:
    """GLM-5 AI分析服务"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.bailian_base_url
        )
        self.model = settings.bailian_model

    async def extract_keywords(self, clause: str) -> list[str]:
        """
        从条款中提取搜索关键词

        Args:
            clause: 条款文本

        Returns:
            关键词列表
        """
        logger.info(f"Extracting keywords from clause: {clause[:50]}...")

        prompt = KEYWORD_PROMPT.format(clause=clause)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        content = response.choices[0].message.content.strip()

        # 解析JSON数组
        try:
            # 清理可能的markdown格式
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            keywords = json.loads(content)
            if isinstance(keywords, list):
                return [str(k).strip() for k in keywords]
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse keywords: {content}")
            # fallback: 分词
            return clause.split()[:5]

        return []

    async def judge_compliance(
        self,
        clause: str,
        regulations: list[dict]
    ) -> SectionAuditResult:
        """
        判断条款合规性

        Args:
            clause: 条款文本
            regulations: 相关法规列表

        Returns:
            审计结果
        """
        logger.info(f"Judging compliance for clause: {clause[:50]}...")

        # 格式化法规文本
        reg_text = "\n".join([
            f"{i+1}. {r.get('title', '未知法规')}\n   {r.get('content', '')[:300]}"
            for i, r in enumerate(regulations)
        ])

        prompt = COMPLIANCE_PROMPT.format(clause=clause, regulations=reg_text)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        content = response.choices[0].message.content.strip()

        # 解析JSON
        try:
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)

            return SectionAuditResult(
                section_name="",  # 由调用者填充
                original_content=clause,
                risk_level=result.get("risk_level", "合规"),
                violated_regulations=result.get("violated_regulations", []),
                reason=result.get("reason", ""),
                suggestion=result.get("suggestion", "")
            )
        except json.JSONDecodeError:
            logger.error(f"Failed to parse compliance result: {content}")
            return SectionAuditResult(
                section_name="",
                original_content=clause,
                risk_level="合规",
                violated_regulations=[],
                reason="AI响应解析失败",
                suggestion=""
            )