# -*- coding: utf-8 -*-
"""
MonitorAgent - 盯盘监控专用 Agent

基于技术指标和持仓上下文，进行智能分析并生成交易建议。
继承自 BaseAgent，利用 ToolRegistry 进行工具调用和多轮推理。
"""

import logging
from typing import Any, Dict, List, Optional

from src.agent.agents.base_agent import BaseAgent
from src.agent.protocols import AgentContext, AgentOpinion
from src.agent.llm_adapter import LLMToolAdapter
from src.agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


# 监控专用的系统提示词
MONITOR_SYSTEM_PROMPT = """
你是一个专业的股票交易分析师，专注于实时监控和交易信号分析。

## 你的任务
基于以下信息给出专业的交易建议：
1. 当前技术指标状态（价格、均线、成交量、RSI、MACD等）
2. 检测到的交易信号（如有）
3. 用户持仓情况（成本、盈亏、仓位占比）
4. 市场环境上下文

## 输出格式
请严格按照以下结构输出 JSON 格式的分析结果：

```json
{
  "core_conclusion": "一句话总结当前状态和建议",
  "signal_analysis": "解释触发的信号及其意义",
  "portfolio_assessment": "结合持仓成本给出具体操作建议",
  "risk_warnings": ["风险点1", "风险点2"],
  "action_plan": {
    "recommendation": "买入/加仓/持有/减仓/卖出/观望",
    "reasoning": "明确的理由",
    "stop_loss": "止损价位（如适用）",
    "take_profit": "止盈价位（如适用）"
  },
  "confidence": "高/中/低"
}
```

## 注意事项
- 保持简洁专业，避免冗长分析
- 优先关注风险和止损
- 如果无明确信号，给出观望建议
- 结合持仓成本给出具体操作（如：成本1750，当前1850，浮盈5.7%，建议部分止盈）
- 不要提供具体的投资建议免责声明，这是内部分析工具
"""


class MonitorAgent(BaseAgent):
    """盯盘监控专用 Agent

    职责：
    - 接收技术指标和持仓信息
    - 进行多轮推理分析
    - 生成结构化的交易建议
    """

    agent_name = "monitor"
    tool_names = [
        "get_technical_indicators",
        "check_portfolio_risk",
        "compare_historical_signals",
    ]
    max_steps = 4  # 监控场景不需要太多步骤

    def __init__(
        self,
        tool_registry: ToolRegistry,
        llm_adapter: LLMToolAdapter,
        skill_instructions: str = "",
        technical_skill_policy: str = "",
    ):
        super().__init__(
            tool_registry=tool_registry,
            llm_adapter=llm_adapter,
            skill_instructions=skill_instructions,
            technical_skill_policy=technical_skill_policy,
        )

    def system_prompt(self, ctx: AgentContext) -> str:
        """构建系统提示词"""
        return MONITOR_SYSTEM_PROMPT

    def build_user_message(self, ctx: AgentContext) -> str:
        """
        构建用户消息

        从 context 中提取：
        - 股票代码和名称
        - 当前价格和涨跌幅
        - 技术指标快照
        - 检测到的信号
        - 持仓信息
        """
        data = ctx.data or {}

        stock_code = data.get("stock_code", "未知")
        stock_name = data.get("stock_name", "未知")
        current_price = data.get("current_price", 0)
        change_pct = data.get("change_pct", 0)

        # 技术指标
        indicators = data.get("indicators", {})
        ma5 = indicators.get("ma5", "N/A")
        ma20 = indicators.get("ma20", "N/A")
        volume_ratio = indicators.get("volume_ratio", "N/A")
        rsi = indicators.get("rsi", "N/A")
        macd_dif = indicators.get("macd_dif", "N/A")
        macd_dea = indicators.get("macd_dea", "N/A")

        # 信号列表
        signals = data.get("signals", [])
        signals_text = ""
        if signals:
            signals_text = "\n\n### 检测到的信号:\n"
            for sig in signals:
                signals_text += f"- {sig.get('description', '')}\n"
        else:
            signals_text = "\n\n### 检测到的信号:\n无明显交易信号\n"

        # 持仓信息
        portfolio = data.get("portfolio")
        portfolio_text = "\n\n### 持仓情况:\n无持仓\n"
        if portfolio and portfolio.get("has_position"):
            quantity = portfolio.get("quantity", 0)
            avg_cost = portfolio.get("avg_cost", 0)
            unrealized_pnl = portfolio.get("unrealized_pnl", 0)
            pnl_pct = portfolio.get("pnl_pct", 0)
            position_ratio = portfolio.get("position_ratio", 0) * 100

            portfolio_text = f"""
### 持仓情况:
- 持仓数量: {quantity} 股
- 平均成本: ¥{avg_cost:.2f}
- 当前价格: ¥{current_price:.2f}
- 未实现盈亏: ¥{unrealized_pnl:.2f} ({pnl_pct:+.2f}%)
- 仓位占比: {position_ratio:.1f}%
"""

        # 组装完整消息
        user_msg = f"""
## 监控股票: {stock_name} ({stock_code})

### 当前行情:
- 当前价格: ¥{current_price:.2f}
- 涨跌幅: {change_pct:+.2f}%

### 技术指标:
- MA5: {ma5 if ma5 is not None else 'N/A'}
- MA20: {ma20 if ma20 is not None else 'N/A'}
- 成交量比率: {volume_ratio if volume_ratio is not None else 'N/A'}
- RSI: {rsi if rsi is not None else 'N/A'}
- MACD DIF: {macd_dif if macd_dif is not None else 'N/A'}
- MACD DEA: {macd_dea if macd_dea is not None else 'N/A'}
{signals_text}{portfolio_text}

请基于以上信息进行分析，并给出专业的交易建议。
"""
        return user_msg

    def post_process(
        self, ctx: AgentContext, raw_text: str
    ) -> Optional[AgentOpinion]:
        """
        后处理：解析 LLM 返回的 JSON

        尝试从 raw_text 中提取 JSON 并验证结构
        """
        import json
        import re

        try:
            # 尝试提取 JSON（可能包含在 markdown 代码块中）
            json_match = re.search(r'```json\s*(.*?)\s*```', raw_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = raw_text

            data = json.loads(json_str)

            # 验证必要字段
            required_fields = ["core_conclusion", "action_plan"]
            if not all(field in data for field in required_fields):
                logger.warning(f"LLM 返回缺少必要字段: {data.keys()}")
                return None

            # 构建 AgentOpinion
            opinion = AgentOpinion(
                agent_name=self.agent_name,
                signal=data.get("core_conclusion", ""),
                confidence=self._parse_confidence(data.get("confidence", "中")),
                reasoning=data.get("action_plan", ""),
                raw_data=data,
            )

            return opinion

        except Exception as e:
            logger.error(f"解析 MonitorAgent 输出失败: {e}", exc_info=True)
            # 即使解析失败，也返回原始文本
            return AgentOpinion(
                agent_name=self.agent_name,
                signal="分析完成（JSON 解析失败）",
                confidence=0.5,
                reasoning="查看原始输出",
                raw_data={"raw_text": raw_text},
            )

    def _parse_confidence(self, confidence_str: str) -> float:
        """将置信度字符串转换为数值"""
        mapping = {
            "高": 0.9,
            "中": 0.7,
            "低": 0.5,
        }
        return mapping.get(confidence_str, 0.7)
