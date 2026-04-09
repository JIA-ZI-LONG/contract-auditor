# backend/chains/keyword_chain.py

"""
关键词提取 Chain

演示 LCEL 链式调用：
- prompt | llm 组合为 chain
- with_structured_output() 强制结构化输出
- 自动支持 invoke/stream/batch/async
"""

from chains.prompts import KEYWORD_PROMPT
from chains.llm import get_llm
from models.schemas import KeywordOutput

# LCEL chain: prompt | llm.with_structured_output()
keyword_chain = KEYWORD_PROMPT | get_llm().with_structured_output(KeywordOutput)

# 使用方式：
# 同步：keywords = keyword_chain.invoke({"clause": "..."})
# 异步：keywords = await keyword_chain.ainvoke({"clause": "..."})
# 批量：results = await keyword_chain.abatch([{"clause": "..."}, {"clause": "..."}])